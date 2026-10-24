"""Técnico e comissão técnica dos clubes no people_db.dat (FM06 6.0.2).

Registro da pessoa (staff e jogador), na ordem em que aparece no arquivo:

    u32 primeiro nome, u32 sobrenome, u32 nome comum (índices das tabelas de nomes
    do server_db; FFFFFFFF = sem), u32 tamanho + nome completo UTF-16 (+ 00 00 se
    houver), u16 dia do ano e u16 ano do nascimento, 00, u32 nação (0xBD Brasil),
    u32 seleção, u32 jogos, u32, 00, data, u32 time (historico.team_index), u8 cargo,
    data de chegada, ...
    ... bloco de contrato: 64, u32 pessoa, 00, u32 clube (índice), u32 salário,
    u16 dia e u16 ano do fim (0 / 1900 = sem data), 02 00 00 00 ...
    ... u32 pessoa, u32 UID (o UID do CHANGE_PLAYER_NAME), ...

Cargo (u8): 16 técnico, 20 auxiliar, 2 treinador (preparador físico, de
goleiros...), 12 fisioterapeuta / médico, 14 olheiro; 1 é jogador. Conferido com
o banco: Internacional (Muricy 16, Tata 20, Paulo Paixão 2, César Abs 12),
São Paulo (Paulo Autuori 16, Milton Cruz 20), Flamengo (Andrade 16, Adílio 20).

O CHANGE_PLAYER_NAME do .lnc vale para staff (o executor, 0x00AAA4B0, pega os
dados da pessoa pelo mesmo método para jogador e não jogador).
"""

from __future__ import annotations

import datetime as dt
import re
import struct
import unicodedata
from dataclasses import dataclass, field

T2 = (0x043902BA, 0x0480F3D6, 17)        # (início, fim, tamanho): toda pessoa (índice, UID, 9 bytes)
T3 = (0x0480F422, 0x05AFA48A, 89)        # jogadores
PEOPLE_END = 0x043902BA
NAME_TABLES = ((0x5C0000, 0x85D000), (0x85D000, 0xDE5A60), (0xDE5A60, 0xEE7000))   # primeiro, sobrenome, comum
_CONTRACT = re.compile(rb"\x64(....)\x00(....)(....)(..)(..)\x02\x00\x00\x00", re.S)
NONE = 0xFFFFFFFF
SHIFT = 20                               # o motor está 20 anos antes da tela

MANAGER, ASSISTANT, COACH, PHYSIO, SCOUT = 16, 20, 2, 12, 14
JOB_OF = {"tecnico": MANAGER, "auxiliar": ASSISTANT, "preparador": COACH, "analista": COACH,
          "medico": PHYSIO, "olheiro": SCOUT}
# quantos de cada cargo um clube pode receber de clubes fora de 2026, quando o dele não basta
DONOR_LIMIT = {MANAGER: 1, ASSISTANT: 3, COACH: 5, PHYSIO: 5, SCOUT: 2}

# código da nação no people_db. Europa (0x81..) e CONMEBOL (0xBB..) seguem a ordem alfabética
# em inglês; conferido pelas tabelas de nomes do server_db (cada nome traz a nação)
NATION = {
    "ARG": 0xBB, "BOL": 0xBC, "BRA": 0xBD, "CHI": 0xBE, "CHL": 0xBE, "COL": 0xBF, "ECU": 0xC0,
    "PAR": 0xC1, "PRY": 0xC1, "PER": 0xC2, "URU": 0xC3, "URY": 0xC3, "VEN": 0xC4,
    "POR": 0xA2, "PRT": 0xA2, "ESP": 0xAA, "FRA": 0x8F, "ENG": 0x8B, "GBR": 0x8B, "NED": 0x9E, "NLD": 0x9E,
    "ITA": 0x96, "GER": 0x91, "DEU": 0x91, "UKR": 0xAE, "CRO": 0x87, "HRV": 0x87, "DEN": 0x8A, "DNK": 0x8A,
    "SWE": 0xAB, "SUI": 0xAC, "CHE": 0xAC, "GRE": 0x92, "GRC": 0x92, "HUN": 0x93, "POL": 0xA1, "ROU": 0xA4,
    "RUS": 0xA5, "SCO": 0xA7, "TUR": 0xAD, "BUL": 0x86, "BGR": 0x86,
    "MEX": 0x6D, "PAN": 0x70, "USA": 0x78,
    "ANG": 0x01, "AGO": 0x01, "CMR": 0x06, "GHA": 0x10, "CIV": 0x13, "GUI": 0x11, "GIN": 0x11,
    "MLI": 0x1A, "MAR": 0x1D, "MOZ": 0x1E, "NGA": 0x21, "SEN": 0x24, "COD": 0x30,
}
COUNTRY = {"brazil": "BRA", "brasil": "BRA", "portugal": "POR", "argentina": "ARG", "uruguay": "URU",
           "paraguay": "PAR", "chile": "CHI", "colombia": "COL", "spain": "ESP", "italy": "ITA",
           "france": "FRA", "netherlands": "NED", "germany": "GER", "ukraine": "UKR", "venezuela": "VEN",
           "ecuador": "ECU", "peru": "PER", "bolivia": "BOL", "england": "ENG", "mexico": "MEX"}


def nation_code(text: str) -> int | None:
    text = (text or "").strip()
    return NATION.get(text.upper()) or NATION.get(COUNTRY.get(text.lower(), ""))


@dataclass
class Staff:
    uid: int
    pid: int
    club: int            # índice do clube do contrato
    job: int
    name: str
    born: tuple[int, int]
    nation: int
    names_at: int        # posição do u32 do primeiro nome
    born_at: int         # posição do u16 dia do nascimento (nação em +5)
    team_at: int         # posição do u32 time (cargo em +4)
    contract_at: int     # posição do 0x64 do contrato (clube em +6)


def _name_entries(server: bytes, lo: int, hi: int):
    """Tabela de nomes: u32 tamanho, UTF-16, 00 00, u16 uso, u32 nação, u32 índice, u32 UID, 00.
    Gera (índice, nome, uso, nação)."""
    at = lo
    while at < hi:
        size = struct.unpack_from("<I", server, at)[0]
        end = at + 4 + 2 * size
        if size > 90 or server[end:end + 2] != b"\0\0" or server[end + 16] != 0:
            at += 1
            continue
        usage, nation, index = struct.unpack_from("<HII", server, end + 2)
        if nation > 400:
            at += 1
            continue
        try:
            text = server[at + 4:end].decode("utf-16-le")
        except UnicodeDecodeError:
            at += 1
            continue
        yield index, text, usage, nation
        at = end + 17


def _walk_names(server: bytes, lo: int, hi: int) -> dict[int, str]:
    out: dict[int, str] = {}
    for index, text, _, _ in _name_entries(server, lo, hi):
        out.setdefault(index, text)
    return out


def names_by_nation(server: bytes) -> dict[tuple[str, int], dict[str, int]]:
    """(tabela, nação) -> {nome: uso} dos primeiros nomes e sobrenomes do banco (no formato do
    nomes_regens.load_sheet): nomes de cada país para quem não tem nome de hoje na planilha."""
    out: dict[tuple[str, int], dict[str, int]] = {}
    for kind, (lo, hi) in zip(("first", "second"), NAME_TABLES):
        for _, text, usage, nation in _name_entries(server, lo, hi):
            if text.strip() and '"' not in text:
                names = out.setdefault((kind, nation), {})
                names[text] = names.get(text, 0) + max(1, usage)
    return out


def name_tables(server: bytes) -> tuple[dict[int, str], dict[int, str], dict[int, str]]:
    return tuple(_walk_names(server, lo, hi) for lo, hi in NAME_TABLES)


def _uids(people: bytes, table) -> set[int]:
    start, end, size = table
    return {struct.unpack_from("<I", people, at + 4)[0] for at in range(start, end, size)}


# fim do registro de uma pessoa: u16 ano, 00 00 00, u32 índice, u32 UID
_RECORD_END = re.compile(rb"[\x6c-\xe0]\x07\x00\x00\x00(....)(....)", re.S)


def _record_start(people: bytes, pos: int, back: int) -> int:
    """Onde começa o registro que contém ``pos``: logo depois do fim do registro anterior.
    Sem esse limite, a busca dos nomes para trás pode cair no registro da pessoa anterior
    (e o campo "time" gravado é o dela: ela vai para o time novo com o contrato antigo,
    o clube do contrato fica nulo no jogo e ele trava)."""
    floor = max(pos - back, 0)
    for match in _RECORD_END.finditer(people, floor, pos):
        index, uid = struct.unpack("<II", match.group(1) + match.group(2))
        if index < 2_000_000 and 0 < uid < 100_000_000:
            floor = match.end()
    return floor


def _names_before(people: bytes, pos: int, tables, back: int = 0x800) -> int | None:
    first, second, common = tables
    for at in range(pos - 20, _record_start(people, pos, back) - 1, -1):
        f, s, c, n = struct.unpack_from("<IIII", people, at)
        if n > 90 or f not in first or s not in second or (c != NONE and c not in common):
            continue
        born = at + 16 + 2 * n + (2 if n else 0)
        if n and people[born - 2:born] != b"\0\0":
            continue
        day, year = struct.unpack_from("<HH", people, born)
        if day <= 365 and 1900 <= year <= 2000 and people[born + 4] == 0:
            return at
    return None


def _staff(people: bytes, tables, persons: set[int], players: set[int], pid: int, at: int, club: int
           ) -> Staff | None:
    """A pessoa do bloco de contrato em ``at`` (u32 pessoa e u32 UID logo depois do contrato)."""
    needle = struct.pack("<I", pid)
    uid, probe = None, people.find(needle, at + 10, at + 0x400)
    while probe >= 0:
        value = struct.unpack_from("<I", people, probe + 4)[0]
        if value in persons and people[probe - 3:probe] == b"\0\0\0":
            uid = value
            break
        probe = people.find(needle, probe + 1, at + 0x400)
    if uid is None or uid in players:
        return None
    names_at = _names_before(people, at, tables)
    if names_at is None:
        return None
    f, s, c, n = struct.unpack_from("<IIII", people, names_at)
    born_at = names_at + 16 + 2 * n + (2 if n else 0)
    team_at = born_at + 9 + 17
    name = tables[2].get(c) if c != NONE else None
    name = name or f"{tables[0].get(f, '')} {tables[1].get(s, '')}".strip()
    return Staff(uid, pid, club, people[team_at + 4], name, struct.unpack_from("<HH", people, born_at),
                 struct.unpack_from("<I", people, born_at + 5)[0], names_at, born_at, team_at, at)


def read_staff(people: bytes, server: bytes) -> list[Staff]:
    """Quem tem contrato e não é jogador (um bloco de contrato só)."""
    tables = name_tables(server)
    persons, players = _uids(people, T2), _uids(people, T3)
    blocks: dict[int, list] = {}
    for match in _CONTRACT.finditer(people, 0, PEOPLE_END):
        pid, club = struct.unpack("<II", match.group(1) + match.group(2))
        day, year = struct.unpack("<HH", match.group(4) + match.group(5))
        if day <= 365 and (year == 1900 or 2004 <= year <= 2016) and club < 60000:
            blocks.setdefault(pid, []).append((match.start(), club))
    staff = []
    for pid, found in blocks.items():
        if len(found) == 1:
            person = _staff(people, tables, persons, players, pid, *found[0])
            if person:
                staff.append(person)
    return staff


# contrato com a seleção: 64, u32 pessoa, 01 (em vez do 00 do clube), u32 código da nação
_NATIONAL = re.compile(rb"\x64(....)\x01([\x00-\xff]\x00\x00\x00)", re.S)


def read_national_managers(people: bytes, server: bytes) -> dict[int, list[Staff]]:
    """Código da nação -> técnico(s) da seleção (Parreira no Brasil, Pekerman na Argentina)."""
    tables = name_tables(server)
    persons, players = _uids(people, T2), _uids(people, T3)
    found: dict[int, list[Staff]] = {}
    for match in _NATIONAL.finditer(people, 0, PEOPLE_END):
        pid, nation = struct.unpack("<II", match.group(1) + match.group(2))
        person = _staff(people, tables, persons, players, pid, match.start(), nation)
        if person and person.job == MANAGER:
            found.setdefault(nation, []).append(person)
    return found


@dataclass
class Person:
    uid: int
    name: str            # primeiro nome + sobrenome
    common: str | None   # nome comum ("Tite"), se houver
    born: tuple[int, int]
    nation: int


# fim da parte comum do registro: u16 ano, 00 00 00, u32 índice, u32 UID, u32, u8 tipo
_PERSON_END = re.compile(rb"[\x6c-\xe0]\x07\x00\x00\x00(....)(....)....[\x01\x02\x04]", re.S)


def read_people(people: bytes, server: bytes) -> list[Person]:
    """Todas as pessoas do people_db (jogadores, staff e árbitros) com nome e nascimento."""
    tables = name_tables(server)
    found = []
    for match in _PERSON_END.finditer(people, 0, PEOPLE_END):
        index, uid = struct.unpack("<II", match.group(1) + match.group(2))
        if not (index < 2_000_000 and 0 < uid < 100_000_000):
            continue
        at = _names_before(people, match.start() + 5, tables, back=0x300)
        if at is None:
            continue
        first, second, common, size = struct.unpack_from("<IIII", people, at)
        born = at + 16 + 2 * size + (2 if size else 0)
        found.append(Person(uid, f"{tables[0].get(first, '')} {tables[1].get(second, '')}".strip(),
                            tables[2].get(common) if common != NONE else None,
                            struct.unpack_from("<HH", people, born), struct.unpack_from("<I", people, born + 5)[0]))
    return found


def _plain(name: str) -> str:
    return unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().casefold().strip()


def namesakes(persons: list[Person], wanted: list[tuple[set[str], str]], taken: set[int]) -> list[Person]:
    """As pessoas de 2005 que são alguém de 2026 (mesmo nome e mesma data de nascimento de
    verdade: o Ancelotti técnico do Milan, o Forlán jogador do Villarreal) e que ninguém
    ocupou. ``wanted``: (nomes, nascimento AAAA-MM-DD) de quem está no jogo em 2026;
    ``taken``: UIDs que já ganham outro nome. No banco de 2005 o nascimento é o real."""
    by_key: dict[tuple[str, int, int], list[Person]] = {}
    for person in persons:
        for name in {_plain(person.name), _plain(person.common or "")} - {""}:
            by_key.setdefault((name, *person.born), []).append(person)
    found: dict[int, Person] = {}
    for names, born in wanted:
        try:
            date = dt.date.fromisoformat(born[:10])
        except ValueError:
            continue
        for name in {_plain(n) for n in names} - {""}:
            for person in by_key.get((name, date.timetuple().tm_yday - 1, date.year), []):
                if person.uid not in taken:
                    found[person.uid] = person
    return list(found.values())


@dataclass
class Wanted:
    club_uid: int        # UID do clube no jogo (identidade)
    clube: str
    cargo: str
    nome: str
    nacionalidade: str = ""
    nascimento: str = ""   # AAAA-MM-DD


@dataclass
class Plan:
    renames: list[tuple[Staff, Wanted]] = field(default_factory=list)
    moves: list[tuple[Staff, int, int]] = field(default_factory=list)      # (pessoa, clube, time)
    report: list[str] = field(default_factory=list)
    fillers: list[tuple[Staff, tuple[str, str, str]]] = field(default_factory=list)   # quem sobra: nome de hoje


def plan(staff: list[Staff], wanted: list[Wanted], club_index: dict[int, int], team_index: dict[int, int],
         spare_clubs: set[int], foreign_clubs: set[int] = frozenset()) -> Plan:
    """club_index / team_index: UID do clube -> índice do clube (contrato) / valor do campo time
    do registro da pessoa (o que o staff do clube já tem; sem staff, historico.team_index).
    spare_clubs: índices dos clubes brasileiros fora de 2026 (doadores); depois deles, um por
    clube de foreign_clubs que tem mais de um no cargo (os auxiliares dos brasileiros acabam)."""
    result = Plan()
    by_club: dict[int, dict[int, list[Staff]]] = {}
    for person in staff:
        by_club.setdefault(person.club, {}).setdefault(person.job, []).append(person)
    donors = {job: [p for club in sorted(spare_clubs) for p in by_club.get(club, {}).get(job, [])]
                   + [by_club[club][job][-1] for club in sorted(foreign_clubs)
                      if len(by_club.get(club, {}).get(job, [])) > 1]
              for job in DONOR_LIMIT}
    grouped: dict[int, list[Wanted]] = {}
    for row in wanted:
        grouped.setdefault(row.club_uid, []).append(row)
    for club_uid, rows in grouped.items():
        club = club_index.get(club_uid)
        if club is None:
            result.report.append(f"{rows[0].clube}: clube sem índice no banco")
            continue
        notes = []
        for job in (MANAGER, ASSISTANT, COACH, PHYSIO, SCOUT):
            targets = [r for r in rows if JOB_OF.get(r.cargo) == job]
            slots = list(by_club.get(club, {}).get(job, []))
            borrowed = 0
            while len(slots) < len(targets) and borrowed < DONOR_LIMIT[job] and donors[job]:
                donor = donors[job].pop(0)
                result.moves.append((donor, club, team_index[club_uid]))
                slots.append(donor)
                borrowed += 1
            for person, row in zip(slots, targets):
                result.renames.append((person, row))
            if targets:
                notes.append(f"{len(targets)}x{job}" + (f" (+{borrowed} de fora)" if borrowed else "")
                             + (f" ({len(targets) - len(slots)} sem vaga)" if len(slots) < len(targets) else ""))
        result.report.append(f"{rows[0].clube}: " + ", ".join(notes))
    return result


def split_name(full: str) -> tuple[str, str, str]:
    """(primeiro, comum, sobrenome) para o CHANGE_PLAYER_NAME."""
    words = full.replace('"', "").split()
    if not words:
        return "", "", ""
    if len(words) == 1:
        return words[0], words[0], ""
    if len(words) == 2:
        return words[0], "", words[1]
    return words[0], " ".join(words), words[-1]


def engine_birth(date: str) -> tuple[int, int] | None:
    """Data real -> (dia do ano base 0, ano) no motor (20 anos antes)."""
    try:
        real = dt.date.fromisoformat(date)
    except ValueError:
        return None
    try:
        shifted = real.replace(year=real.year - SHIFT)
    except ValueError:                    # 29/2
        shifted = real.replace(year=real.year - SHIFT, day=28)
    return shifted.timetuple().tm_yday - 1, shifted.year


def person_index(people: bytes, person: Staff) -> int | None:
    """Índice da pessoa (o do par que fecha o registro, depois do contrato): é o que as
    listas do time no server_db guardam (elenco_times.py)."""
    match = _RECORD_END.search(people, person.contract_at, person.contract_at + 0x400)
    if not match:
        return None
    index, uid = struct.unpack("<II", match.group(1) + match.group(2))
    return index if uid == person.uid else None


def apply(people: bytes, result: Plan) -> bytes:
    out = bytearray(people)
    for person, club, team in result.moves:
        struct.pack_into("<I", out, person.contract_at + 6, club)
        struct.pack_into("<I", out, person.team_at, team)
    for person, row in result.renames:
        born = engine_birth(row.nascimento) if row.nascimento else None
        if born:
            struct.pack_into("<HH", out, person.born_at, *born)
        code = nation_code(row.nacionalidade)
        if code is not None:
            struct.pack_into("<I", out, person.born_at + 5, code)
    return bytes(out)


def lnc_text(result: Plan) -> str:
    lines = ["# FM06 Brasil 2026: técnicos e comissão técnica (scripts/aplicar_comissao.py)"]
    for person, row in result.renames:
        first, common, second = split_name(row.nome)
        lines.append(f'"CHANGE_PLAYER_NAME"\t{person.uid}\t"{first}"\t"{common}"\t"{second}"')
    for person, (first, common, second) in result.fillers:
        lines.append(f'"CHANGE_PLAYER_NAME"\t{person.uid}\t"{first}"\t"{common}"\t"{second}"')
    return "\r\n".join(lines) + "\r\n"


def fill_names(result: Plan, staff: list[Staff], clubs: set[int], name) -> None:
    """Quem fica num clube de 2026 sem nome de 2026 (staff de 2005 que sobra) ganha um nome de
    hoje: name(uid) -> (primeiro, comum, sobrenome)."""
    named = {person.uid for person, _ in result.renames}
    moved = {person.uid: club for person, club, _ in result.moves}
    for person in staff:
        if person.uid not in named and moved.get(person.uid, person.club) in clubs:
            result.fillers.append((person, tuple(n.replace('"', "") for n in name(person.uid))))
