"""Elenco e comissão de cada time no server_db.dat: quem aparece na lista do clube no jogo.

O registro do time (leitor TEAM, 0x00A1FA30) começa com o byte 0x0A e termina com o
próprio (índice, UID do clube); o índice é o valor do campo "time" das pessoas
(people_contracts.team_field). Depois do byte 0x0A vêm 61 bytes de campos fixos (u16
reputação em +3, u32 técnico em +23 = TEAM+0x70) e quatro listas de pessoas (o u32 é
o índice da pessoa, o do fim do registro dela no people_db: u16 ano, 00 00 00, u32
índice, u32 UID), quase sempre em ordem crescente:

    u8 n + n x u32    TEAM+0x74  fisioterapeutas e médicos (cargo 12)
    u16 n + n x u32   TEAM+0x80  jogadores
    u8 n + n x u32    TEAM+0x90  auxiliares e treinadores (cargos 20 e 2)
    u8 n + n x u32    TEAM+0x9C  vazia em todos os times do banco 6.0.2

O jogo monta o elenco por essas listas: mudar só o contrato e o campo "time" da pessoa
(como o reforço fazia até 24/10) deixava o jogador na lista do time antigo. O Warley
aparecia no Palmeiras com o Amapá na ficha, e os 31 jogadores levados para o Red Bull
Bragantino não entravam no elenco (o jogo completava com juniores inventados).
Conferido no banco 6.0.2: Palmeiras (time 297) com 106 jogadores, 7 fisioterapeutas e
médicos, 6 auxiliares e treinadores e o Leão em TEAM+0x70.
"""

from __future__ import annotations

import bisect
import re
import struct
from dataclasses import dataclass, field

PREFIX = 61                     # bytes de campos fixos depois do 0x0A
MAX_TEAMS = 100_000             # o banco 6.0.2 tem uns 20 mil times
MANAGER = 22                    # TEAM+0x70: u32 índice do técnico (FFFFFFFF = sem), 22 bytes depois do 0x0A + 1
NONE = 0xFFFFFFFF
REGION = (0xC00000, 0x1600000)  # registros dos times (o histórico de campeões desloca o arquivo)
PLAYERS, PHYSIOS, COACHES, SCOUTS = "jogadores", "fisioterapeutas", "treinadores", "outros"
LIST_OF_JOB = {12: PHYSIOS, 20: COACHES, 2: COACHES, 16: "tecnico"}   # olheiro (14) não fica em lista
_ORDER = (PHYSIOS, PLAYERS, COACHES, SCOUTS)
_WIDE = {PLAYERS}               # contagem em u16; as outras em u8


@dataclass
class Team:
    start: int                  # posição do 0x0A
    value: int                  # índice do time (valor do campo "time" das pessoas)
    manager: int
    uid: int = 0                # UID do clube (o do par que fecha o registro: Palmeiras 329)
    lists: dict[str, list[int]] = field(default_factory=dict)
    spans: dict[str, tuple[int, int]] = field(default_factory=dict)   # (início, fim) de cada lista no arquivo


def read_team(server: bytes, start: int) -> Team | None:
    """O registro que começa em ``start`` (o 0x0A), ou None se não parece um time."""
    if server[start:start + 2] != b"\x0a\x00" or start + PREFIX + 8 > len(server):
        return None
    value = struct.unpack_from("<I", server, start - 8)[0] + 1
    if value > MAX_TEAMS:
        return None
    team = Team(start, value, struct.unpack_from("<I", server, start + 1 + MANAGER)[0])
    at = start + 1 + PREFIX
    for name in _ORDER:
        wide = name in _WIDE
        count = struct.unpack_from("<H" if wide else "<B", server, at)[0]
        size = (2 if wide else 1) + 4 * count
        if count > (600 if wide else 80) or at + size > len(server):
            return None
        items = list(struct.unpack_from(f"<{count}I", server, at + size - 4 * count))
        if any(i > 2_000_000 and i != NONE for i in items):   # índices; FFFFFFFF aparece (Santo André)
            return None
        team.lists[name], team.spans[name] = items, (at, at + size)
        at += size
    closing = re.compile(re.escape(struct.pack("<I", value)) + rb"(....)\x0a\x00", re.S).search(server, at, at + 0x4000)
    if not closing:                                     # o par (índice, UID) que fecha este time
        return None
    team.uid = struct.unpack("<I", closing.group(1))[0]
    return team


def all_teams(server: bytes) -> list[Team]:
    """Todos os registros de time do banco (uns 19 mil no 6.0.2). Um registro só por clube:
    as equipes reserva e sub-20 do jogo não estão no banco."""
    lo, hi = REGION
    found: dict[tuple[int, int], Team] = {}
    for match in re.finditer(rb"\x0a\x00", server[lo:hi]):
        team = read_team(server, lo + match.start())
        if team:        # 3 times (172, 394, 452) têm antes um trecho que também parece time; o
            found[(team.value, team.uid)] = team    # de verdade é o segundo (as pessoas batem)
    return list(found.values())


@dataclass(frozen=True)
class Move:
    person: int                 # índice da pessoa (Contract.index)
    club: int                   # UID verdadeiro do clube novo (fecha o registro do time)
    team: int                   # valor do campo "time" do clube novo (people_contracts.club_teams)
    kind: str                   # PLAYERS, PHYSIOS, COACHES ou "tecnico"


def _target(teams: list[Team], by_uid: dict[int, list[Team]], move: Move) -> Team | None:
    found = by_uid.get(move.club, [])
    if len(found) > 1:
        found = [t for t in found if t.value == move.team]
    if not found:               # clube com outro clube no fim do registro (Corinthians)
        found = [t for t in teams if t.value == move.team]
    return found[0] if len(found) == 1 else None


def apply(server: bytes, moves: list[Move]) -> tuple[bytes, list[Move]]:
    """Tira cada pessoa das listas em que está (do tipo dela) e põe na do time novo; o
    técnico vai em TEAM+0x70 e sai do time antigo. As listas mudam de tamanho, então o
    arquivo é remontado do fim para o começo. Devolve o arquivo e os movimentos cujo time
    novo não foi achado (esses não mudam)."""
    teams = all_teams(server)
    by_uid: dict[int, list[Team]] = {}
    for team in teams:
        by_uid.setdefault(team.uid, []).append(team)
    where: dict[tuple[str, int], list[Team]] = {}
    for team in teams:
        for name, items in team.lists.items():
            for person in items:
                where.setdefault((name, person), []).append(team)
    managers = {team.manager: team for team in teams if team.manager != NONE}
    changed: dict[int, Team] = {}
    missing = []
    for move in moves:
        target = _target(teams, by_uid, move)
        if target is None:
            missing.append(move)
            continue
        if move.kind == "tecnico":
            old = managers.get(move.person)
            if old is not None and old is not target:
                old.manager = NONE
                changed[old.start] = old
            target.manager, managers[move.person] = move.person, target
            changed[target.start] = target
            continue
        for old in where.pop((move.kind, move.person), []):
            if old is not target and move.person in old.lists[move.kind]:
                old.lists[move.kind].remove(move.person)
                changed[old.start] = old
        items = target.lists[move.kind]
        if move.person not in items:
            if items == sorted(items):              # a maioria vem em ordem (a do Corinthians não)
                bisect.insort(items, move.person)
            else:
                items.append(move.person)
            changed[target.start] = target
        where[(move.kind, move.person)] = [target]
    out = bytearray(server)
    edits = []
    for team in changed.values():
        struct.pack_into("<I", out, team.start + 1 + MANAGER, team.manager)
        for name, (begin, end) in team.spans.items():
            items = team.lists[name]
            data = struct.pack("<H" if name in _WIDE else "<B", len(items)) + struct.pack(f"<{len(items)}I", *items)
            if data != bytes(out[begin:end]):
                edits.append((begin, end, data))
    for begin, end, data in sorted(edits, reverse=True):
        out[begin:end] = data
    return bytes(out), missing
