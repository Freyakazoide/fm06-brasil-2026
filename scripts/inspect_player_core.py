from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(
    0,
    str(ROOT / "src"),
)

from fm06patch.people_db import (
    PeopleDatabase,
)


CONFIG = (
    ROOT
    / "config"
    / "local.json"
)


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

    people_path = (
        Path(
            config["game_dir"]
        )
        / "data"
        / "db"
        / "people_db.dat"
    )

    database = PeopleDatabase(
        people_path.read_bytes()
    )

    player = database.player(
        args.player_uid
    )

    print("=" * 90)
    print(
        " FM06 BRASIL 2026 - "
        "PLAYER CORE"
    )
    print("=" * 90)

    print()
    print(
        f"Nome                : "
        f"{args.name or '-'}"
    )

    print(
        f"Player UID          : "
        f"{player.player_uid}"
    )

    print(
        f"people_db offset    : "
        f"{player.uid_offset_hex}"
    )

    print(
        f"Detection score     : "
        f"{player.score}"
    )

    print()
    print(
        f"Nation/group interno: "
        f"{player.nation_internal_id}"
    )

    print(
        f"Marker              : "
        f"{player.marker_255}"
    )

    print(
        f"Player type raw     : "
        f"{player.player_type_raw}"
    )

    print()
    print(
        f"Reputation #1       : "
        f"{player.reputation_1}"
    )

    print(
        f"Reputation #2       : "
        f"{player.reputation_2}"
    )

    print(
        f"Reputation #3       : "
        f"{player.reputation_3}"
    )

    print()
    print(
        f"Current Ability     : "
        f"{player.current_ability}"
    )

    print(
        f"Potential Ability   : "
        f"{player.potential_ability}"
    )

    print()
    print(
        "Campos ainda desconhecidos"
    )

    print(
        f"  before year       : "
        f"{player.unknown_before_year}"
    )

    print(
        f"  year-like         : "
        f"{player.year_like}"
    )

    print(
        f"  before UID        : "
        f"{player.unknown_before_uid}"
    )

    print(
        f"  reference +4      : "
        f"{player.unknown_reference}"
    )


if __name__ == "__main__":
    main()
