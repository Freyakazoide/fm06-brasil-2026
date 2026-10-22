"""Árbitros de 2026: o quadro da data/modelos/arbitros_2026.xlsx nos árbitros brasileiros do FM06.

    python scripts\\aplicar_arbitros.py            (simulação: mostra quem vira quem)
    python scripts\\aplicar_arbitros.py --apply    (grava o people_db.dat e o .lnc do jogo)

Cada árbitro da planilha (maior nível primeiro) ocupa um árbitro brasileiro do banco de
2005 (maior capacidade primeiro; quem também tem contrato com clube fica de fora). O
.lnc dá o nome (CHANGE_PLAYER_NAME, aplicado no New Game) e o people_db recebe a
capacidade e a reputação pelo nível (19 = 180, o maior do banco). O rigor da planilha
não entra: os atributos de árbitro do FM06 estão zerados e não se sabe qual é qual.

Grava sobre o people_db atual do jogo, como o aplicar_comissao.py (mexem em pessoas
diferentes), e lê os árbitros da cópia original (workspace/baseline/people_db.original.dat).
Se rodar o reforcar_elencos.py de novo, rode este também. Depois: New Game.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import arbitros  # noqa: E402

SHEET = ROOT / "data" / "modelos" / "arbitros_2026.xlsx"
PEOPLE_BACKUP = ROOT / "workspace" / "baseline" / "people_db.original.dat"
SERVER_BACKUP = ROOT / "workspace" / "baseline" / "server_db.original.dat"
REPORT = ROOT / "workspace" / "mods" / "arbitros_2026_hospedeiros.csv"
LNC_NAME = "brasil_2026_arbitros.lnc"


def game_dir() -> Path:
    return Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    game = game_dir()
    people_path = game / "data" / "db" / "people_db.dat"
    if not PEOPLE_BACKUP.exists():
        PEOPLE_BACKUP.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(people_path, PEOPLE_BACKUP)
        print(f"[OK] cópia do people_db original em {PEOPLE_BACKUP}")
    original = PEOPLE_BACKUP.read_bytes()
    server = (SERVER_BACKUP if SERVER_BACKUP.exists() else game / "data" / "db" / "server_db.dat").read_bytes()

    referees = arbitros.load_sheet(SHEET)
    print("Lendo os árbitros do people_db...", flush=True)
    officials = arbitros.read(original, server)
    pairs = arbitros.plan(officials, referees)
    for official, referee in pairs:
        print(f"   {referee.nome:34} (nível {referee.nivel:2}) -> {official.name} "
              f"(capacidade {official.ability} -> {referee.ability})")
    print(f"[OK] {len(pairs)} árbitros de 2026 sobre {len(officials)} árbitros brasileiros do banco "
          f"({sum(o.employed for o in officials)} com contrato de clube ficam de fora)")
    if len(pairs) < len(referees):
        print(f"[AVISO] {len(referees) - len(pairs)} árbitros da planilha sem árbitro do banco para ocupar")
    if not args.apply:
        print("\nSimulação. Para gravar, feche o jogo e rode de novo com --apply.")
        return

    current = people_path.read_bytes()
    if len(current) != len(original):
        sys.exit(f"[ERRO] {people_path} não tem o tamanho do original; restaure o people_db e rode de novo.")
    people_path.write_bytes(arbitros.apply(current, pairs))
    lnc_text = arbitros.lnc_text(pairs)
    lnc_path = game / "data" / "db" / "lnc" / "all" / LNC_NAME
    lnc_path.parent.mkdir(parents=True, exist_ok=True)
    lnc_path.write_text(lnc_text, encoding="utf-16")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with REPORT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["arbitro_2026", "nivel", "uid", "arbitro_fm06", "capacidade_fm06", "capacidade_nova"])
        for official, referee in pairs:
            writer.writerow([referee.nome, referee.nivel, official.uid, official.name, official.ability,
                             referee.ability])
    print(f"[OK] gravado {people_path}")
    print(f"[OK] gravado {lnc_path}; lista em {REPORT}")
    print("Agora: New Game (o .lnc dá os nomes no New Game).")


if __name__ == "__main__":
    main()
