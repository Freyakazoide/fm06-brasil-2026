from __future__ import annotations

import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "local.json"


PLAYERS = [
    {
        "name": "Sávio",
        "uid": 104318,
        "current_club_uid": 1749,
    },
    {
        "name": "Fred",
        "uid": 321081,
        "current_club_uid": 865,
    },
    {
        "name": "Rogério Ceni",
        "uid": 3300977,
        "current_club_uid": 337,
    },
]


FILES = [
    "server_db.dat",
    "client_db.dat",
    "people_db.dat",
]


def find_all(
    data: bytes,
    needle: bytes,
):
    hits = []
    cursor = 0

    while True:
        pos = data.find(
            needle,
            cursor,
        )

        if pos == -1:
            break

        hits.append(pos)
        cursor = pos + 1

    return hits


def nearby_club_matches(
    data: bytes,
    player_offset: int,
    club_uid: int,
    radius: int,
):
    start = max(
        0,
        player_offset - radius,
    )

    end = min(
        len(data),
        player_offset + radius,
    )

    block = data[
        start:end
    ]

    matches = []

    patterns = []

    if club_uid <= 0xFFFF:
        patterns.append(
            (
                "u16",
                struct.pack(
                    "<H",
                    club_uid,
                ),
            )
        )

    patterns.append(
        (
            "u32",
            struct.pack(
                "<I",
                club_uid,
            ),
        )
    )

    for kind, pattern in patterns:

        for local in find_all(
            block,
            pattern,
        ):

            absolute = (
                start + local
            )

            matches.append(
                (
                    kind,
                    absolute,
                    absolute
                    - player_offset,
                )
            )

    return matches


def main():

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

    databases = {
        filename:
            (
                db_dir
                / filename
            ).read_bytes()
        for filename in FILES
    }

    print("=" * 120)
    print(
        " FM06 BRASIL 2026 - "
        "CURRENT CLUB TRACE"
    )
    print("=" * 120)

    for player in PLAYERS:

        uid = player["uid"]

        club_uid = (
            player[
                "current_club_uid"
            ]
        )

        print()
        print(
            f"{player['name']} "
            f"player_uid={uid} "
            f"current_club_uid="
            f"{club_uid}"
        )

        print("-" * 120)

        uid_bytes = struct.pack(
            "<I",
            uid,
        )

        for filename, data in (
            databases.items()
        ):

            player_hits = find_all(
                data,
                uid_bytes,
            )

            print()
            print(
                f"{filename}: "
                f"{len(player_hits)} "
                f"player UID hit(s)"
            )

            found = False

            for hit_number, hit in enumerate(
                player_hits,
                start=1,
            ):

                matches = (
                    nearby_club_matches(
                        data,
                        hit,
                        club_uid,
                        radius=4096,
                    )
                )

                if not matches:
                    continue

                found = True

                print(
                    f"  PLAYER HIT #{hit_number} "
                    f"0x{hit:08X}"
                )

                for (
                    kind,
                    club_offset,
                    relative,
                ) in matches:

                    print(
                        f"      "
                        f"{kind:<3} "
                        f"club="
                        f"0x{club_offset:08X} "
                        f"relative="
                        f"{relative:+d} "
                        f"(0x{abs(relative):X})"
                    )

            if not found:
                print(
                    "  nenhuma referência "
                    "ao clube atual em ±4096"
                )


if __name__ == "__main__":
    main()