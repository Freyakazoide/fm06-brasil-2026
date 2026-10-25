"""Dá jogadores de 2005 a mais aos clubes de 2026 que não têm onde encaixar o elenco.

    python scripts/reforcar_elencos.py            (simulação)
    python scripts/reforcar_elencos.py --apply    (grava o people_db.dat do jogo)

Cada jogador de 2026 ocupa um jogador de 2005 do clube (hospedeiro). Vários
clubes do FM06 têm poucos ou nenhum (Cuiabá 4, Red Bull Bragantino 14). Este
script muda, no people_db.dat, o clube do contrato de jogadores de clubes que
não usamos (primeiro os brasileiros fora de 2026, depois até 2 por clube
estrangeiro; nunca quem tem jogos pela seleção, que continuaria convocado pela
seleção dele) para esses clubes, até cada um ter vaga para o elenco de 2026
(limite --limite por clube). Os clubes da CONMEBOL de data/estrangeiros
(coletar_estrangeiros.py) entram do mesmo jeito: os que têm menos jogadores no banco que
o elenco de 2026 ganham doadores (os outros clubes desses países não doam ninguém, nem
os nossos). O .lnc e o gravar_atributos.py depois trocam nome, dados e
nacionalidade de cada um. Contrato e campo "time" mudam juntos, e quem chega com
contrato num clube e time de outro vai para o time do clube do contrato. O elenco que o
jogo mostra é a lista de jogadores do registro do time no server_db.dat
(elenco_times.py): ela muda junto, sobre o server_db que o aplicar_brasil_2026.py gravou
(rode este depois dele).

Entradas: workspace/elencos_2005.csv (live_player_editor --squads-all num New
Game), jogadores_2026.xlsx, identidade_fm06.csv. Parte sempre do people_db
original (cópia em workspace/baseline/people_db.original.dat, feita na
primeira vez). Depois: New Game, --squads-all de novo, montar_elencos.py.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import elenco_times, estaduais_clubes, estrangeiros, historico, people_contracts, server_teams  # noqa: E402

IDENTITIES = ROOT / "data" / "brasil" / "clubes" / "identidade_fm06.csv"
PLAYERS = ROOT / "data" / "brasil" / "jogadores" / "jogadores_2026.xlsx"
HOSTS = ROOT / "workspace" / "elencos_2005.csv"
HOSTS_BASE = ROOT / "workspace" / "elencos_2005_sem_reforco.csv"   # contagem de um jogo sem reforço
BACKUP = ROOT / "workspace" / "baseline" / "people_db.original.dat"
SERVER_BACKUP = ROOT / "workspace" / "baseline" / "server_db.original.dat"
REPORT = ROOT / "workspace" / "mods" / "reforcos.csv"
DONORS = ROOT / "workspace" / "mods" / "doadores.json"   # versão antiga: doadores de nacionalidade
PER_FOREIGN_CLUB = 2
PEOPLE_SHA256 = "B21DDF3417B2B2F715FA2DB008190334B888DC6436DC0DEDABB35FD96885DF4A"   # docs/reversing/people-db.md


def game_dir() -> Path:
    return Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"])


def _sheet_rows(path: Path = PLAYERS) -> list[dict]:
    rows = openpyxl.load_workbook(path, read_only=True)["Jogadores"].iter_rows(values_only=True)
    header = next(rows)
    return [dict(zip(header, r)) for r in rows]


def comissao_tables(server: bytes):
    from fm06patch.comissao import name_tables
    return name_tables(server)


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
    if hashlib.sha256(people).hexdigest().upper() != PEOPLE_SHA256:
        print(f"[AVISO] workspace/baseline/{BACKUP.name} não é o people_db de 12/10 (o do teste do Saviola): "
              "se foi copiado de um jogo já mexido, o reforço corrige os times, mas confira os elencos")
    server = (SERVER_BACKUP if SERVER_BACKUP.exists() else game / "data" / "db" / "server_db.dat").read_bytes()

    identities = list(csv.DictReader(IDENTITIES.open(encoding="utf-8-sig")))
    foreign = estrangeiros.identity_rows()          # clubes da CONMEBOL (vazio sem data/estrangeiros)
    ours = {int(r["uid_jogo"]) for r in identities + foreign}
    hosts = Counter(int(r["clube_uid"]) for r in csv.DictReader(args.hospedeiros.open(encoding="utf-8")))
    sheet = _sheet_rows()
    if foreign and estrangeiros.PLAYERS.exists():
        sheet += _sheet_rows(estrangeiros.PLAYERS)
    sizes = Counter(r["clube"] for r in sheet)
    indexes = people_contracts.brazil_club_indexes(server)
    brazil = {index: uid for uid, index in indexes.items()}
    abroad = estrangeiros.club_indexes(server, foreign) if foreign else {}   # UID do jogo -> índice
    abroad_clubs = {index: uid for uid, index in abroad.items()}
    found = people_contracts.contracts(people)
    # a contagem sem reforço (no jogo) é só dos clubes brasileiros de quando foi feita; dos
    # estrangeiros vale a do banco (os contratos com o clube)
    in_db = Counter(c.club for c in found.values() if c.club in abroad_clubs)
    for uid, index in abroad.items():
        hosts.setdefault(uid, in_db[index])
    # clubes que jogam um estadual: com certeza carregados (o par "00 BD 00 00 00" também pega
    # alguns estrangeiros, que o jogo não carrega)
    true = server_teams.true_uids(server)
    repo_of = {v: k for k, v in true.items()}
    playing = {true.get(t.club_uid) for t in estaduais_clubes.state_teams(server)}
    host_uids = {int(r["uid"]) for r in csv.DictReader(args.hospedeiros.open(encoding="utf-8"))}

    needs = []
    club_index = {**abroad, **indexes}
    for row in identities + foreign:
        uid, club = int(row["uid_jogo"]), row["clube_2026"]
        missing = min(sizes.get(club, 0), args.limite) - hosts.get(uid, 0)
        if missing > 0:
            if uid not in club_index:
                print(f"[AVISO] {club}: índice do clube {uid} não achado no server_db")
                continue
            needs.append((club, uid, missing))

    # doadores: brasileiros de clubes fora de 2026, depois até 2 por clube estrangeiro (fora
    # os clubes da CONMEBOL de 2026)
    donors = [c for c in found.values() if c.club in brazil and brazil[c.club] not in ours]
    taken: Counter = Counter()
    by_club: dict[int, list] = defaultdict(list)
    for c in found.values():
        if c.club not in brazil and c.club not in abroad_clubs:
            by_club[c.club].append(c)
    for club, people_of_club in sorted(by_club.items(), key=lambda kv: -len(kv[1])):
        donors += people_of_club[:PER_FOREIGN_CLUB]
    donors = [d for d in donors if d.uid not in host_uids]
    tables = comissao_tables(server)                # sem quem joga por seleção: o argentino da
    donors = [d for d in donors if not people_contracts.caps(people, d.at, tables)]   # seleção viraria brasileiro

    moves, report, pool = {}, [], iter(donors)
    for club, uid, missing in needs:
        for _ in range(missing):
            donor = next(pool, None)
            if donor is None:
                break
            moves[donor.uid] = club_index[uid]
            taken[club] += 1
            report.append({"jogador_uid": donor.uid, "clube_antigo_indice": donor.club,
                           "clube_2026": club, "clube_uid": uid})
    for club, uid, missing in needs:
        print(f"{club:32} {hosts.get(uid, 0):3} hospedeiros + {taken[club]:3} (faltavam {missing})")
    print(f"[OK] {len(moves)} jogadores movidos para {len(needs)} clubes ({len(donors)} doadores disponíveis)")

    # excedentes: jogadores de 2005 (do banco) além do elenco de 2026 ficariam no clube com o
    # nome de 2005; vão para clubes brasileiros fora de 2026 (nos estrangeiros ficam e ganham
    # um nome de hoje do país no montar_elencos.py)
    spare = [i for i, u in brazil.items() if u not in ours and u in playing]
    removed = 0
    for row in identities:
        uid, club = int(row["uid_jogo"]), row["clube_2026"]
        own = [c for c in found.values() if brazil.get(c.club) == uid and c.uid not in moves]
        extra = len(own) - sizes.get(club, 0)
        if sizes.get(club, 0) and extra > 0:
            for c in sorted(own, key=lambda c: c.until)[:extra]:   # quem tem contrato mais curto sai
                moves[c.uid] = spare[removed % len(spare)]
                removed += 1
    print(f"[OK] {removed} jogadores de 2005 que sobravam nos clubes de 2026 saíram para clubes fora de 2026")

    if not args.apply:
        print("\nSimulação. Para gravar, rode de novo com --apply.")
        return
    # o campo "time" do registro tem de ir junto com o clube do contrato: o time do clube no
    # server_db; sem ele, o dos jogadores do clube (que numa cópia mexida pode ser de outro)
    destinations = set(moves.values())
    teams = {club: team for club, team in people_contracts.club_teams(server).items() if club in destinations}
    if abroad:
        values = estrangeiros.team_values(server)
        teams.update({index: values[uid] for uid, index in abroad.items() if index in destinations and uid in values})
    teams.update({club: team for club, team in people_contracts.club_team_values(
        people, people_contracts.contracts(people, multi=True), destinations - set(teams), tables).items()})
    for club in destinations - set(teams):
        try:
            teams[club] = historico.team_index(server, repo_of[brazil[club]])   # estrangeiro: KeyError
        except (KeyError, ValueError):
            pass
    data, skipped = people_contracts.move(people, moves, found, server, teams)
    if skipped:
        print(f"[AVISO] {len(skipped)} jogadores não mudaram (registro ou time do clube não achado)")
    # contrato num clube e time de outro (cópia "original" feita de um banco já mexido por uma
    # versão antiga do reforço): o jogador vai para o time do clube do contrato
    wrong = people_contracts.wrong_teams(data, people_contracts.contracts(data, multi=True),
                                         people_contracts.club_teams(server), tables)
    if wrong:
        out = bytearray(data)
        for _, at, team in wrong:
            out[at:at + 4] = team.to_bytes(4, "little")
        data = bytes(out)
        print(f"[OK] {len(wrong)} jogadores estavam com o contrato num clube e no time de outro (a cópia "
              "original do people_db já vinha mexida); agora ficam no clube do contrato")
    # o elenco do jogo é a lista de jogadores do registro do time no server_db (elenco_times)
    club_uid = {**abroad_clubs, **brazil}
    stayed = set(skipped)
    list_moves = [elenco_times.Move(found[uid].index, club_uid[club], teams[club], elenco_times.PLAYERS)
                  for uid, club in moves.items() if uid not in stayed and club in club_uid]
    after = people_contracts.contracts(data, multi=True)
    for uid, _, team in wrong:
        club = struct.unpack_from("<I", data, after[uid].at)[0]
        if club in club_uid:
            list_moves.append(elenco_times.Move(after[uid].index, club_uid[club], team, elenco_times.PLAYERS))
    server_path = game / "data" / "db" / "server_db.dat"
    lists, missing = elenco_times.apply(server_path.read_bytes(), list_moves)
    server_path.write_bytes(lists)
    print(f"[OK] {len(list_moves) - len(missing)} jogadores mudados de elenco no {server_path.name}"
          + (f"; {len(missing)} sem o time do clube novo (ficam no elenco antigo)" if missing else ""))
    people_path.write_bytes(data)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with REPORT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(report[0]) if report else ["jogador_uid"])
        writer.writeheader()
        writer.writerows(report)
    DONORS.unlink(missing_ok=True)     # a nacionalidade vai pelo código da nação; não há mais doadores
    print(f"[OK] gravado {people_path}; lista em {REPORT}")
    print("Agora: New Game, --squads-all de novo, montar_elencos.py, gravar_atributos.py, copiar o .lnc e outro New Game.")


if __name__ == "__main__":
    main()
