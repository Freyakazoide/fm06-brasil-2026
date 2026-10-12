from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(
    0,
    str(ROOT / "src"),
)

from fm06patch.player_history import (
    PlayerHistoryDatabase,
)


CONFIG = (
    ROOT
    / "config"
    / "local.json"
)

CLUB_MAP = (
    ROOT
    / "workspace"
    / "dumps"
    / "active_clubs.csv"
)


def load_clubs():
    result = {}

    if not CLUB_MAP.exists():
        return result

    with CLUB_MAP.open(
        "r",
        encoding="utf-8-sig",
    ) as file:

        for row in csv.DictReader(
            file,
            delimiter=";",
        ):
            result[
                int(row["record_id"])
            ] = row["short_name"]

    return result


def amount_text(
    value: int,
) -> str:

    if value == 0xFFFFFFFF:
        return "-"

    return str(value)


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "player_uid",
        type=int,
    )

    parser.add_argument(
        "--name",
        default="",
    )

    args = parser.parse_args()

    with CONFIG.open(
        "r",
        encoding="utf-8",
    ) as file:
        config = json.load(file)

    db_dir = (
        Path(config["game_dir"])
        / "data"
        / "db"
    )

    db = PlayerHistoryDatabase(
        index_data=(
            db_dir
            / "pl_hist_index.dat"
        ).read_bytes(),

        spans_data=(
            db_dir
            / "pl_hist_id.dat"
        ).read_bytes(),

        history_data=(
            db_dir
            / "pl_hist_dt.dat"
        ).read_bytes(),
    )

    clubs = load_clubs()

    records = db.records(
        args.player_uid
    )

    print("=" * 105)

    title = (
        args.name
        or str(args.player_uid)
    )

    print(
        f" FM06 BRASIL 2026 - "
        f"HISTÓRICO: {title}"
    )

    print("=" * 105)
    print()

    print(
        f"{'ANO':<6}"
        f"{'CLUBE':<28}"
        f"{'UID':>8}  "
        f"{'J':>4} "
        f"{'G':>4} "
        f"{'FLAG':>6} "
        f"{'AMOUNT_RAW':>14} "
        f"{'NEXT':>12}"
    )

    print("-" * 105)

    for record in records:

        club_name = clubs.get(
            record.club_uid,
            f"UID {record.club_uid}",
        )

        next_text = (
            "-"
            if record.next_relative_offset
            is None
            else (
                f"0x"
                f"{record.next_relative_offset:X}"
            )
        )

        print(
            f"{record.year:<6}"
            f"{club_name:<28}"
            f"{record.club_uid:>8}  "
            f"{record.appearances:>4} "
            f"{record.goals:>4} "
            f"{"Empr" if record.is_loan else "-":>6} "
            f"{amount_text(record.amount_raw):>14} "
            f"{next_text:>12}"
        )

    print()
    print(
        f"Registros: {len(records)}"
    )


if __name__ == "__main__":
    main()