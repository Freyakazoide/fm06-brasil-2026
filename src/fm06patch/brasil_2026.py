"""Estrutura do futebol brasileiro em 2026 aplicada ao banco do FM06.

Entradas (em data/brasil):
    series_2026.csv        série, estado e nome de cada clube em 2026
    equivalencias_fm06.csv nome do clube no FM06 (vazio = não existe no jogo)

Clube sem equivalente vira substituto: o clube brasileiro de maior reputação
ainda não usado, preenchendo na ordem Série A, B, C e D. A Série D é completada
com substitutos até 96 clubes.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .server_teams import DIVISIONS, NONE, TeamRecord, find_brazil_teams, write_team

SERIES = ("A", "B", "C", "D")
SIZES = {"A": 20, "B": 20, "C": 20, "D": 96}
# Índice na tabela de competições do server_db de cada série de 2026
# (com os patches serie_c_nova e serie_d_96 no fm.exe).
INDEX = {"A": DIVISIONS["A"], "B": DIVISIONS["B"], "C": DIVISIONS["NOVA_C"], "D": DIVISIONS["C"]}
COMP_ID = {"A": 102423, "B": 107191, "C": 319191, "D": 107192}
# Outros nomes atualizados (ID da competição -> nome, nome curto, nome longo)
OTHER_NAMES = {
    1301385: ("Copa do Mundo da FIFA", "Copa do Mundo", "Copa do Mundo da FIFA"),   # WC_WORLD_CUP
}


@dataclass
class Placement:
    serie: str
    clube: str          # nome em 2026 ("" para vaga extra)
    estado: str
    team: TeamRecord
    kind: str           # "equivalente" ou "substituto"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def plan(data: bytes, data_dir: Path) -> list[Placement]:
    clubs = read_csv(data_dir / "series_2026.csv")
    equivalent = {row["clube"]: row["fm06"] for row in read_csv(data_dir / "equivalencias_fm06.csv")}
    teams = find_brazil_teams(data)
    by_name: dict[str, list[TeamRecord]] = {}
    for team in teams:
        by_name.setdefault(team.short_name, []).append(team)

    used: set[int] = set()
    exact: dict[int, TeamRecord] = {}
    for number, row in enumerate(clubs):
        name = equivalent.get(row["clube"], row["clube"])
        if not name:
            continue
        found = by_name.get(name, [])
        if len(found) != 1:
            raise KeyError(f"{row['clube']}: '{name}' achou {len(found)} clubes no FM06")
        if found[0].club_uid in used:
            raise KeyError(f"{row['clube']}: '{name}' já foi usado por outro clube")
        exact[number] = found[0]
        used.add(found[0].club_uid)

    pool = sorted((t for t in teams if t.club_uid not in used), key=lambda t: -t.reputation)

    def substitute() -> TeamRecord:
        team = pool.pop(0)
        used.add(team.club_uid)
        return team

    placements = []
    for serie in SERIES:
        rows = [(n, r) for n, r in enumerate(clubs) if r["serie"] == serie]
        for number, row in rows:
            if number in exact:
                placements.append(Placement(serie, row["clube"], row["estado"], exact[number], "equivalente"))
            else:
                placements.append(Placement(serie, row["clube"], row["estado"], substitute(), "substituto"))
        for _ in range(SIZES[serie] - len(rows)):
            placements.append(Placement(serie, "", "", substitute(), "substituto"))
    return placements


def apply(data: bytes, placements: list[Placement]) -> bytes:
    """Coloca cada time na sua série e tira das divisões nacionais os outros."""
    buffer = bytearray(data)
    chosen = {p.team.club_uid for p in placements}
    national = set(INDEX.values())
    for team in find_brazil_teams(data):
        if team.club_uid not in chosen and team.division in national:
            team.division = NONE
            write_team(buffer, team)
    for placement in placements:
        placement.team.division = INDEX[placement.serie]
        write_team(buffer, placement.team)
    return bytes(buffer)


def apply_last_season(data: bytes, placements: list[Placement], path: Path) -> tuple[bytes, list[str]]:
    """Classificação real de 2025 (serie, posicao, clube com o nome de 2026) nos campos
    "temporada passada" do time (TEAM+0x5C divisão, TEAM+0x60 posição). Sem isso o jogo
    usa a de 2005 do banco do FM06 (vagas da 1ª Libertadores, Sul-Americana, Copa do
    Brasil). Divisão de 2025 pelo mesmo índice das séries de 2026."""
    if not path.exists():
        return data, []
    buffer = bytearray(data)
    by_name = {p.clube: p.team for p in placements if p.clube}
    national = set(INDEX.values())
    for team in find_brazil_teams(data):
        if team.last_division in national:
            team.last_division, team.last_position = NONE, 0
            write_team(buffer, team)
    missing = []
    teams = find_brazil_teams(data)
    for team in teams:                                  # clube fora das séries de 2026: nome no FM06
        by_name.setdefault(team.short_name, team)
    for row in read_csv(path):
        name = row["clube"].strip()
        team = by_name.get(name) or by_name.get(name.replace("-", " (") + ")" if "-" in name else name)
        if team is None:
            missing.append(row["clube"])
            continue
        team.last_division = INDEX[row["serie"].strip().upper()]
        team.last_position = int(row["posicao"])
        write_team(buffer, team)
    return bytes(buffer), missing


def write_report(path: Path, placements: list[Placement]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["serie", "clube_2026", "estado", "tipo", "fm06_uid", "fm06_nome", "reputacao"])
        for p in placements:
            writer.writerow([p.serie, p.clube, p.estado, p.kind, p.team.club_uid, p.team.short_name, p.team.reputation])


def lnc_text() -> str:
    """Nomes das competições (arquivo .lnc, UTF-16)."""
    lines = ["# FM06 Brasil 2026: nomes das séries nacionais", "# Comando\tID\tNome\tIdioma"]
    for serie in SERIES:
        comp = COMP_ID[serie]
        lines += [
            f'"COMP_NAME_CHANGE"\t{comp}\t"Série {serie}"\t""',
            f'"COMP_SHORT_NAME_CHANGE"\t{comp}\t"Série {serie}"\t""',
            f'"COMP_LONG_NAME_CHANGE"\t{comp}\t"Campeonato Brasileiro Série {serie}"\t""',
        ]
    for comp, (name, short, long) in OTHER_NAMES.items():
        lines += [
            f'"COMP_NAME_CHANGE"\t{comp}\t"{name}"\t""',
            f'"COMP_SHORT_NAME_CHANGE"\t{comp}\t"{short}"\t""',
            f'"COMP_LONG_NAME_CHANGE"\t{comp}\t"{long}"\t""',
        ]
    return "\r\n".join(lines) + "\r\n"
