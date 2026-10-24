"""Elencos e técnicos de 2026 da primeira divisão dos outros países da CONMEBOL.

    python scripts\\coletar_estrangeiros.py [--cache workspace\\sofascore] [--pais AR UY ...]
                                          [--torneio AR=155 ...] [--so-montar]

Precisa de internet (o Sofascore não responde de onde o Claude roda): rode no PC.
1. Acha no Sofascore a primeira divisão de 2026 de Argentina, Uruguai, Colômbia,
   Paraguai, Equador, Chile, Peru, Bolívia e Venezuela (pelo id conhecido do torneio,
   conferido pelo país; senão pela categoria do país; se escolher o torneio errado,
   passe --torneio PAIS=id) e os clubes da tabela.
2. Baixa o elenco, o técnico, as transferências, a visão geral dos atributos e a
   seleção de cada jogador (o mesmo do coletar_sofascore.py; o cache vale para as
   próximas vezes).
3. Monta data\\estrangeiros (scripts/montar_estrangeiros.py): o clube do FM06 de cada
   clube de 2026, os jogadores, os técnicos e as carreiras.

Grava <cache>\\times_estrangeiros.json. Depois: python scripts\\aplicar_tudo.py (completo).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from coletar_comissao import manager  # noqa: E402
from coletar_sofascore import SMALL_SQUAD, YEAR, Sofascore, lineup_players  # noqa: E402
from fm06patch.estrangeiros import NATIONS, display_name  # noqa: E402

# id do torneio da primeira divisão no Sofascore (conferido pelo país do torneio; se não
# conferir, procura na categoria do país pelo nome abaixo)
KNOWN = {"AR": 155, "UY": 278, "CO": 11539, "PY": 11541, "EC": 240, "CL": 11653, "PE": 406, "BO": 16736, "VE": 231}
# nome da primeira divisão na categoria do país (o de mais seguidores, se mais de um casar)
FIRST_DIVISION = {
    "AR": r"liga profesional|primera divisi",
    "UY": r"primera divisi|liga auf|campeonato uruguayo",
    "CO": r"primera a|liga betplay|liga dimayor",
    "PY": r"primera divisi|divisi[oó]n profesional|copa de primera",
    "EC": r"ligapro|serie a",
    "CL": r"primera divisi|liga de primera|campeonato nacional",
    "PE": r"liga 1|primera divisi",
    "BO": r"divisi[oó]n profesional|primera divisi|liga de f[uú]tbol profesional",
    "VE": r"liga futve|primera divisi",
}
NOT_FIRST = re.compile(r"(?i)\b(ii|2|b|segunda|reserv|women|femen|u\d\d|sub|cup|youth|nacional b)\b")


def known_tournament(api: Sofascore, alpha2: str, tid: int) -> tuple[int, int, str] | None:
    """O torneio ``tid``, se é do país e tem temporada de 2026."""
    try:
        item = (api.get(f"/unique-tournament/{tid}") or {}).get("uniqueTournament", {})
    except RuntimeError as error:
        print("[ERRO]", error)
        return None
    if (item.get("category") or {}).get("alpha2") != alpha2:
        return None
    season = season_2026(api, tid)
    return (tid, season, item.get("name", f"torneio {tid}")) if season else None


def categories(api: Sofascore) -> dict[str, int]:
    try:
        found = (api.get("/sport/football/categories") or {}).get("categories", [])
    except RuntimeError as error:
        print("[ERRO]", error, "(a lista de países do Sofascore; sem ela só os torneios conhecidos)")
        return {}
    return {c.get("alpha2"): c["id"] for c in found if c.get("alpha2")}


def tournament(api: Sofascore, alpha2: str, categories: dict[str, int]) -> tuple[int, int, str] | None:
    """(id do torneio, id da temporada de 2026, nome) da primeira divisão do país."""
    if alpha2 not in categories:
        print(f"[AVISO] {NATIONS[alpha2][2]}: primeira divisão de {YEAR} não achada; passe --torneio {alpha2}=id "
              f"(o número no endereço do torneio no sofascore.com)")
        return None
    groups = (api.get(f"/category/{categories[alpha2]}/unique-tournaments") or {}).get("groups", [])
    found = [t for g in groups for t in g.get("uniqueTournaments", [])
             if re.search(FIRST_DIVISION[alpha2], t.get("name", ""), re.I) and not NOT_FIRST.search(t.get("name", ""))
             and (alpha2 == "PY" or not t.get("name", "").lower().startswith("copa"))]   # Copa de la Liga não
    for item in sorted(found, key=lambda t: -(t.get("userCount") or 0)):
        season = season_2026(api, item["id"])
        if season:
            return item["id"], season, item["name"]
    names = ", ".join(f"{t.get('name')} ({t.get('id')})" for g in groups for t in g.get("uniqueTournaments", []))
    print(f"[AVISO] {NATIONS[alpha2][2]}: primeira divisão de {YEAR} não achada; torneios: {names[:400]}")
    return None


def season_2026(api: Sofascore, tid: int) -> int | None:
    seasons = (api.get(f"/unique-tournament/{tid}/seasons") or {}).get("seasons", [])
    return next((s["id"] for s in seasons if YEAR in str(s.get("year", ""))), None)


def league_teams(api: Sofascore, tid: int, season: int) -> dict[int, str]:
    """Clubes da tabela; sem tabela (mata-mata), os dos últimos jogos."""
    table = api.get(f"/unique-tournament/{tid}/season/{season}/standings/total") or {}
    teams = {r["team"]["id"]: r["team"]["name"] for t in table.get("standings", []) for r in t.get("rows", [])}
    for page in range(3):
        if len(teams) >= 10:
            break
        events = (api.get(f"/unique-tournament/{tid}/season/{season}/events/last/{page}") or {}).get("events", [])
        for event in events:
            for side in ("homeTeam", "awayTeam"):
                teams.setdefault(event[side]["id"], event[side]["name"])
    return teams


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cache", type=Path, default=ROOT / "workspace" / "sofascore")
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--pais", nargs="*", default=list(NATIONS), help="AR UY CO PY EC CL PE BO VE")
    parser.add_argument("--torneio", nargs="*", default=[], help="PAIS=id do torneio no Sofascore (AR=155)")
    parser.add_argument("--so-montar", action="store_true", help="não baixa nada: só monta data\\estrangeiros")
    args = parser.parse_args()
    if not args.so_montar:
        collect(args)
    subprocess.run([sys.executable, str(ROOT / "scripts" / "montar_estrangeiros.py"), "--cache", str(args.cache)],
                   check=True)


def collect(args) -> None:
    api = Sofascore(args.cache)
    forced = dict(item.upper().split("=") for item in args.torneio)
    countries: dict[str, int] | None = None     # só se algum torneio conhecido não conferir
    teams = []
    for alpha2 in (a.upper() for a in args.pais):
        if alpha2 not in NATIONS:
            print(f"[AVISO] país {alpha2} desconhecido (use {' '.join(NATIONS)})")
            continue
        if alpha2 in forced:
            tid = int(forced[alpha2])
            found = (tid, season_2026(api, tid), f"torneio {tid}")
        else:
            found = None
            if alpha2 in KNOWN:
                found = known_tournament(api, alpha2, KNOWN[alpha2])
            if not found:
                countries = categories(api) if countries is None else countries
                found = tournament(api, alpha2, countries)
        if not found or not found[1]:
            continue
        tid, season, name = found
        clubs = league_teams(api, tid, season)
        print(f"[OK] {NATIONS[alpha2][2]}: {name} ({tid}), {len(clubs)} clubes")
        for team_id, team_name in sorted(clubs.items(), key=lambda kv: kv[1]):
            teams.append({"pais": alpha2, "liga": name, "serie": NATIONS[alpha2][3],
                          "clube": display_name(team_name, alpha2), "sofascore_id": team_id,
                          "sofascore_nome": team_name, "sub20_id": None, "escalados": [], "tecnico": None})

    def team_data(team: dict) -> None:
        squad = (api.get(f"/team/{team['sofascore_id']}/players") or {}).get("players", [])
        if len(squad) < SMALL_SQUAD:
            team["escalados"] = lineup_players(api, team["sofascore_id"])
            for pid in team["escalados"]:
                api.get(f"/player/{pid}")
        try:
            team["tecnico"] = manager(api, team["sofascore_id"])
        except RuntimeError as error:
            print("[ERRO]", error)

    with ThreadPoolExecutor(args.threads) as pool:
        list(pool.map(team_data, teams))
    (args.cache / "times_estrangeiros.json").write_text(json.dumps(teams, ensure_ascii=False, indent=1),
                                                        encoding="utf-8")
    print(f"[OK] {len(teams)} clubes, {sum(1 for t in teams if t['tecnico'])} com técnico")

    jobs = []
    for team in teams:
        squad = api.get(f"/team/{team['sofascore_id']}/players") or {}
        national = {x["player"]["id"] for x in squad.get("nationalPlayers", [])}
        for pid in [x["player"]["id"] for x in squad.get("players", [])] + team["escalados"]:
            jobs += [f"/player/{pid}/attribute-overviews", f"/player/{pid}/transfer-history"]
            if pid in national:
                jobs.append(f"/player/{pid}/national-team-statistics")
    jobs = list(dict.fromkeys(jobs))
    print(f"[..] {len(jobs)} pedidos de jogadores (pode demorar; o que já baixou fica no cache)")

    def fetch(path: str) -> int:
        try:
            api.get(path)
            return 0
        except RuntimeError as error:
            print("[ERRO]", error)
            return 1

    with ThreadPoolExecutor(args.threads) as pool:
        errors = sum(pool.map(fetch, jobs))
    print(f"[OK] jogadores baixados ({errors} erros) em {args.cache}")


if __name__ == "__main__":
    main()
