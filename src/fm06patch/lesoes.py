"""Lesões do começo de 2026 (ficha C3b): tabela STARTING_INJURY do server_db.dat.

O banco tem a classe STARTING_INJURY (vtable 0x010E21F4, construtor 0x009EDDE0); o leitor
(0x00AA7390) lê, depois do u8 de tipo de todo registro de lista:

    u32 pessoa (índice no people_db), u32 lesão (índice no catálogo INJURY),
    DATE início, DATE fim (u16 dia do ano a partir de 0, u16 ano; 0/1900 = sem data),
    u8, u8, u8, e o par (u32 índice do registro, u32 UID = FFFFFFFF)

e põe o registro na lista DB+0x98 (0x00AA743B), lida por 0x00A0E190 logo depois da lista
DB+0x94 (0x00A11D60). No banco original: 1.225 registros de 28 bytes em 0x13CE347. A pessoa
é o índice que fecha o registro da pessoa no people_db (Filippo Inzaghi, UID 811, índice
317, lesão 11 "strained ankle ligaments"; Johan Mjällby, índice 71, lesão 26 "torn knee
ligaments"). A lista não está em ordem de pessoa e uma pessoa pode ter mais de um registro
(41 repetidas), então o registro novo vai no fim. Os três u8 são 0 em 709 dos 807 registros
com data; o significado não foi visto, ficam 0. O server_db é lido em sequência: a lista
pode crescer.

O catálogo INJURY (lista de 83 tipos em 0x5C8041 do banco original) tem o nome em inglês
("twisted ankle", "damaged knee cartilage"...); KINDS liga as palavras da planilha ao índice.
"""

from __future__ import annotations

import datetime as dt
import re
import struct
from dataclasses import dataclass

YEAR_SHIFT = -20
RECORD = 28
_DATA = struct.Struct("<BIIHHHHBBB")     # 20 bytes antes do par (índice, UID)
NO_DATE = (0, 1900)

# palavras inteiras da coluna "lesao" (em minúsculas; a primeira que aparecer vale) -> índice no INJURY
KINDS = (
    (("menisco", "cartilagem", "artroscopia no joelho"), 25, "damaged knee cartilage"),
    (("ligamento cruzado", "lca"), 27, "damaged cruciate ligaments"),
    (("ligamento do joelho",), 26, "torn knee ligaments"),
    (("calcanhar",), 9, "damaged heel"),
    (("tíbia", "tibia", "fíbula", "fibula"), 21, "broken leg (lower)"),
    (("tendão de aquiles", "aquiles"), 12, "damaged achilles tendon"),
    (("tornozelo",), 6, "sprained ankle"),
    (("posterior da coxa", "posterior"), 31, "torn hamstring"),
    (("coxa",), 30, "thigh strain"),
    (("panturrilha",), 18, "torn calf muscle"),
    (("virilha", "adutor", "pubalgia"), 35, "groin strain"),
    (("ombro",), 59, "dislocated shoulder"),
    (("pé", "metatarso"), 15, "broken foot"),
    (("joelho",), 22, "twisted knee"),
)


@dataclass(frozen=True)
class Injury:
    person: int                      # índice da pessoa no people_db
    kind: int                        # índice no catálogo INJURY
    start: tuple[int, int]           # (dia do ano a partir de 0, ano do motor)
    end: tuple[int, int]
    flags: tuple[int, int, int] = (0, 0, 0)

    def pack(self, index: int) -> bytes:
        return _DATA.pack(0, self.person, self.kind, *self.start, *self.end, *self.flags) + struct.pack("<Ii", index, -1)


def kind_of(text: str) -> tuple[int, str] | None:
    low = text.lower()
    for words, kind, name in KINDS:
        if any(re.search(rf"\b{re.escape(w)}\b", low) for w in words):
            return kind, name
    return None


def engine_date(date: dt.date, shift: int = YEAR_SHIFT) -> tuple[int, int]:
    try:
        moved = date.replace(year=date.year + shift)
    except ValueError:                   # 29/2
        moved = date.replace(year=date.year + shift, day=28)
    return moved.timetuple().tm_yday - 1, moved.year


def _valid(data: bytes, count_at: int) -> bool:
    count = struct.unpack_from("<I", data, count_at)[0]
    if not 100 <= count <= 100_000 or count_at + 4 + RECORD * count > len(data):
        return False
    for i in (0, 1, count // 2, count - 1):
        at = count_at + 4 + RECORD * i
        if data[at] != 0 or struct.unpack_from("<Ii", data, at + 20) != (i, -1):
            return False
        years = struct.unpack_from("<HHHH", data, at + 9)[1::2]
        if not all(y == 1900 or 1980 <= y <= 2030 for y in years):
            return False
    return True


def locate(data: bytes) -> int:
    """Posição do u32 quantidade da lista STARTING_INJURY."""
    needle = struct.pack("<Ii", 0, -1)
    at = data.find(needle)
    while at >= 0:
        if at >= 24 and data[at - 20] == 0 and _valid(data, at - 24):
            return at - 24
        at = data.find(needle, at + 1)
    raise ValueError("lista STARTING_INJURY não achada no server_db")


def records(data: bytes) -> list[Injury]:
    count_at = locate(data)
    count = struct.unpack_from("<I", data, count_at)[0]
    out = []
    for i in range(count):
        _, person, kind, d1, y1, d2, y2, a, b, c = _DATA.unpack_from(data, count_at + 4 + RECORD * i)
        out.append(Injury(person, kind, (d1, y1), (d2, y2), (a, b, c)))
    return out


def add(data: bytes, injuries: list[Injury]) -> tuple[bytes, list[Injury]]:
    """Acrescenta no fim da lista as lesões que ainda não estão nela (igual pessoa, tipo e
    datas). Devolve o banco e as que entraram."""
    count_at = locate(data)
    count = struct.unpack_from("<I", data, count_at)[0]
    have = {(r.person, r.kind, r.start, r.end) for r in records(data)}
    new = [i for i in injuries if (i.person, i.kind, i.start, i.end) not in have]
    end = count_at + 4 + RECORD * count
    block = b"".join(i.pack(count + n) for n, i in enumerate(new))
    out = bytearray(data[:end] + block + data[end:])
    struct.pack_into("<I", out, count_at, count + len(new))
    return bytes(out), new


def person_index(people: bytes, uid: int) -> int | None:
    """Índice da pessoa: o u32 antes do UID no fim da parte comum do registro (u16 ano,
    00 00 00, u32 índice, u32 UID, u32, u8 tipo 1/2/4). Só quando o UID fecha um registro só."""
    found = set()
    needle = struct.pack("<I", uid)
    at = people.find(needle)
    while at >= 0:
        if (at >= 9 and people[at - 8] == 0x07 and 0x6C <= people[at - 9] <= 0xE0
                and people[at - 7:at - 4] == b"\0\0\0" and at + 8 < len(people) and people[at + 8] in (1, 2, 4)):
            found.add(struct.unpack_from("<I", people, at - 4)[0])
        at = people.find(needle, at + 1)
    return found.pop() if len(found) == 1 else None


@dataclass(frozen=True)
class Row:
    clube: str
    nome: str
    lesao: str
    desde: dt.date
    volta: dt.date


def load_sheet(path) -> list[Row]:
    import openpyxl

    rows = openpyxl.load_workbook(path, read_only=True, data_only=True)["Lesoes"].iter_rows(values_only=True)
    header = [str(h or "").strip() for h in next(rows)]
    out = []
    for values in rows:
        row = dict(zip(header, values))
        if not row.get("nome_comum") or not row.get("desde") or not row.get("volta_prevista"):
            continue
        day = lambda v: v.date() if isinstance(v, dt.datetime) else dt.date.fromisoformat(str(v)[:10])
        out.append(Row(str(row["clube"]).strip(), str(row["nome_comum"]).strip(), str(row.get("lesao") or ""),
                       day(row["desde"]), day(row["volta_prevista"])))
    return out
