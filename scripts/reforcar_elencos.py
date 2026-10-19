"""Dá jogadores de 2005 a mais aos clubes de 2026 que não têm onde encaixar o elenco.

    python scripts/reforcar_elencos.py            (simulação)
    python scripts/reforcar_elencos.py --apply    (grava o people_db.dat do jogo)

Cada jogador de 2026 ocupa um jogador de 2005 do clube (hospedeiro). Vários
clubes do FM06 têm poucos ou nenhum (Cuiabá 4, Red Bull Bragantino 14). Este
script muda, no people_db.dat, o clube do contrato de jogadores de clubes que
não usamos (primeiro os brasileiros fora de 2026, depois até 2 por clube
estrangeiro) para esses clubes, até cada um ter vaga para o elenco de 2026
(limite --limite por clube). O injetor depois troca nome, dados e
nacionalidade de cada um.

Entradas: workspace/elencos_2005.csv (live_player_editor --squads-all num New
Game), jogadores_2026.xlsx, identidade_fm06.csv. Parte sempre do people_db
original (cópia em workspace/baseline/people_db.original.dat, feita na
primeira vez). Depois: New Game, --squads-all de novo, montar_elencos.py.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import people_contracts  # noqa: E402

IDENTITIES = ROOT / "data" / "brasil" / "clubes" / "identidade_fm06.csv"
PLAYERS = ROOT / "data" / "brasil" / "jogadores" / "jogadores_2026.xlsx"
HOSTS = ROOT / "workspace" / "elencos_2005.csv"
HOSTS_BASE = ROOT / "workspace" / "elencos_2005_sem_reforco.csv"   # contagem de um jogo sem reforço
BACKUP = ROOT / "workspace" / "baseline" / "people_db.original.dat"
SERVER_BACKUP = ROOT / "workspace" / "baseline" / "server_db.original.dat"
REPORT = ROOT / "workspace" / "mods" / "reforcos.csv"
DONORS = ROOT / "workspace" / "mods" / "doadores.json"
PER_FOREIGN_CLUB = 2


def game_dir() -> Path:
    return Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"])


def _sheet_rows() -> list[dict]:
    rows = openpyxl.load_workbook(PLAYERS, read_only=True)["Jogadores"].iter_rows(values_only=True)
    header = next(rows)
    return [dict(zip(header, r)) for r in rows]


def nationality_donors(people: bytes, found: dict, brazil: dict, ours: set, nations: set) -> tuple[dict, dict]:
    """Um doador de nacionalidade por nação, carregado no jogo: um jogador dessa nação
    que já joga num clube brasileiro, ou um que é levado para um clube brasileiro fora de
    2026 (as ligas da Ásia, África etc. não carregam, e o doador não estaria na memória).
    Devolve ({nação: UID}, {UID: índice do clube novo})."""
    spare = sorted(i for i, uid in brazil.items() if uid not in ours)
    by_code = people_contracts.nationalities(people)
    loose = people_contracts.contracts(people, multi=True)
    donors, moves = {}, {}
    for name in sorted(nations):
        code = people_contracts.NATION_CODES.get(name)
        candidates = [(uid, year) for uid, year in by_code.get(code, []) if uid in found] if code else []
        if code and not candidates:                     # só com mais de um bloco (empréstimo)
            candidates = [(uid, year) for uid, year in by_code.get(code, []) if uid in loose]
            found.update({uid: loose[uid] for uid, _ in candidates})
        if not candidates:
            continue
        in_brazil = [uid for uid, _ in candidates if found[uid].club in brazil]
        if in_brazil:
            donors[name] = in_brazil[0]
            continue
        uid = sorted(candidates, key=lambda c: abs(c[1] - 1982))[0][0]
        donors[name] = uid
        moves[uid] = spare[len(moves) % len(spare)]
    return donors, moves


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--hospedeiros", type=Path, default=None,
                        help="padrão: elencos_2005_sem_reforco.csv (cópia do primeiro elencos_2005.csv)")
    parser.add_argument("--limite", type=int, default=45, help="máximo de jogadores de 2026 por clube")
    args = parser.parse_args()

    if args.hospedeiros is None:
        if not HOSTS_BASE.exists():
            shutil.copy2(HOSTS, HOSTS_BASE)
            print(f"[OK] contagem sem reforço guardada em {HOSTS_BASE}")
        args.hospedeiros = HOSTS_BASE
    game = game_dir()
    people_path = game / "data" / "db" / "people_db.dat"
    if not BACKUP.exists():
        BACKUP.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(people_path, BACKUP)
        print(f"[OK] cópia do people_db original em {BACKUP}")
    people = BACKUP.read_bytes()
    server = (SERVER_BACKUP if SERVER_BACKUP.exists() else game / "data" / "db" / "server_db.dat").read_bytes()

    identities = list(csv.DictReader(IDENTITIES.open(encoding="utf-8-sig")))
    ours = {int(r["uid_jogo"]) for r in identities}
    hosts = Counter(int(r["clube_uid"]) for r in csv.DictReader(args.hospedeiros.open(encoding="utf-8")))
    sheet = _sheet_rows()
    sizes = Counter(r["clube"] for r in sheet)
    indexes = people_contracts.brazil_club_indexes(server)
    brazil = {index: uid for uid, index in indexes.items()}
    found = people_contracts.contracts(people)
    host_uids = {int(r["uid"]) for r in csv.DictReader(args.hospedeiros.open(encoding="utf-8"))}

    needs = []
    for row in identities:
        uid, club = int(row["uid_jogo"]), row["clube_2026"]
        missing = min(sizes.get(club, 0), args.limite) - hosts.get(uid, 0)
        if missing > 0:
            if uid not in indexes:
                print(f"[AVISO] {club}: índice do clube {uid} não achado no server_db")
                continue
            needs.append((club, uid, missing))

    # doadores: brasileiros de clubes fora de 2026, depois até 2 por clube estrangeiro
    donors = [c for c in found.values() if c.club in brazil and brazil[c.club] not in ours]
    taken: Counter = Counter()
    by_club: dict[int, list] = defaultdict(list)
    for c in found.values():
        if c.club not in brazil:
            by_club[c.club].append(c)
    for club, people_of_club in sorted(by_club.items(), key=lambda kv: -len(kv[1])):
        donors += people_of_club[:PER_FOREIGN_CLUB]
    nation_donors, pins = nationality_donors(people, found, brazil, ours,
                                             {r["nacionalidade"] for r in sheet if r["nacionalidade"] != "Brasil"})
    donors = [d for d in donors if d.uid not in host_uids and d.uid not in pins
              and d.uid not in nation_donors.values()]

    moves, report, pool = {}, [], iter(donors)
    for club, uid, missing in needs:
        for _ in range(missing):
            donor = next(pool, None)
            if donor is None:
                break
            moves[donor.uid] = indexes[uid]
            taken[club] += 1
            report.append({"jogador_uid": donor.uid, "clube_antigo_indice": donor.club,
                           "clube_2026": club, "clube_uid": uid})
    for club, uid, missing in needs:
        print(f"{club:28} {hosts.get(uid, 0):3} hospedeiros + {taken[club]:3} (faltavam {missing})")
    print(f"[OK] {len(moves)} jogadores movidos para {len(needs)} clubes ({len(donors)} doadores disponíveis)")
    print(f"[OK] doadores de nacionalidade: {len(nation_donors)} nações ({len(pins)} levados para clube brasileiro)")
    moves.update(pins)

    if not args.apply:
        print("\nSimulação. Para gravar, rode de novo com --apply.")
        return
    people_path.write_bytes(people_contracts.move(people, moves, found))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with REPORT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(report[0]) if report else ["jogador_uid"])
        writer.writeheader()
        writer.writerows(report)
    DONORS.write_text(json.dumps(nation_donors, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] gravado {people_path}; lista em {REPORT}; doadores em {DONORS}")
    print("Agora: New Game, --squads-all de novo, montar_elencos.py, copiar o .lnc, outro New Game, injetor.")


if __name__ == "__main__":
    main()
