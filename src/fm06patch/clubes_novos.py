"""Clubes novos no server_db.dat (ficha C13): um clube e o time dele nos fins das listas.

Lista de clubes (DB+0x10, leitor 0x00A06810): u32 quantidade e registros do tipo 0 (CLUB,
leitor 0x00A31C70), cada um começando com 00 e o u32 da nação e terminando com (índice,
UID). Antes do par: u8 n × u32 times do clube, u8 m × 8 bytes relações, 18 bytes
(rivais.py). O 1º registro do banco 6.0.2 é albanês (nação 0x7E).

Lista de times (leitor do TEAM 0x00A1FA30): u32 quantidade e registros dos tipos 10 (time
de clube), 11 (seleção) e 12. O time de clube tem um cabeçalho fixo, cinco listas (u8 × u32,
u16 × u32 jogadores, u8 × u32, u8 × u32, u16 × objeto) e um fim com o índice do clube 14
bytes antes do par (índice, UID) que fecha o registro.

As duas listas são lidas em sequência: um registro novo vai no fim, com o próximo índice,
e o contador da lista sobe.
"""

from __future__ import annotations

import csv
import re
import struct
from dataclasses import dataclass
from pathlib import Path

from .server_teams import _DATES

NONE = 0xFFFFFFFF
CLUB_TAIL = 18                  # bytes entre as relações e o par que fecha o clube
TEAM_CLUB = 14                  # o índice do clube fica 14 bytes antes do par do time
FIRST_NATION = 0x7E             # o 1º clube do banco é albanês
TEAM_TYPES = (10, 11, 12)
TEAM_MANAGER = 23               # u32 técnico (TEAM+0x70, elenco_times.MANAGER + 1)
TEAM_STATE = 47                 # u32 estadual do time (TEAM+0x64, estaduais_clubes.STATE_FIELD)


@dataclass
class Records:
    count_at: int               # posição do u32 quantidade
    ends: list[int]             # posição do par (índice, UID) de cada registro

    def start(self, index: int) -> int:
        return self.count_at + 4 if index == 0 else self.ends[index - 1] + 8

    def end(self, index: int) -> int:
        return self.ends[index] + 8

    def uid(self, data: bytes, index: int) -> int:
        return struct.unpack_from("<I", data, self.ends[index] + 4)[0]


def _club_start(data: bytes, at: int) -> bool:
    """Começo de um registro de clube: 00, u32 nação (FFFFFFFF = sem), u8, texto (apelido)."""
    if data[at] != 0 or struct.unpack_from("<I", data, at + 1)[0] not in range(0x100) and             struct.unpack_from("<I", data, at + 1)[0] != NONE:
        return False
    n = struct.unpack_from("<I", data, at + 6)[0]
    return n < 80 and all(32 <= c < 0x250 for c in struct.unpack_from(f"<{n}H", data, at + 10))


def _team_start(data: bytes, at: int) -> bool:
    return data[at] in TEAM_TYPES


def _walk(data: bytes, count_at: int, is_start, max_size: int) -> Records:
    count = struct.unpack_from("<I", data, count_at)[0]
    ends, at = [], count_at + 4
    for index in range(count):
        needle = struct.pack("<I", index)
        q = data.find(needle, at + 8, at + max_size)
        while q >= 0:
            uid = struct.unpack_from("<I", data, q + 4)[0]
            if uid and (index == count - 1 or is_start(data, q + 8)):
                break
            q = data.find(needle, q + 1, at + max_size)
        if q < 0:
            raise ValueError(f"registro {index} da lista em {count_at:#x} não achado")
        ends.append(q)
        at = q + 8
    return Records(count_at, ends)


def club_list(data: bytes) -> Records:
    for m in re.finditer(rb"(....)\x00" + struct.pack("<I", FIRST_NATION), data):
        count = struct.unpack_from("<I", data, m.start())[0]
        if 10_000 < count < 60_000 and _club_start(data, m.start() + 4):
            try:
                return _walk(data, m.start(), _club_start, 0x8000)
            except ValueError:
                continue
    raise ValueError("lista de clubes não achada")


def team_list(data: bytes) -> Records:
    for m in re.finditer(rb"(....)\x0b\x00", data):
        count = struct.unpack_from("<I", data, m.start())[0]
        if 10_000 < count < 60_000:
            try:
                return _walk(data, m.start(), _team_start, 0x8000)
            except ValueError:
                continue
    raise ValueError("lista de times não achada")


# ---- registro do clube ----

def club_lists(data: bytes, start: int, pair: int) -> tuple[int, int]:
    """(posição do u8 n dos times, posição do u8 m das relações) a partir do fim do clube,
    como no rivais.read: as relações começam com o tipo de 1 a 9 e os times são de 1 a 7."""
    end = first = pair - CLUB_TAIL
    while first - 8 > start and 1 <= data[first - 8] <= 9:
        first -= 8
    for m_at in range(first - 1, end):
        size = (end - m_at - 1) // 8
        if (end - m_at - 1) % 8 or data[m_at] != size:
            continue
        for n in range(1, 8):
            n_at = m_at - 4 * n - 1
            if data[n_at] == n and all(struct.unpack_from("<I", data, n_at + 1 + 4 * i)[0] < 100_000
                                       for i in range(n)):
                return n_at, m_at
    raise ValueError("listas do fim do clube não achadas")


def club_names(data: bytes, start: int, pair: int) -> tuple[int, int, int]:
    """(posição do texto nome longo, posição do curto, fim do curto) depois das datas."""
    mark = data.find(_DATES, start, pair)
    if mark < 0:
        raise ValueError("nomes do clube não achados")
    long_at = mark + len(_DATES)
    short_at = _skip_text(data, long_at)
    return long_at, short_at, _skip_text(data, short_at)


def _skip_text(data: bytes, at: int) -> int:
    n = struct.unpack_from("<I", data, at)[0]
    return at + 4 + (2 * n + 2 if n else 0)


def text(s: str) -> bytes:
    return struct.pack("<I", len(s)) + (s.encode("utf-16-le") + b"\0\0" if s else b"")


def clone_club(data: bytes, clubs: Records, donor: int, uid: int, name: str, short: str,
               teams: list[int], index: int | None = None) -> bytes:
    """Registro de um clube novo copiado do donor: nomes, times, índice e UID novos, sem
    apelidos e sem relações (o resto, como nação, cidade e estádio, vem do donor)."""
    start, pair = clubs.start(donor), clubs.ends[donor]
    long_at, short_at, names_end = club_names(data, start, pair)
    n_at, m_at = club_lists(data, start, pair)
    first = _skip_text(data, start + 6)                         # 00, nação, u8, apelido 1
    second = _skip_text(data, first + 1)                        # u8, apelido 2
    out = bytearray(data[start:start + 6]) + text("") + data[first:first + 1] + text("")
    out += data[second:long_at] + text(name) + text(short) + data[names_end:n_at]
    out += struct.pack(f"<B{len(teams)}I", len(teams), *teams) + b"\0"            # sem relações
    out += data[pair - CLUB_TAIL:pair] + struct.pack("<II", len(clubs.ends) if index is None else index, uid)
    return bytes(out)


# ---- registro do time ----

# cabeçalho fixo do time até o u8 da 1ª lista (medido no Flamengo, conferido nos 19.218 times de clube)
TEAM_HEADER = 62


@dataclass
class Team:
    start: int
    lists_at: int               # posição do u8 da 1ª lista
    players: list[int]
    tail_at: int                # depois das cinco listas (as duas datas e o fim)
    end: int


def parse_team(data: bytes, start: int, end: int) -> Team | None:
    """Time de clube (tipo 10) com as cinco listas; None se o registro não fecha (objetos na
    5ª lista)."""
    at = start + TEAM_HEADER
    lists_at = at
    n = data[at]
    at += 1 + 4 * n
    m = struct.unpack_from("<H", data, at)[0]
    players = list(struct.unpack_from(f"<{m}I", data, at + 2))
    at += 2 + 4 * m
    for _ in range(2):
        at += 1 + 4 * data[at]
    if struct.unpack_from("<H", data, at)[0] != 0:
        return None
    at += 2
    return Team(start, lists_at, players, at, end)


def clone_team(data: bytes, team: Team, club_index: int, index: int, uid: int, state: int = NONE) -> bytes:
    """Time novo copiado de outro: sem jogadores, sem divisão e sem estadual, ligado ao clube
    novo. O estadual herdado punha um 21º time no Paulista de 20 e o Brasil sumia da lista de
    países do New Game (teste 1)."""
    head = bytearray(data[team.start:team.lists_at])
    head[2] = 0                                                     # classificação anterior
    struct.pack_into("<II", head, 7, NONE, NONE)                    # divisão atual e anterior
    struct.pack_into("<I", head, TEAM_STATE, state)
    struct.pack_into("<I", head, TEAM_MANAGER, NONE)                # sem o técnico do doador
    tail = bytearray(data[team.tail_at:team.end])
    struct.pack_into("<I", tail, len(tail) - 8 - TEAM_CLUB, club_index)
    struct.pack_into("<II", tail, len(tail) - 8, index, uid)
    return bytes(head) + b"\0" + b"\0\0" + b"\0" + b"\0" + b"\0\0" + bytes(tail)


def add(data: bytes, clubs: Records, teams: Records, club_bytes: bytes, team_bytes: bytes,
        count: int = 1) -> bytes:
    """Clubes no fim da lista de clubes e times no fim da lista de times (count de cada, na
    mesma ordem); contadores somados. A lista de times vem depois da de clubes no arquivo:
    grava os times primeiro."""
    out = bytearray(data)
    team_end = teams.end(len(teams.ends) - 1)
    out[team_end:team_end] = team_bytes
    struct.pack_into("<I", out, teams.count_at, len(teams.ends) + count)
    club_end = clubs.end(len(clubs.ends) - 1)
    out[club_end:club_end] = club_bytes
    struct.pack_into("<I", out, clubs.count_at, len(clubs.ends) + count)
    return bytes(out)


NEW_UID = 9_100_000             # UIDs dos clubes novos (o do teste 1 foi 9000001)
CLUBS_END_602 = 0x5B8590        # fim da lista de clubes no banco 6.0.2


def shift(data: bytes) -> int:
    """Quanto o que vem depois da lista de clubes (as tabelas de nomes) andou com os clubes
    novos: 0 no banco 6.0.2."""
    clubs = club_list(data)
    return clubs.end(len(clubs.ends) - 1) - CLUBS_END_602


@dataclass
class NewClub:
    name: str                   # nome longo
    short: str                  # nome curto: é por ele que o brasil_2026.plan acha o clube
    donor_uid: int              # clube do jogo copiado (nação, cidade, estádio, cores)
    state: int = NONE           # estadual do time (índice da competição); NONE = nenhum


def create(data: bytes, wanted: list[NewClub]) -> tuple[bytes, list[tuple[NewClub, int]]]:
    """Clubes novos, cada um com um time, nos fins das listas. O par que antecede o 1º clube e
    o 1º time novos é o do último registro de cada lista, que no banco 6.0.2 é o mesmo UID
    (0x0206D174): o "UID do repositório" (server_teams) do clube e do time novos fica igual,
    como nos outros clubes. Devolve o banco e (clube, UID) de cada um."""
    clubs, teams = club_list(data), team_list(data)
    if clubs.uid(data, len(clubs.ends) - 1) != teams.uid(data, len(teams.ends) - 1):
        raise ValueError("o último clube e o último time não têm o mesmo UID")
    index_of = {clubs.uid(data, i): i for i in range(len(clubs.ends))}
    club_bytes, team_bytes, made = b"", b"", []
    for k, club in enumerate(wanted):
        donor = index_of[club.donor_uid]
        n_at, _ = club_lists(data, clubs.start(donor), clubs.ends[donor])
        donor_team = struct.unpack_from("<I", data, n_at + 1)[0]
        team = parse_team(data, teams.start(donor_team), teams.end(donor_team))
        if team is None or team.end - team.tail_at != 57:
            raise ValueError(f"{club.short}: o time {donor_team} do clube copiado não tem o formato simples")
        club_index, team_index, uid = len(clubs.ends) + k, len(teams.ends) + k, NEW_UID + k
        club_bytes += clone_club(data, clubs, donor, uid, club.name, club.short, [team_index], club_index)
        team_bytes += clone_team(data, team, club_index, team_index, uid, club.state)
        made.append((club, uid))
    return add(data, clubs, teams, club_bytes, team_bytes, len(wanted)), made


SHEET = Path(__file__).resolve().parents[2] / "data" / "brasil" / "clubes" / "clubes_novos_2026.csv"


def load_sheet(data: bytes, path: Path = SHEET) -> list[NewClub]:
    """clubes_novos_2026.csv: clube_2026 (nome curto, o da series_2026.csv), nome_longo, uf e
    doador_uid (clube do jogo copiado). O time entra na 2ª divisão do estadual da UF: o
    estaduais_clubes.plan só enxerga times com estadual e põe na 1ª quem está na lista de 2026
    (na 1ª direto, o time sobrava no formato e o Brasil sumia do New Game, teste 1)."""
    from .estaduais_clubes import LOWER_ID, comp_index

    if not path.exists():
        return []
    out = []
    for row in csv.DictReader(path.open(encoding="utf-8-sig")):
        uf = row["uf"].strip()
        out.append(NewClub(row["nome_longo"].strip(), row["clube_2026"].strip(), int(row["doador_uid"]),
                           comp_index(data, LOWER_ID[uf]) if uf in LOWER_ID else NONE))
    return out


def with_new_clubs(data: bytes, path: Path = SHEET) -> bytes:
    """O banco com os clubes novos da planilha. É determinístico: o aplicar_brasil_2026.py grava
    isto no jogo e as outras etapas que leem o server_db original (workspace/baseline) chamam
    isto para ver os mesmos clubes e índices. Banco que já tem os clubes: volta como está."""
    clubs = club_list(data)
    if NEW_UID <= clubs.uid(data, len(clubs.ends) - 1) < NEW_UID + 10_000:
        return data
    wanted = load_sheet(data, path)
    return create(data, wanted)[0] if wanted else data
