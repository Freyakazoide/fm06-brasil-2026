"""Mídia brasileira de 2026 (MEDIA_SOURCE) no server_db.dat.

A lista DB+0x24 do server_db (leitor 0x00A08430, chamado em 0x00A12424 pelo carregador
0x00A12120) é a mesma lista polimórfica das pessoas: o 1º byte de cada registro é o tipo e
o tipo 0 é MEDIA_SOURCE (construtor 0x009ED840, leitor 0x00AA5210). No server_db só há
registros do tipo 0: 87 fontes, logo depois das lesões (u32 87 em 0x5CA056 no original),
quase todas inglesas, mais algumas polonesas, O JOGO e voetbalprimeur.nl. Nenhuma do Brasil.

Registro (leitor 0x00AA5210):

    u8 0 (tipo), texto nome (+0x1C), u8 0 (+0x28), texto nome curto (+0x2C),
    u8 0 (+0x38), u8 meio (+0x39), u8 n e n × u32 UID de clube coberto (+0x4C; sempre 8,
    0 = nenhum), texto endereço (+0x40, versão ≥ 0xE8),
    u8 periodicidade, u8 alcance, u32 UID do lugar,
    u32 índice do registro, u32 UID

Texto: u32 n e n caracteres UTF-16 + 00 00; n = 0 é só o u32.
Meio: 1 jornal, 2 revista, 4 rádio, 5 TV, 6 site (7 aposta, 8 site de lesões).
Periodicidade: 1 contínua (site, rádio, TV), 2 diária, 3 de domingo, 5 mensal.
Alcance: 2 cidade (UID da cidade: Londres 100023 no Evening Standard, Liverpool 100047 no
Echo), 4 país (UID da nação: Inglaterra 765, Escócia 793, Portugal 788; Brasil 1651).
Clubes: o icLiverpool.com cobre o 676 (Liverpool) e outro registro igual cobre o 650 (Everton).
"""

from __future__ import annotations

import csv
import struct
from dataclasses import dataclass, field

FIRST = "the Daily Mirror"
COUNT = 87                      # fontes no banco original
CLUB_SLOTS = 8
NEW_UID = 102_000_000           # acima dos UIDs do banco (e dos 101_000_000+ do premios.py)
BRAZIL = 1651                   # UID da nação (código 189)
KIND = {"jornal": 1, "revista": 2, "radio": 4, "tv": 5, "site": 6}
EVERY = {"continua": 1, "diaria": 2, "domingo": 3, "mensal": 5}
CITY, COUNTRY = 2, 4


@dataclass
class Media:
    name: str
    kind: int
    every: int
    scope: int
    place: int
    clubs: list[int] = field(default_factory=list)
    url: str = ""
    short: str = ""
    index: int = 0
    uid: int = 0
    at: int = 0

    def pack(self) -> bytes:
        clubs = (self.clubs + [0] * CLUB_SLOTS)[:CLUB_SLOTS]
        out = bytearray(b"\0" + _text(self.name) + b"\0" + _text(self.short or self.name))
        out += struct.pack(f"<BBB{CLUB_SLOTS}I", 0, self.kind, CLUB_SLOTS, *clubs)
        out += _text(self.url) + struct.pack("<BBIII", self.every, self.scope, self.place, self.index, self.uid)
        return bytes(out)


def _text(s: str) -> bytes:
    return struct.pack("<I", len(s)) + (s.encode("utf-16-le") + b"\0\0" if s else b"")


def _read_text(data: bytes, at: int) -> tuple[str, int]:
    n = struct.unpack_from("<I", data, at)[0]
    if n > 300:
        raise ValueError("texto longo demais")
    if n == 0:
        return "", at + 4
    return data[at + 4:at + 4 + 2 * n].decode("utf-16-le"), at + 4 + 2 * n + 2


def locate(data: bytes) -> tuple[int, list[Media]]:
    """Posição do u32 quantidade e as fontes. A lista começa no Daily Mirror."""
    first = b"\0" + _text(FIRST)
    at = data.find(first)
    while at >= 0:
        count_at = at - 4
        count = struct.unpack_from("<I", data, count_at)[0]
        try:
            return count_at, _parse(data, at, count)
        except (ValueError, struct.error, UnicodeDecodeError):
            at = data.find(first, at + 1)
    raise ValueError("lista de mídia não achada")


def _parse(data: bytes, at: int, count: int) -> list[Media]:
    if not 0 < count < 10_000:
        raise ValueError("quantidade")
    out = []
    for i in range(count):
        start = at
        if data[at] != 0:
            raise ValueError("tipo")
        name, at = _read_text(data, at + 1)
        short, at = _read_text(data, at + 1)
        kind, n = data[at + 1], data[at + 2]
        clubs = list(struct.unpack_from(f"<{n}I", data, at + 3))
        while clubs and not clubs[-1]:
            clubs.pop()
        url, at = _read_text(data, at + 3 + 4 * n)
        every, scope, place, index, uid = struct.unpack_from("<BBIII", data, at)
        if index != i:
            raise ValueError("índice")
        out.append(Media(name, kind, every, scope, place, clubs, url, short, index, uid, start))
        at += 14
    return out


def add(data: bytes, wanted: list[Media]) -> tuple[bytes, list[Media]]:
    """Fontes novas no fim da lista. Se já há fontes deste módulo (UID ≥ NEW_UID), não faz nada."""
    count_at, sources = locate(data)
    if any(m.uid >= NEW_UID for m in sources):
        return data, []
    new = []
    for k, m in enumerate(wanted):
        m.index, m.uid = len(sources) + k, NEW_UID + k
        new.append(m)
    tail = count_at + 4 + sum(len(m.pack()) for m in sources)
    out = bytearray(data)
    out[tail:tail] = b"".join(m.pack() for m in new)
    struct.pack_into("<I", out, count_at, len(sources) + len(new))
    return bytes(out), new


def load_sheet(path, city_uid, club_uid) -> tuple[list[Media], list[str]]:
    """midia_2026.csv -> fontes. city_uid(nome) e club_uid(clube de 2026) devolvem o UID ou None."""
    out, problems = [], []
    for row in csv.DictReader(open(path, encoding="utf-8-sig")):
        name = row["nome"].strip()
        kind, every = KIND.get(row["meio"].strip()), EVERY.get(row["periodicidade"].strip())
        if kind is None or every is None:
            problems.append(f"{name}: meio ou periodicidade desconhecidos")
            continue
        if row["alcance"].strip() == "cidade":
            scope, place = CITY, city_uid(row["cidade"].strip())
            if place is None:
                problems.append(f"{name}: cidade {row['cidade']!r} não achada")
                continue
        else:
            scope, place = COUNTRY, BRAZIL
        clubs = []
        for club in filter(None, (c.strip() for c in row["clubes"].split(";"))):
            uid = club_uid(club)
            if uid is None:
                problems.append(f"{name}: clube {club!r} não achado")
            else:
                clubs.append(uid)
        out.append(Media(name, kind, every, scope, place, clubs[:CLUB_SLOTS], row["endereco"].strip()))
    return out, problems
