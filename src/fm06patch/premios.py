"""Histórico de prêmios (PERSON_AWARD_HISTORY) no server_db.dat: Bola de Ouro de 2006 a 2025.

A lista DB+0x90 (leitor 0x00A0B7A0, chamado em 0x00A125E8) vem logo antes do histórico de
campeões (DB+0x88, historico.find_list). Registro (construtor 0x009ED280, leitor 0x00A96C40):

    u8 0, u32 prêmio (índice da lista de prêmios), u16 ano,
    u32 pessoa do 1º, do 2º e do 3º (índice no people_db; FFFFFFFF = fora do banco),
    u8, u8, u8 (gols, nos prêmios de artilheiro),
    texto do 1º, do 2º e do 3º (u32 n e n caracteres UTF-16 + 00 00; n = 0 é só o u32),
    u32 índice do registro, u32 UID

No banco original: 5.362 registros em 0x1296FF5, de 428 prêmios. O índice do prêmio é a
posição na lista de nomes do lang_db (0 "World Footballer of the Year", Ronaldinho 2004).
Do Brasil só três têm histórico:
  129 "Brazilian 1st Division Player of the Year" (1971-2004: Robinho 2004, Alex 2003,
      Kaká 2002, Alex Mineiro 2001 = Bola de Ouro da Placar);
  131 "Brazilian 1st Division Top Goalscorer" (1971-2004, com gols: Washington 34 em 2004);
  631 "Brazilian Internet Voting Player of the Year" (2000-2004).
O jogo mostra o ano + 20 (motor em 2005): como no histórico de campeões, os anos do banco
desses três ficam −20 e a Bola de Ouro real de A entra como A − 20 no 129. Não há prêmio
com histórico para o Craque do Brasileirão nem para a Bola de Prata (a seleção do ano, 130,
não tem nenhum registro), então ficam de fora.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from . import historico

SHIFT = 20
NONE = 0xFFFFFFFF
BRAZIL = (129, 131, 631)
GOLDEN_BALL = 129
NEW_UID = 101_000_000           # acima dos UIDs do banco e dos 100_000_000+ do campeoes.py


@dataclass
class Record:
    at: int
    award: int
    year: int
    people: tuple[int, int, int]
    numbers: tuple[int, int, int]
    names: tuple[str, str, str]
    index: int
    uid: int

    def pack(self) -> bytes:
        out = bytearray(struct.pack("<BIH3I3B", 0, self.award, self.year, *self.people, *self.numbers))
        for name in self.names:
            out += struct.pack("<I", len(name)) + (name.encode("utf-16-le") + b"\0\0" if name else b"")
        return bytes(out + struct.pack("<II", self.index, self.uid))


def _text(data: bytes, at: int) -> tuple[str, int]:
    n = struct.unpack_from("<I", data, at)[0]
    if n > 300:
        raise ValueError("texto longo demais")
    if n == 0:
        return "", at + 4
    return data[at + 4:at + 4 + 2 * n].decode("utf-16-le"), at + 4 + 2 * n + 2


def _parse(data: bytes, at: int, count: int) -> tuple[list[Record], int]:
    out = []
    for i in range(count):
        if data[at] != 0:
            raise ValueError("tipo")
        award, year, *rest = struct.unpack_from("<IH3I3B", data, at + 1)
        q = at + 1 + 21
        names = []
        for _ in range(3):
            name, q = _text(data, q)
            names.append(name)
        index, uid = struct.unpack_from("<II", data, q)
        if index != i:
            raise ValueError("índice")
        out.append(Record(at, award, year, tuple(rest[:3]), tuple(rest[3:]), tuple(names), index, uid))
        at = q + 8
    return out, at


def locate(data: bytes) -> tuple[int, list[Record]]:
    """Posição do u32 quantidade e os registros: a lista termina onde começa a de campeões."""
    end = historico.find_list(data)
    count = struct.unpack_from("<I", data, end - 8)[0] + 1      # o último fecha com quantidade − 1
    needle, low = struct.pack("<I", count), max(0, end - 3_000_000)
    at = data.rfind(needle, low, end)
    while at >= 0:
        try:
            records, stop = _parse(data, at + 4, count)
        except (ValueError, struct.error, UnicodeDecodeError):
            stop = -1
        if stop == end:
            return at, records
        at = data.rfind(needle, low, at)
    raise ValueError("lista de histórico de prêmios não achada")


def apply(data: bytes, golden_ball: dict[int, tuple[str, int]], gone: set[int] = frozenset()
          ) -> tuple[bytes, list[str]]:
    """golden_ball: ano real -> (nome, pessoa ou NONE). Anos do Brasil −20 e a Bola de Ouro no
    fim da lista. ``gone``: índices de pessoas de 2005 que viraram outra de 2026 (hospedeiros);
    em qualquer prêmio, a ligação com elas sai e fica só o nome (o Robinho de 2004 apontava para
    o índice 28921, hoje outro jogador). Se a lista já tem registros deste módulo
    (UID ≥ NEW_UID), não faz nada."""
    count_at, records = locate(data)
    if any(r.uid >= NEW_UID for r in records):
        return data, ["histórico de prêmios já gravado; nada a fazer"]
    out = bytearray(data)
    shifted = unlinked = 0
    for r in records:
        if r.award in BRAZIL:
            struct.pack_into("<H", out, r.at + 5, r.year - SHIFT)
            shifted += 1
        for k, person in enumerate(r.people):
            if person in gone:
                struct.pack_into("<I", out, r.at + 7 + 4 * k, NONE)
                unlinked += 1
    have = {r.year - SHIFT for r in records if r.award == GOLDEN_BALL}
    count = len(records)
    new = [Record(0, GOLDEN_BALL, year - SHIFT, (person, NONE, NONE), (0, 0, 0), (name, "", ""),
                  count + k, NEW_UID + k)
           for k, (year, (name, person)) in enumerate(sorted((y, w) for y, w in golden_ball.items()
                                                             if y - SHIFT not in have))]
    tail = count_at + 4 + sum(len(r.pack()) for r in records)
    out[tail:tail] = b"".join(r.pack() for r in new)
    struct.pack_into("<I", out, count_at, count + len(new))
    linked = sum(r.people[0] != NONE for r in new)
    return bytes(out), [f"{shifted} registros do Brasil com o ano −20 (prêmios {', '.join(map(str, BRAZIL))})",
                        f"{unlinked} ligações com pessoas que viraram outra saíram (fica o nome)",
                        f"Bola de Ouro: {len(new)} anos novos ({linked} ligados ao jogador de 2026)"]


def load_sheet(path, prize: str = "Bola de Ouro") -> dict[int, tuple[str, str, str]]:
    """Aba Premios: ano -> (vencedor, jogador_2026, clube_2026) do prêmio; as duas últimas
    colunas só quando o vencedor ainda está no jogo (vazias = só o nome)."""
    import openpyxl

    rows = openpyxl.load_workbook(path, read_only=True, data_only=True)["Premios"].iter_rows(values_only=True)
    header = [str(h or "").strip() for h in next(rows)]
    out = {}
    for values in rows:
        row = dict(zip(header, values))
        if str(row.get("premio") or "").strip() == prize and row.get("ano") and row.get("vencedor"):
            out[int(row["ano"])] = (str(row["vencedor"]).strip(), str(row.get("jogador_2026") or "").strip(),
                                    str(row.get("clube_2026") or "").strip())
    return out
