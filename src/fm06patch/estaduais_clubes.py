"""Participantes dos estaduais de 2026 no server_db.dat.

O estadual de cada clube fica no registro do time (offset STATE_FIELD a partir
do "0A 00"): índice, na tabela de competições do banco, da 1ª ou da 2ª
divisão do estado. O estadual de 2026 (0x00BB6290 -> 0x00AC6F70) junta todos
os times cujo TEAM+0x64 é aquela competição, sem limite de quantidade.

Lista de 2026: data/brasil/estaduais/clubes_2026_modelo.csv (uf, clube,
cidade). Clube que não existe no FM06: entra o de maior reputação do mesmo
estado que ainda não está na lista. Quem estava na 1ª divisão e não está na
lista vai para a 2ª.
"""

from __future__ import annotations

import csv
import re
import struct
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from .estaduais import ID as FIRST_ID
from .server_teams import TeamRecord, club_names

STATE_FIELD = 47
LOWER_ID = {
    "AC": 0x1A2B4, "AL": 0x1A2B3, "AM": 0x49C80, "AP": 0x4C769, "BA": 0x4B9AF, "CE": 0x4C76B,
    "DF": 0x4C76D, "ES": 0x4C76F, "GO": 0x4B9B1, "MA": 0x4C771, "MG": 0x4B9B3, "MS": 0x4C773,
    "MT": 0x4C775, "PA": 0x4C785, "PB": 0x4C777, "PE": 0x4B9B5, "PI": 0x4C779, "PR": 0x4B9B7,
    "RJ": 0x4CD6B, "RN": 0x4C77B, "RO": 0x4C77D, "RR": 0x4C77F, "RS": 0x49C7E, "SC": 0x4B9B9,
    "SE": 0x4C781, "SP": 0x4CD6C, "TO": 0x4C783,
}
CLUBS_CSV = Path(__file__).resolve().parents[2] / "data" / "brasil" / "estaduais" / "clubes_2026_modelo.csv"
UF_NAMES = {
    "AC": "acre", "AL": "alagoas", "AM": "amazonas", "AP": "amapa", "BA": "bahia", "CE": "ceara",
    "DF": "distrito federal", "ES": "espirito santo", "GO": "goias", "MA": "maranhao",
    "MG": "minas gerais", "MS": "mato grosso do sul", "MT": "mato grosso", "PA": "para",
    "PB": "paraiba", "PE": "pernambuco", "PI": "piaui", "PR": "parana", "RJ": "rio de janeiro",
    "RN": "rio grande do norte", "RO": "rondonia", "RR": "roraima", "RS": "rio grande do sul",
    "SC": "santa catarina", "SE": "sergipe", "SP": "sao paulo", "TO": "tocantins",
}
# siglas e palavras que não ajudam a reconhecer o clube
_NOISE = {"ec", "fc", "sc", "ac", "cr", "ce", "se", "aa", "ad", "ae", "ca", "cs", "clube", "esporte",
          "esportivo", "futebol", "club", "de", "do", "da", "dos", "das", "e"}
# nome de 2026 -> nome no FM06, quando as palavras não batem
ALIASES = {
    "Athletico-PR": "Atlético Paranaense",
    "Red Bull Bragantino": "Bragantino",
    "Desportiva Ferroviária": "Desportiva",
    "Sport": "Sport Recife",
    "Atlético de Cajazeiras": "Atlético Cajazeirense",
    "Sport Sinop": "Sinop",
}


def comp_index(data: bytes, comp_id: int) -> int:
    at = data.find(struct.pack("<I", comp_id), 0x5B0000, 0x5C0000)
    if at < 0:
        raise ValueError(f"competição {comp_id:#x} não está na tabela do banco")
    return struct.unpack_from("<I", data, at - 4)[0]


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    text = re.sub(r"\((\w\w)\)", r" \1 ", text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _words(text: str, uf: str) -> set[str]:
    words = set(normalize(text).split()) - _NOISE
    return words - {uf.lower()}


@dataclass
class StateEntry:
    uf: str
    clube: str
    cidade: str
    team: TeamRecord
    substitute: bool


def state_teams(data: bytes) -> list[TeamRecord]:
    """Todos os times com estadual: registro "0A 00" (UID do clube antes) com o
    campo do estadual num dos 54 índices. Varre o banco inteiro (o leitor por
    cabeçalho de clube perde 53 times de estadual)."""
    states = {comp_index(data, cid) for cid in FIRST_ID.values()}
    states |= {comp_index(data, cid) for cid in LOWER_ID.values()}
    teams = []
    at = data.find(b"\x0a\x00", 4)
    while 0 <= at < len(data) - STATE_FIELD - 4:
        if (data[at + 5:at + 7] == b"\x00\x00" and data[at + 38:at + 40] == b"\x10\x27"
                and struct.unpack_from("<I", data, at + STATE_FIELD)[0] in states):
            uid = struct.unpack_from("<I", data, at - 4)[0]
            division, last = struct.unpack_from("<II", data, at + 7)
            name, short = club_names(data, uid, len(data))
            teams.append(TeamRecord(offset=at, club_uid=uid, last_position=data[at + 2],
                                    reputation=struct.unpack_from("<H", data, at + 3)[0],
                                    division=division, last_division=last, name=name,
                                    short_name=short))
        at = data.find(b"\x0a\x00", at + 1)
    return teams


def state_of(data: bytes, team: TeamRecord) -> int:
    return struct.unpack_from("<I", data, team.offset + STATE_FIELD)[0]


def _exact(clube: str, uf: str, pool: list[TeamRecord]) -> TeamRecord | None:
    target = normalize(ALIASES.get(clube, clube))
    base = re.sub(rf"\s+{uf.lower()}$", "", target)
    for team in pool:
        names = {normalize(team.short_name), normalize(team.name)}
        names |= {re.sub(rf"\s+{uf.lower()}$", "", n) for n in names}
        if target in names or base in names:
            return team
    return None


def _match(clube: str, uf: str, pool: list[TeamRecord]) -> TeamRecord | None:
    clube = ALIASES.get(clube, clube)
    target = normalize(clube)
    base = re.sub(rf"\s+{uf.lower()}$", "", target)
    for team in pool:                                   # nome igual (curto ou longo)
        names = {normalize(team.short_name), normalize(team.name)}
        names |= {re.sub(rf"\s+{uf.lower()}$", "", n) for n in names}
        if target in names or base in names:
            return team
    wanted = _words(clube, uf)
    best, score = None, 0.0
    for team in pool:                                   # palavras em comum
        have = _words(team.short_name, uf) | _words(team.name, uf)
        if not wanted or not have:
            continue
        common = len(wanted & have)
        value = common / len(wanted)
        if common and value > score:
            best, score = team, value
    return best if score >= 0.99 else None


def plan(data: bytes, rows: list[dict] | None = None) -> tuple[list[StateEntry], dict[str, int]]:
    rows = rows if rows is not None else list(csv.DictReader(CLUBS_CSV.open(encoding="utf-8-sig")))
    teams = state_teams(data)
    first = {uf: comp_index(data, cid) for uf, cid in FIRST_ID.items()}
    lower = {uf: comp_index(data, cid) for uf, cid in LOWER_ID.items()}
    entries: list[StateEntry] = []
    counts: dict[str, int] = {}
    for uf in FIRST_ID:
        wanted = [r for r in rows if r["uf"].strip().upper() == uf]
        pool = [t for t in teams if state_of(data, t) in (first[uf], lower[uf])]
        used: set[int] = set()
        found: dict[int, TeamRecord] = {}
        for finder in (_exact, _match):                 # nome igual primeiro, depois palavras
            for i, row in enumerate(wanted):
                if i in found:
                    continue
                team = finder(row["clube"], uf, [t for t in pool if t.club_uid not in used])
                if team is not None:
                    found[i] = team
                    used.add(team.club_uid)
        missing = []
        for i, row in enumerate(wanted):
            if i in found:
                entries.append(StateEntry(uf, row["clube"], row.get("cidade", ""), found[i], False))
            else:
                missing.append(row)
        for row in missing:
            free = sorted((t for t in pool if t.club_uid not in used and t.short_name),
                          key=lambda t: -t.reputation)
            if not free:
                raise ValueError(f"{uf}: sem clube no banco para substituir {row['clube']}")
            used.add(free[0].club_uid)
            entries.append(StateEntry(uf, row["clube"], row.get("cidade", ""), free[0], True))
        counts[uf] = len(wanted)
    return entries, counts


def apply(data: bytes, entries: list[StateEntry]) -> bytes:
    out = bytearray(data)
    first = {uf: comp_index(data, cid) for uf, cid in FIRST_ID.items()}
    lower = {uf: comp_index(data, cid) for uf, cid in LOWER_ID.items()}
    chosen = {e.team.club_uid for e in entries}
    for team in state_teams(data):
        value = state_of(data, team)
        for uf in FIRST_ID:
            if value == first[uf] and team.club_uid not in chosen:
                struct.pack_into("<I", out, team.offset + STATE_FIELD, lower[uf])
    for e in entries:
        struct.pack_into("<I", out, e.team.offset + STATE_FIELD, first[e.uf])
    return bytes(out)


def write_report(path: Path, entries: list[StateEntry]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["uf", "clube_2026", "cidade", "tipo", "fm06_uid", "fm06_nome", "reputacao"])
        for e in entries:
            w.writerow([e.uf, e.clube, e.cidade, "substituto" if e.substitute else "equivalente",
                        e.team.club_uid, e.team.short_name, e.team.reputation])
