"""Baixa do Sofascore os elencos de 2026 das Séries A, B, C e D (e os sub-20).

Uso: python scripts/coletar_sofascore.py [--cache workspace/sofascore]

Grava no cache um JSON por pedido (refazer é instantâneo) e, em
<cache>/times.json, cada time da série com o clube de data/brasil/series_2026.csv
e o sub-20. Por jogador: elenco (nome, número, posições, nascimento, altura, pé,
país, contrato, valor), visão geral dos atributos, transferências e seleção.
Depois: scripts/montar_jogadores.py.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch.estaduais_clubes import _NOISE, normalize  # noqa: E402

API = "https://api.sofascore.com/api/v1"
TOURNAMENTS = {"A": 325, "B": 390, "C": 1281, "D": 10326}
YEAR = "2026"
# os do site (sem eles o Sofascore às vezes responde 403)
HEADERS = ["-H", "Accept: application/json", "-H", "Referer: https://www.sofascore.com/",
           "-H", "Origin: https://www.sofascore.com"]


class Sofascore:
    def __init__(self, cache: Path):
        self.cache = cache
        cache.mkdir(parents=True, exist_ok=True)

    def get(self, path: str, retries: int = 4):
        key = self.cache / (hashlib.md5(path.encode()).hexdigest() + ".json")
        if key.exists():
            try:
                return json.loads(key.read_text())
            except ValueError:
                key.unlink()
        code = ""
        for attempt in range(retries):
            run = subprocess.run(["curl", "-s", "-m", "25", "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                                  *HEADERS, "-w", "\n%{http_code}", API + path], capture_output=True, text=True)
            body, _, code = run.stdout.rpartition("\n")
            if code in ("200", "404"):
                data = json.loads(body) if code == "200" else None
                tmp = key.with_suffix(f".{time.time_ns()}.tmp")
                tmp.write_text(json.dumps(data))
                tmp.replace(key)
                return data
            time.sleep(3 * (attempt + 1))
        raise RuntimeError(f"{path}: HTTP {code}")


def series_teams(api: Sofascore) -> dict[str, dict[str, str]]:
    teams: dict[str, dict[str, str]] = {}
    for serie, tid in TOURNAMENTS.items():
        season = next(s for s in api.get(f"/unique-tournament/{tid}/seasons")["seasons"] if YEAR in s["year"])
        table = api.get(f"/unique-tournament/{tid}/season/{season['id']}/standings/total") or {}
        teams[serie] = {str(r["team"]["id"]): r["team"]["name"] for t in table.get("standings", []) for r in t["rows"]}
    return teams


def _words(text: str) -> set[str]:
    return set(normalize(text).split()) - _NOISE


def match_clubs(teams: dict[str, dict[str, str]]) -> tuple[list[dict], list[str]]:
    """Time do Sofascore -> clube de series_2026.csv (mesma série, nome igual ou parecido)."""
    rows = list(csv.DictReader((ROOT / "data" / "brasil" / "series_2026.csv").open(encoding="utf-8-sig")))
    found, missing = [], []
    for serie, pool in teams.items():
        free = dict(pool)
        for row in (r for r in rows if r["serie"] == serie):
            best, score = None, 0.0
            for tid, name in free.items():
                if normalize(name) == normalize(row["clube"]):
                    best, score = tid, 9.0
                    break
                a, b = _words(row["clube"]), _words(name)
                if a and b and len(a & b) / max(len(a), len(b)) > score:
                    best, score = tid, len(a & b) / max(len(a), len(b))
            if best and score >= 0.5:
                found.append({"serie": serie, "clube": row["clube"], "estado": row["estado"],
                              "sofascore_id": int(best), "sofascore_nome": free.pop(best)})
            else:
                missing.append(f"Série {serie}: {row['clube']}")
        missing += [f"Série {serie}: sobrou no Sofascore {name}" for name in free.values()]
    return found, missing


def youth_team(api: Sofascore, name: str):
    query = (name + " U20").replace(" ", "%20").replace("/", "%2F")
    results = (api.get("/search/teams?q=" + query) or {}).get("results", [])
    base = name.lower().split()[0]
    for item in results:
        team = item["entity"]
        if (item.get("type") == "team" and team.get("country", {}).get("alpha2") == "BR" and team.get("gender") == "M"
                and "U20" in team["name"] and base in team["name"].lower()):
            return team["id"], team["name"]
    return None, None


SMALL_SQUAD = 20


def lineup_players(api: Sofascore, team_id: int) -> list[int]:
    """Quem jogou pelo time em 2026 (escalações), para elenco que o Sofascore não lista."""
    found: dict[int, None] = {}
    for page in range(4):
        events = (api.get(f"/team/{team_id}/events/last/{page}") or {}).get("events", [])
        for event in events:
            if not event.get("season", {}).get("year", "").startswith(YEAR):
                continue
            lineups = api.get(f"/event/{event['id']}/lineups")
            side = "home" if event["homeTeam"]["id"] == team_id else "away"
            for item in (lineups or {}).get(side, {}).get("players", []):
                found[item["player"]["id"]] = None
        if not events:
            break
    return list(found)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=ROOT / "workspace" / "sofascore")
    parser.add_argument("--threads", type=int, default=6)
    args = parser.parse_args()
    api = Sofascore(args.cache)
    teams, missing = match_clubs(series_teams(api))
    for line in missing:
        print("[AVISO]", line)
    with ThreadPoolExecutor(args.threads) as pool:
        for team, (yid, yname) in zip(teams, pool.map(lambda t: youth_team(api, t["sofascore_nome"]), teams)):
            team["sub20_id"], team["sub20_nome"] = yid, yname
    for team in teams:
        squad = (api.get(f"/team/{team['sofascore_id']}/players") or {}).get("players", [])
        team["escalados"] = lineup_players(api, team["sofascore_id"]) if len(squad) < SMALL_SQUAD else []
        for pid in team["escalados"]:
            api.get(f"/player/{pid}")
    (args.cache / "times.json").write_text(json.dumps(teams, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] {len(teams)} clubes, {sum(1 for t in teams if t['sub20_id'])} com sub-20")

    jobs = []
    for team in teams:
        for tid in filter(None, (team["sofascore_id"], team["sub20_id"])):
            squad = api.get(f"/team/{tid}/players") or {}
            national = {x["player"]["id"] for x in squad.get("nationalPlayers", [])}
            for pid in [x["player"]["id"] for x in squad.get("players", [])] + (
                    team["escalados"] if tid == team["sofascore_id"] else []):
                jobs += [f"/player/{pid}/attribute-overviews", f"/player/{pid}/transfer-history"]
                if pid in national:
                    jobs.append(f"/player/{pid}/national-team-statistics")
    jobs = list(dict.fromkeys(jobs))
    print(f"[..] {len(jobs)} pedidos de jogadores")

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
