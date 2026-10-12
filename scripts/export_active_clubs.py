from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(
    0,
    str(ROOT / "src"),
)

from fm06patch.lang_db import LangDatabase


CONFIG = (
    ROOT
    / "config"
    / "local.json"
)

OUTPUT = (
    ROOT
    / "workspace"
    / "dumps"
    / "active_clubs.csv"
)


def main():
    with CONFIG.open(
        "r",
        encoding="utf-8",
    ) as file:
        config = json.load(file)

    lang_db_path = (
        Path(config["game_dir"])
        / "data"
        / "db"
        / "lang_db.dat"
    )

    db = LangDatabase.load(
        lang_db_path
    )

    clubs = db.clubs()

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.writer(
            file,
            delimiter=";",
        )

        writer.writerow([
            "record_id",
            "record_id_hex",
            "offset",
            "flag",
            "full_name",
            "short_name",
        ])

        for club in clubs:
            writer.writerow([
                club.record_id,
                club.record_id_hex,
                club.offset_hex,
                club.flag,
                club.full_name,
                club.short_name,
            ])

    print("=" * 90)
    print(" FM06 BRASIL 2026 - CLUBES DA TABELA ATIVA")
    print("=" * 90)

    for club in clubs:
        print(
            f"{club.record_id:5d} "
            f"{club.record_id_hex:>8}  "
            f"{club.offset_hex}  "
            f"{club.full_name:<32} "
            f"-> {club.short_name}"
        )

    print()
    print(
        f"Registros: {len(clubs)}"
    )

    print()
    print("CSV:")
    print(OUTPUT)


if __name__ == "__main__":
    main()