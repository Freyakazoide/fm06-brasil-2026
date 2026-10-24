"""Monta data/estrangeiros a partir do que o coletar_estrangeiros.py baixou.

    python scripts\\montar_estrangeiros.py [--cache workspace\\sofascore]

(o coletar_estrangeiros.py já roda este no fim). Para cada clube de
<cache>/times_estrangeiros.json acha o clube do FM06 do mesmo país pelo nome
(fm06patch/estrangeiros.py) e grava:

- identidade_estrangeiros.csv: clube de 2026 -> clube do FM06. Clube sem par fica com
  uid_jogo vazio e de fora do mod; para corrigir, ponha o UID do jogo (o "Show Unique
  IDs" do FM, ou o de outro clube do país nesta lista) e rode de novo: o que estiver
  preenchido à mão fica;
- jogadores_estrangeiros_2026.xlsx (montar_jogadores.py) e carreiras_estrangeiros_2026.csv
  (montar_carreiras.py), só dos clubes com par;
- tecnicos_estrangeiros_2026.csv: o técnico de cada clube (o aplicar_comissao.py põe no
  técnico do clube do FM06).
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import estrangeiros as ex, people_contracts  # noqa: E402

SERVER_BACKUP = ROOT / "workspace" / "baseline" / "server_db.original.dat"
COACH_FIELDS = ["clube_2026", "pais", "cargo", "nome", "nacionalidade", "nascimento", "fonte"]


def server_bytes() -> bytes:
    if SERVER_BACKUP.exists():
        return SERVER_BACKUP.read_bytes()
    game = Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"])
    return (game / "data" / "db" / "server_db.dat").read_bytes()


def identities(teams: list[dict], server: bytes, kept: dict[int, dict]) -> tuple[list[dict], list[str]]:
    """Uma linha por clube de 2026; ``kept``: linhas da lista anterior com UID posto à mão."""
    brazil = set(people_contracts.brazil_club_indexes(server))
    pools = {alpha2: ex.fm06_clubs(server, alpha2, brazil) for alpha2 in {t["pais"] for t in teams}}
    rows, taken, notes, near = [], {}, [], []
    for team in teams:
        clubs = pools[team["pais"]]
        old = kept.get(team["sofascore_id"])
        club = None
        if old:
            club = next((c for c in clubs if c["uid"] == int(old["uid_jogo"])), None)
            club = club or {"uid": int(old["uid_jogo"]), "repo": int(old.get("uid_repo") or 0),
                            "short": old.get("fm06_nome", "")}
        else:
            club, how = ex.match(team["sofascore_nome"], clubs, ex.ALIASES.get(team["pais"]))
            if club and how == "aproximado":
                near.append(f"{team['clube']} -> {club['long']}")
        if club and club["uid"] in taken:
            notes.append(f"{team['clube']}: o clube do FM06 {club['short']} já é de {taken[club['uid']]}")
            club = None
        if club:
            taken[club["uid"]] = team["clube"]
        rows.append({"clube_2026": team["clube"], "pais": team["pais"], "uid_jogo": club["uid"] if club else "",
                     "uid_repo": club.get("repo", "") if club else "", "fm06_nome": club["short"] if club else "",
                     "tipo": "estrangeiro", "onde": team.get("liga", ""), "sofascore_id": team["sofascore_id"],
                     "sofascore_nome": team["sofascore_nome"]})
    if near:
        notes.append("casados por aproximação (confira; se errado, ponha o UID certo e 'sim' em manual): "
                     + "; ".join(near))
    return rows, notes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=ROOT / "workspace" / "sofascore")
    args = parser.parse_args()
    teams = json.loads((args.cache / "times_estrangeiros.json").read_text(encoding="utf-8"))
    kept = {}
    if ex.IDENTITIES.exists():
        for row in csv.DictReader(ex.IDENTITIES.open(encoding="utf-8-sig")):
            if str(row.get("uid_jogo") or "").isdigit() and row.get("manual", "").strip():
                kept[int(row["sofascore_id"])] = row
    rows, notes = identities(teams, server_bytes(), kept)
    ex.DATA.mkdir(parents=True, exist_ok=True)
    with ex.IDENTITIES.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=ex.FIELDS + ["manual"])
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "manual": "sim" if row["sofascore_id"] in kept else ""})
    matched = {r["clube_2026"] for r in rows if r["uid_jogo"] != ""}
    for note in notes:
        print("[CONFIRA]" if note.startswith("casados") else "[AVISO]", note)
    missing = [r for r in rows if r["uid_jogo"] == ""]
    print(f"[OK] {len(matched)} de {len(rows)} clubes com clube do FM06 em {ex.IDENTITIES.relative_to(ROOT)}")
    if missing:
        print("[CONFIRA] sem clube do FM06 (ficam de fora; ponha o UID na coluna uid_jogo e 'sim' em manual): "
              + ", ".join(r["clube_2026"] for r in missing))

    chosen = [t for t in teams if t["clube"] in matched]
    (args.cache / "times_estrangeiros_fm06.json").write_text(json.dumps(chosen, ensure_ascii=False, indent=1),
                                                             encoding="utf-8")
    with ex.COACHES.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=COACH_FIELDS)
        writer.writeheader()
        for team in chosen:
            if team.get("tecnico"):
                writer.writerow({"clube_2026": team["clube"], "pais": team["pais"], "cargo": "tecnico",
                                 **team["tecnico"], "fonte": "Sofascore"})
    print(f"[OK] {sum(1 for t in chosen if t.get('tecnico'))} técnicos em {ex.COACHES.relative_to(ROOT)}")
    scripts = ROOT / "scripts"
    subprocess.run([sys.executable, str(scripts / "montar_jogadores.py"), "--cache", str(args.cache),
                    "--times", "times_estrangeiros_fm06.json", "--saida", str(ex.PLAYERS)], check=True)
    subprocess.run([sys.executable, str(scripts / "montar_carreiras.py"), "--cache", str(args.cache),
                    "--times", "times_estrangeiros_fm06.json", "--jogadores", str(ex.PLAYERS),
                    "--saida", str(ex.CAREERS)], check=True)


if __name__ == "__main__":
    main()
