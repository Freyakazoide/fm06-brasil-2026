"""Tabelas de nomes do server_db.dat (primeiro nome, sobrenome, nome comum).

Cada tabela: u32 quantidade e, para cada nome,
    u8 0, u32 n, nome (UTF-16LE, n caracteres), 00 00, u16 uso, u32 nação, u32 índice, u32 UID
O índice é a posição na tabela (a pessoa cita o nome pelo índice) e "uso" é quantas
pessoas do banco têm o nome (confere em 96% dos nomes). A ordem é por nação e, dentro
dela, pelo uso.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

# começo do u32 quantidade de cada tabela no server_db 6.0.2 original
TABLES = {"first": 0x005F7416, "second": 0x0085C9F9, "common": 0x00DE5A49}


@dataclass
class Name:
    at: int          # posição do u8 0
    text: str
    uses: int
    nation: int
    index: int
    uid: int

    @property
    def size(self) -> int:
        return 1 + 4 + 2 * len(self.text) + 2 + 2 + 12


def read_table(data: bytes, start: int) -> tuple[list[Name], int]:
    """(nomes, posição logo depois da tabela)."""
    count = struct.unpack_from("<I", data, start)[0]
    at, names = start + 4, []
    for position in range(count):
        if data[at] != 0:
            raise ValueError(f"nomes: registro {position} sem 00 em 0x{at:X}")
        size = struct.unpack_from("<I", data, at + 1)[0]
        end = at + 5 + 2 * size
        if data[end:end + 2] != b"\0\0":
            raise ValueError(f"nomes: texto sem 00 00 em 0x{at:X}")
        uses, nation, index, uid = struct.unpack_from("<HIII", data, end + 2)
        if index != position:
            raise ValueError(f"nomes: índice {index} na posição {position}")
        names.append(Name(at, data[at + 5:end].decode("utf-16-le"), uses, nation, index, uid))
        at = end + 16
    return names, at


NEW_UID = 110_000_000        # acima dos UIDs do banco (máx. ~74 milhões) e dos do histórico (100 milhões)
NEW_SHARE = 0.7              # parte do "uso" da nação que fica com os nomes novos
KINDS = {"prenome": "first", "sobrenome": "second", "apelido": "common"}


def _record(text: str, uses: int, nation: int, index: int, uid: int) -> bytes:
    return (b"\0" + struct.pack("<I", len(text)) + text.encode("utf-16-le") + b"\0\0"
            + struct.pack("<HIII", uses, nation, index, uid))


def locate(data: bytes, original: bytes) -> dict[str, int]:
    """Começo de cada tabela em ``data`` (o banco já mexido), achado pelos primeiros bytes
    da tabela no original: as outras mudanças não mexem nas tabelas de nomes."""
    found = {}
    for kind, start in TABLES.items():
        needle = original[start + 4:start + 68]          # sem a quantidade, que muda
        at = data.find(needle, max(0, start - 0x100000))
        if at < 0:
            raise ValueError(f"nomes: tabela {kind} não encontrada")
        found[kind] = at - 4
    return found


def plan(data: bytes, wanted: dict[tuple[str, int], dict[str, int]], starts: dict[str, int] | None = None):
    """wanted: (tabela, nação) -> {nome: peso 1..100}.

    Nome que a nação já tem: o "uso" sobe para o peso novo (se for maior). Nome novo: entra
    no fim da tabela (índice = posição, como o jogo exige) com o peso. O peso é escalado
    para os nomes novos somarem NEW_SHARE do uso da nação. Devolve
    {tabela: (mudanças de uso [(posição do u16, valor)], registros novos [bytes])}."""
    starts = starts or TABLES
    result = {}
    uid = NEW_UID
    for kind in ("first", "second", "common"):
        names, _ = read_table(data, starts[kind])
        uses_at, appended = [], []
        index = len(names)
        for (table, nation), weights in sorted(wanted.items()):
            if table != kind or not weights:
                continue
            mine = {n.text.casefold(): n for n in names if n.nation == nation}
            listed = {text.casefold() for text in weights}
            old_total = sum(n.uses for key, n in mine.items() if key not in listed)
            scale = (old_total * NEW_SHARE / (1 - NEW_SHARE) / sum(weights.values())) if old_total else 1.0
            for text, weight in sorted(weights.items()):
                value = min(65535, max(1, round(weight * scale)))
                existing = mine.get(text.casefold())
                if existing:
                    if value > existing.uses:
                        uses_at.append((existing.at + 5 + 2 * len(existing.text) + 2, value))
                    continue
                appended.append(_record(text, value, nation, index, uid))
                index += 1
                uid += 1
        result[kind] = (uses_at, appended)
    return result


def apply(data: bytes, changes, starts: dict[str, int] | None = None) -> bytes:
    starts = starts or TABLES
    out = bytearray(data)
    for kind in ("common", "second", "first"):           # de trás para frente: as posições não mudam
        uses_at, appended = changes[kind]
        for at, value in uses_at:
            struct.pack_into("<H", out, at, value)
        if appended:
            start = starts[kind]
            _, end = read_table(bytes(out), start)
            count = struct.unpack_from("<I", out, start)[0]
            struct.pack_into("<I", out, start, count + len(appended))
            out[end:end] = b"".join(appended)
    return bytes(out)


def load_sheet(path) -> dict[tuple[str, int], dict[str, int]]:
    """data/modelos/nomes_regens.xlsx -> (tabela, código da nação) -> {nome: peso}."""
    import openpyxl

    from .people_contracts import NATION_CODES

    wanted: dict[tuple[str, int], dict[str, int]] = {}
    rows = openpyxl.load_workbook(path, read_only=True)["Nomes"].iter_rows(values_only=True)
    header = [str(h or "") for h in next(rows)]
    col = {h: i for i, h in enumerate(header)}
    for row in rows:
        nation = NATION_CODES.get(str(row[col["nacao"]] or "").strip())
        kind = KINDS.get(str(row[col["tipo"]] or "").strip().casefold())
        text = str(row[col["nome"]] or "").strip()
        if nation is None or kind is None or not text or len(text) > 40:
            continue
        weight = row[col["peso"]]
        weight = int(weight) if str(weight or "").strip().isdigit() else 50
        wanted.setdefault((kind, nation), {})[text] = max(1, min(100, weight))
    return wanted


class Filler:
    """Nome brasileiro de hoje para quem sobra num clube de 2026 com o nome de 2005 (sorteado
    pelos pesos da planilha; o mesmo UID tem sempre o mesmo nome)."""

    NICKNAME_CHANCE = 0.2

    def __init__(self, wanted: dict[tuple[str, int], dict[str, int]], nation: int = 0xBD):
        self.first = wanted.get(("first", nation), {})
        self.second = wanted.get(("second", nation), {})
        self.common = wanted.get(("common", nation), {})

    def __bool__(self) -> bool:
        return bool(self.first and self.second)

    def name(self, uid: int) -> tuple[str, str, str]:
        """(primeiro, comum, sobrenome) para o CHANGE_PLAYER_NAME."""
        import random

        rng = random.Random(uid)

        def pick(weights: dict[str, int]) -> str:
            names = sorted(weights)
            return rng.choices(names, weights=[weights[n] for n in names])[0]

        first, second = pick(self.first), pick(self.second)
        common = pick(self.common) if self.common and rng.random() < self.NICKNAME_CHANCE else ""
        return first, common, second
