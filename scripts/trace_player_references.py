from __future__ import annotations

import json
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(
    0,
    str(ROOT / "src"),
)

from fm06patch.people_db import PeopleDatabase


CONFIG = ROOT / "config" / "local.json"

RADIUS = 2048
MAX_RESULTS = 10


PLAYERS = [
    {
        "name": "Sávio",
        "uid": 104318,
        "club_name": "Zaragoza",
        "club_uid": 1749,
        "field_a": 1324,
        "field_b": 1746,
        "nation_internal_id": 170,
    },
    {
        "name": "Fred",
        "uid": 321081,
        "club_name": "Lyon",
        "club_uid": 865,
        "field_a": 589,
        "field_b": 864,
        "nation_internal_id": 143,
    },
    {
        "name": "Rogério Ceni",
        "uid": 3300977,
        "club_name": "São Paulo",
        "club_uid": 337,
        "field_a": 212,
        "field_b": 336,
        "nation_internal_id": 189,
    },
    {
        "name": "Zinedine Zidane",
        "uid": 8076,
        "club_name": "Real Madrid",
        "club_uid": 1736,
        "field_a": 1313,
        "field_b": 1733,
        "nation_internal_id": 170,
    },
]


def p16(value: int) -> bytes:
    return struct.pack("<H", value)


def p32(value: int) -> bytes:
    return struct.pack("<I", value)


def find_all(
    data: bytes,
    needle: bytes,
):
    result = []
    cursor = 0

    while True:
        pos = data.find(
            needle,
            cursor,
        )

        if pos == -1:
            break

        result.append(pos)
        cursor = pos + 1

    return result


def find_relatives(
    block: bytes,
    block_start: int,
    center: int,
    needle: bytes,
):
    result = []

    cursor = 0

    while True:

        pos = block.find(
            needle,
            cursor,
        )

        if pos == -1:
            break

        absolute = (
            block_start + pos
        )

        result.append(
            absolute - center
        )

        cursor = pos + 1

    return result


def inspect_reference_hit(
    data: bytes,
    hit: int,
    player: dict,
):
    start = max(
        0,
        hit - RADIUS,
    )

    end = min(
        len(data),
        hit + RADIUS,
    )

    block = data[start:end]

    patterns = {
        "PLAYER_UID":
            p32(
                player["uid"]
            ),

        "CLUB_UID32":
            p32(
                player["club_uid"]
            ),

        "CLUB_UID16":
            p16(
                player["club_uid"]
            ),

        "FIELD_A32":
            p32(
                player["field_a"]
            ),

        "FIELD_B32":
            p32(
                player["field_b"]
            ),

        "FIELD_A16":
            p16(
                player["field_a"]
            ),

        "FIELD_B16":
            p16(
                player["field_b"]
            ),

        "PAIR_A32_B32":
            (
                p32(
                    player["field_a"]
                )
                + p32(
                    player["field_b"]
                )
            ),

        "PAIR_A16_B16":
            (
                p16(
                    player["field_a"]
                )
                + p16(
                    player["field_b"]
                )
            ),

        "CLUB_KEY":
            (
                p32(
                    player["field_a"]
                )
                + p32(
                    player["field_b"]
                )
                + b"\x00"
                + p32(
                    player[
                        "nation_internal_id"
                    ]
                )
            ),
    }

    matches = {}

    for name, needle in (
        patterns.items()
    ):

        matches[name] = (
            find_relatives(
                block,
                start,
                hit,
                needle,
            )
        )

    score = 0

    if matches["CLUB_KEY"]:
        score += 1000

    if matches["PAIR_A32_B32"]:
        score += 500

    if matches["PAIR_A16_B16"]:
        score += 300

    if matches["CLUB_UID32"]:
        score += 200

    if matches["FIELD_A32"]:
        score += 100

    if matches["FIELD_B32"]:
        score += 100

    if matches["CLUB_UID16"]:
        score += 30

    if matches["FIELD_A16"]:
        score += 20

    if matches["FIELD_B16"]:
        score += 20

    if matches["PLAYER_UID"]:
        score += 50

    return {
        "offset": hit,
        "score": score,
        "matches": matches,
    }


def format_matches(values):
    if not values:
        return "-"

    return ", ".join(
        f"{value:+d}"
        for value in values[:8]
    )


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
        "people_db":
            (
                db_dir
                / "people_db.dat"
            ).read_bytes(),

        "server_db":
            (
                db_dir
                / "server_db.dat"
            ).read_bytes(),

        "client_db":
            (
                db_dir
                / "client_db.dat"
            ).read_bytes(),
    }

    people_parser = PeopleDatabase(
        databases[
            "people_db"
        ]
    )

    print("=" * 125)
    print(
        " FM06 BRASIL 2026 - "
        "PLAYER REFERENCE TRACE"
    )
    print("=" * 125)

    for player in PLAYERS:

        core = people_parser.player(
            player["uid"]
        )

        references = [
            (
                "before_uid",
                core.unknown_before_uid,
            ),
            (
                "reference_plus4",
                core.unknown_reference,
            ),
        ]

        print()
        print("=" * 125)

        print(
            f"{player['name']} "
            f"(UID {player['uid']})"
        )

        print(
            f"Current club: "
            f"{player['club_name']} "
            f"UID={player['club_uid']} "
            f"KEY=("
            f"{player['field_a']},"
            f"{player['field_b']},"
            f"{player['nation_internal_id']}"
            f")"
        )

        print(
            f"before_uid      = "
            f"{core.unknown_before_uid}"
        )

        print(
            f"reference_plus4 = "
            f"{core.unknown_reference}"
        )

        print("=" * 125)

        for reference_name, value in (
            references
        ):

            needle = p32(
                value
            )

            print()
            print(
                f"{reference_name} "
                f"= {value}"
            )

            print("-" * 125)

            for db_name, data in (
                databases.items()
            ):

                raw_hits = find_all(
                    data,
                    needle,
                )

                results = []

                for hit in raw_hits:

                    result = (
                        inspect_reference_hit(
                            data,
                            hit,
                            player,
                        )
                    )

                    if (
                        result["score"]
                        > 0
                    ):
                        results.append(
                            result
                        )

                results.sort(
                    key=lambda item: (
                        -item["score"],
                        item["offset"],
                    )
                )

                print()
                print(
                    f"{db_name}: "
                    f"{len(raw_hits)} "
                    f"raw hit(s), "
                    f"{len(results)} "
                    f"com contexto relevante"
                )

                for index, result in (
                    enumerate(
                        results[
                            :MAX_RESULTS
                        ],
                        start=1,
                    )
                ):

                    matches = (
                        result[
                            "matches"
                        ]
                    )

                    print()
                    print(
                        f"  #{index} "
                        f"0x"
                        f"{result['offset']:08X} "
                        f"score="
                        f"{result['score']}"
                    )

                    for key in (
                        "PLAYER_UID",
                        "CLUB_UID32",
                        "CLUB_UID16",
                        "FIELD_A32",
                        "FIELD_B32",
                        "FIELD_A16",
                        "FIELD_B16",
                        "PAIR_A32_B32",
                        "PAIR_A16_B16",
                        "CLUB_KEY",
                    ):

                        if not matches[
                            key
                        ]:
                            continue

                        print(
                            f"       "
                            f"{key:<15} "
                            f"{format_matches(matches[key])}"
                        )


if __name__ == "__main__":
    main()