"""Registros de time no server_db.dat (divisão inicial, classificação anterior).

Formato deduzido do leitor do TEAM no fm.exe (método 10 da vtable, 0x00A1FA30)
e conferido no banco: Série A, B e C dão 20, 20 e 128 registros.

    u32 UID do clube
    0A 00
    u8  classificação na temporada passada  -> TEAM+0x60 (0 = sem)
    u16 reputação                           -> TEAM+0x6C
    00 00
    u32 divisão atual                       -> TEAM+0x54
    u32 divisão da temporada passada        -> TEAM+0x5C (FFFFFFFF = nenhuma)

Com o patch `serie_c_nova`, o índice 376 (Taça de Prata) é a nova Série C.

As divisões são índices da tabela de competições do server_db (0x005B85C0),
resolvidos para ponteiros por 0x009E8280.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass

# NOVA_C: registro "Taça de Prata" (ID 319191), usado como nova Série C pelo
# patch serie_c_nova do fm.exe; com ele, a antiga C (86) é o 4º nível.
DIVISIONS = {"A": 73, "B": 85, "C": 86, "NOVA_C": 376}
NONE = 0xFFFFFFFF

_RECORD = re.compile(rb"\x0a\x00(.)(..)\x00\x00(....)(....)", re.S)
_DATES = b"\x6c\x07\x00\x00\x6c\x07\x00\x00\x6c\x07\x00\x00\x00"
_CLUB_TAIL = b"\x00\xbd\x00\x00\x00"


@dataclass
class TeamRecord:
    offset: int  # posição do "0A 00"
    club_uid: int
    last_position: int
    reputation: int
    division: int
    last_division: int
    name: str = ""
    short_name: str = ""

    @property
    def serie(self) -> str:
        return division_name(self.division)

    @property
    def last_serie(self) -> str:
        return division_name(self.last_division)


def division_name(index: int) -> str:
    if index == NONE:
        return "-"
    for key, value in DIVISIONS.items():
        if value == index:
            return key
    return str(index)


def division_index(text: str) -> int:
    text = text.strip().upper()
    if text in ("-", "NENHUMA"):
        return NONE
    if text in DIVISIONS:
        return DIVISIONS[text]
    return int(text)


def _string(data: bytes, offset: int) -> tuple[str, int]:
    length = struct.unpack_from("<I", data, offset)[0]
    if not 1 <= length <= 100:
        return "", offset
    end = offset + 4 + 2 * length
    return data[offset + 4:end].decode("utf-16le", "replace"), end + 2


def club_names(data: bytes, uid: int, limit: int = 0x400000) -> tuple[str, str]:
    """Nome longo e curto do clube.

    O registro do clube começa com u32, u32 UID, 00 BD 00 00 00 00, apelidos e,
    depois do marcador de datas (1900, 1900, 1900), nome longo e nome curto.
    """
    needle = struct.pack("<I", uid) + _CLUB_TAIL
    start = 0
    while True:
        start = data.find(needle, start, limit)
        if start < 0:
            return "", ""
        mark = data.find(_DATES, start, start + 0x600)
        if mark > 0:
            long_name, after = _string(data, mark + len(_DATES))
            short_name, _ = _string(data, after)
            if long_name:
                return long_name, short_name
        start += 1


def find_teams(data: bytes, divisions=None, with_names: bool = True) -> list[TeamRecord]:
    wanted = set(DIVISIONS.values() if divisions is None else divisions)
    teams = []
    for match in _RECORD.finditer(data):
        division, last = struct.unpack("<II", match.group(3) + match.group(4))
        if division not in wanted or match.start() < 4:
            continue
        team = TeamRecord(
            offset=match.start(),
            club_uid=struct.unpack_from("<I", data, match.start() - 4)[0],
            last_position=match.group(1)[0],
            reputation=struct.unpack("<H", match.group(2))[0],
            division=division,
            last_division=last,
        )
        if with_names:
            team.name, team.short_name = club_names(data, team.club_uid)
        teams.append(team)
    return teams


def find_team(teams: list[TeamRecord], key: str) -> TeamRecord:
    """Acha um time pelo UID do clube ou pelo nome (curto ou longo, exato)."""
    key = key.strip()
    if key.isdigit():
        matches = [t for t in teams if t.club_uid == int(key)]
    else:
        low = key.casefold()
        matches = [t for t in teams if low in (t.short_name.casefold(), t.name.casefold())]
    if len(matches) != 1:
        found = ", ".join(f"{t.short_name} ({t.club_uid})" for t in matches) or "nenhum"
        raise KeyError(f"'{key}': {found}")
    return matches[0]


def write_team(buffer: bytearray, team: TeamRecord) -> None:
    struct.pack_into("<B", buffer, team.offset + 2, team.last_position)
    struct.pack_into("<II", buffer, team.offset + 7, team.division, team.last_division)


BRAZIL_NATION = 0xBD
_CLUB_HEADER = re.compile(rb"(....)(....)\x00\xbd\x00\x00\x00\x00", re.S)
_VALID_DIVISIONS = set(DIVISIONS.values()) | {NONE}


def _team_record(data: bytes, uid: int, start: int = 0xE00000, end: int = 0x1600000):
    """Registro do time de um clube: UID + 0A 00, com campos plausíveis."""
    needle = struct.pack("<I", uid) + b"\x0a\x00"
    found = []
    at = start
    while True:
        at = data.find(needle, at, end)
        if at < 0:
            break
        rec = at + 4
        division, last = struct.unpack_from("<II", data, rec + 7)
        reputation = struct.unpack_from("<H", data, rec + 3)[0]
        if (data[rec + 5:rec + 7] == b"\x00\x00" and division in _VALID_DIVISIONS
                and last in _VALID_DIVISIONS and reputation <= 10000 and data[rec + 2] <= 40):
            found.append(rec)
        at += 1
    return found[0] if len(found) == 1 else None


def find_brazil_teams(data: bytes) -> list[TeamRecord]:
    """Todos os times de clubes brasileiros (nação 0xBD no registro do clube),
    mais os que estão nas divisões nacionais."""
    teams = {t.club_uid: t for t in find_teams(data)}
    for match in _CLUB_HEADER.finditer(data, 0, 0x400000):
        uid = struct.unpack("<I", match.group(2))[0]
        if uid == 0 or uid in teams:
            continue
        mark = data.find(_DATES, match.end(), match.end() + 0x600)
        if mark < 0:
            continue
        long_name, after = _string(data, mark + len(_DATES))
        short_name, _ = _string(data, after)
        rec = _team_record(data, uid) if long_name else None
        if rec is None:
            continue
        division, last = struct.unpack_from("<II", data, rec + 7)
        teams[uid] = TeamRecord(
            offset=rec,
            club_uid=uid,
            last_position=data[rec + 2],
            reputation=struct.unpack_from("<H", data, rec + 3)[0],
            division=division,
            last_division=last,
            name=long_name,
            short_name=short_name,
        )
    return list(teams.values())
