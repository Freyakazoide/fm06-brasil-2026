"""Mídia brasileira de 2026 (data/brasil/midia_2026.csv) no server_db.dat.

    python scripts\\aplicar_midia.py            (simulação: mostra o que faria)
    python scripts\\aplicar_midia.py --apply    (grava; o jogo tem de estar fechado)

O FM06 só tem mídia inglesa, polonesa e o O JOGO. As fontes da planilha entram no fim da
lista MEDIA_SOURCE: as de alcance "pais" cobrem o Brasil; as de "cidade" cobrem a cidade
(UID do lang_db) e os clubes da coluna clubes (UID do jogo na identidade_fm06.csv). Rodar de
novo não grava duas vezes (src/fm06patch/midia.py, ficha C11).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import estadios, midia  # noqa: E402

SHEET = ROOT / "data" / "brasil" / "midia_2026.csv"
IDENTITY = ROOT / "data" / "brasil" / "clubes" / "identidade_fm06.csv"
NAMES = {midia.CITY: "cidade", midia.COUNTRY: "Brasil"}


def game_dir() -> Path:
    return Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    db_dir = game_dir() / "data" / "db"
    server_path = db_dir / "server_db.dat"
    server, lang = server_path.read_bytes(), (db_dir / "lang_db.dat").read_bytes()
    clubs = {row["clube_2026"].strip(): int(row["uid_jogo"])
             for row in csv.DictReader(IDENTITY.open(encoding="utf-8-sig"))}

    def city_uid(name: str) -> int | None:
        found = [u for u in estadios.lang_uids(lang, name) if estadios.city_index(server, u)]
        return found[0] if found else None

    wanted, problems = midia.load_sheet(SHEET, city_uid, clubs.get)
    for m in wanted:
        print(f"{m.name}: meio {m.kind}, {NAMES[m.scope]} {m.place}, clubes {m.clubs}")
    for problem in problems:
        print("[AVISO]", problem)
    db, new = midia.add(server, wanted)
    print(f"[OK] {len(new)} fontes novas na mídia" if new else "[OK] mídia já gravada; nada a fazer")
    if args.apply:
        server_path.write_bytes(db)
        print(f"[OK] gravado {server_path}")
    else:
        print("(simulação: rode com --apply para gravar)")


if __name__ == "__main__":
    main()
