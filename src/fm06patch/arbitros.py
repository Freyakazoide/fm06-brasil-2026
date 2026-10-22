"""Árbitros (OFFICIAL) no people_db.dat.

O registro da pessoa (comissao.py) fecha a parte comum com u16 ano, 00 00 00, u32
índice, u32 UID. Logo depois vem o bloco do tipo: u32, u8 tipo (1 jogador, 2 staff,
4 árbitro) e, no árbitro (leitor 0x00A6D540): u32, u16 capacidade, u16 potencial,
u16 reputação, 10 x u8 atributos (zerados nos árbitros brasileiros: não dá para saber
qual seria o "rigor"), u32. O banco 6.0.2 tem 6.798 árbitros, 492 do Brasil (Wilson
Luís Seneme 135/160/145, Leonardo Gaciba 122/160/122). O CHANGE_PLAYER_NAME do .lnc
procura a pessoa pelo UID, como no staff.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass

from .comissao import _CONTRACT, NONE, _names_before, name_tables, split_name

OFFICIAL = 4
BRAZIL = 0xBD
_OFFICIAL = re.compile(rb"[\x6c-\xe0]\x07\x00\x00\x00(....)(....)....\x04....(..)(..)(..)", re.S)


@dataclass
class Official:
    uid: int
    name: str
    nation: int
    ability: int
    potential: int
    reputation: int
    values_at: int              # posição do u16 capacidade
    employed: bool = False      # também tem contrato com clube (76 dos brasileiros)


@dataclass
class Referee:
    nome: str
    uf: str
    quadro: str
    nivel: int                  # 1-20

    @property
    def ability(self) -> int:
        """Nível 1-20 -> capacidade 1-200 (19 = 180, o maior árbitro brasileiro do banco)."""
        return max(1, min(200, round(self.nivel * 9.5)))


def read(people: bytes, server: bytes, nation: int | None = BRAZIL) -> list[Official]:
    tables = name_tables(server)
    found = []
    for match in _OFFICIAL.finditer(people):
        index, uid = struct.unpack("<II", match.group(1) + match.group(2))
        values = [struct.unpack("<H", match.group(i))[0] for i in (3, 4, 5)]
        if not (index < 2_000_000 and 0 < uid < 100_000_000 and max(values) <= 200):
            continue
        names_at = _names_before(people, match.start() + 5, tables, back=0x200)
        if names_at is None:
            continue
        first, second, common, size = struct.unpack_from("<IIII", people, names_at)
        born = names_at + 16 + 2 * size + (2 if size else 0)
        code = struct.unpack_from("<I", people, born + 5)[0]
        if nation is not None and code != nation:
            continue
        name = (tables[2].get(common) if common != NONE else None) or \
            f"{tables[0].get(first, '')} {tables[1].get(second, '')}".strip()
        employed = _CONTRACT.search(people, names_at, match.start()) is not None
        found.append(Official(uid, name, code, *values, match.start(3), employed))
    return found


def plan(officials: list[Official], referees: list[Referee]) -> list[tuple[Official, Referee]]:
    """Os árbitros da planilha (maior nível primeiro) nos árbitros do banco de maior capacidade.
    Quem também tem contrato com clube fica de fora (o nome novo apareceria na comissão)."""
    hosts = sorted((o for o in officials if not o.employed), key=lambda o: (-o.ability, -o.reputation, o.uid))
    return list(zip(hosts, sorted(referees, key=lambda r: -r.nivel)))


def apply(people: bytes, pairs: list[tuple[Official, Referee]]) -> bytes:
    """Capacidade e reputação pelo nível; o potencial não fica abaixo da capacidade."""
    out = bytearray(people)
    for official, referee in pairs:
        value = referee.ability
        struct.pack_into("<HHH", out, official.values_at, value, max(official.potential, value), value)
    return bytes(out)


def lnc_text(pairs: list[tuple[Official, Referee]]) -> str:
    lines = ["# FM06 Brasil 2026: árbitros do quadro de 2026 (scripts/aplicar_arbitros.py)"]
    for official, referee in pairs:
        first, common, second = split_name(referee.nome)
        lines.append(f'"CHANGE_PLAYER_NAME"\t{official.uid}\t"{first}"\t"{common}"\t"{second}"')
    return "\r\n".join(lines) + "\r\n"


def load_sheet(path) -> list[Referee]:
    """data/modelos/arbitros_2026.xlsx, aba Arbitros (nome, uf, quadro, nivel)."""
    import openpyxl

    rows = openpyxl.load_workbook(path, read_only=True)["Arbitros"].iter_rows(values_only=True)
    header = [str(h or "") for h in next(rows)]
    referees = []
    for values in rows:
        row = dict(zip(header, values))
        name = str(row.get("nome") or "").strip()
        level = str(row.get("nivel") or "").strip()
        if name and level.isdigit():
            referees.append(Referee(name, str(row.get("uf") or ""), str(row.get("quadro") or ""), int(level)))
    return referees
