from __future__ import annotations

import csv
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

CONFIG = (
    ROOT
    / "config"
    / "local.json"
)

MAP_FILE = (
    ROOT
    / "workspace"
    / "dumps"
    / "brazil_entity_map.csv"
)


ANCHORS = [
    (
        "Sávio",
        104318,
    ),
    (
        "Fred",
        321081,
    ),
    (
        "Rogério Ceni",
        3300977,
    ),
]


def find_all(
    data: bytes,
    value: int,
):

    needle = struct.pack(
        "<I",
        value,
    )

    result = []

    cursor = 0

    while True:

        pos = data.find(
            needle,
            cursor,
        )

        if pos == -1:
            break

        result.append(
            pos
        )

        cursor = pos + 1

    return result


def byte_metrics(
    data: bytes,
    center: int,
    radius: int = 64,
):

    start = max(
        0,
        center - radius,
    )

    end = min(
        len(data),
        center + radius,
    )

    block = data[
        start:end
    ]

    if not block:

        return (
            0,
            0,
            0,
        )

    small = sum(
        1
        for byte in block
        if (
            1
            <= byte
            <= 20
        )
    )

    zeros = block.count(
        0
    )

    ff = block.count(
        255
    )

    length = len(
        block
    )

    return (
        small / length,
        zeros / length,
        ff / length,
    )


def nearby_clubs(
    data: bytes,
    center: int,
    clubs,
    radius: int = 128,
):

    start = max(
        0,
        center - radius,
    )

    end = min(
        len(data),
        center + radius,
    )

    block = data[
        start:end
    ]

    result = []

    for uid, name in clubs:

        needle = struct.pack(
            "<I",
            uid,
        )

        cursor = 0

        while True:

            pos = block.find(
                needle,
                cursor,
            )

            if pos == -1:
                break

            absolute = (
                start + pos
            )

            result.append(
                (
                    absolute
                    - center,

                    uid,

                    name,
                )
            )

            cursor = pos + 1

    return result


def main():

    with CONFIG.open(
        "r",
        encoding="utf-8",
    ) as file:

        config = json.load(
            file
        )

    people = (
        Path(
            config["game_dir"]
        )
        / "data"
        / "db"
        / "people_db.dat"
    ).read_bytes()

    with MAP_FILE.open(
        "r",
        encoding="utf-8-sig",
    ) as file:

        club_rows = list(
            csv.DictReader(
                file,
                delimiter=";",
            )
        )

    clubs = [
        (
            int(
                row[
                    "lang_id"
                ]
            ),
            row[
                "short_name"
            ],
        )
        for row in club_rows
        if row[
            "status"
        ] == "OK"
    ]

    print("=" * 120)
    print(
        " FM06 BRASIL 2026 - "
        "PEOPLE DATABASE ANCHORS"
    )
    print("=" * 120)

    all_hits = {}

    for name, uid in ANCHORS:

        hits = find_all(
            people,
            uid,
        )

        all_hits[
            name
        ] = hits

        print()
        print(
            f"{name} "
            f"(UID {uid})"
        )

        print(
            f"hits: {len(hits)}"
        )

        print()

        print(
            f"{'#':>2} "
            f"{'OFFSET':>12} "
            f"{'MOD4':>5} "
            f"{'SMALL':>7} "
            f"{'ZERO':>7} "
            f"{'FF':>7} "
            f"CLUB UIDs ±128"
        )

        print(
            "-" * 120
        )

        for index, hit in enumerate(
            hits,
            start=1,
        ):

            small, zero, ff = (
                byte_metrics(
                    people,
                    hit,
                )
            )

            relations = (
                nearby_clubs(
                    people,
                    hit,
                    clubs,
                )
            )

            relation_text = (
                ", ".join(
                    f"{rel:+d}:"
                    f"{club_name}"
                    f"({club_uid})"
                    for (
                        rel,
                        club_uid,
                        club_name,
                    )
                    in relations
                )
            )

            print(
                f"{index:>2} "
                f"0x{hit:08X} "
                f"{hit % 4:>5} "
                f"{small:>7.3f} "
                f"{zero:>7.3f} "
                f"{ff:>7.3f} "
                f"{relation_text}"
            )

    print()
    print("=" * 120)
    print(
        " HIT ORDINALS LADO A LADO"
    )
    print("=" * 120)
    print()

    max_hits = max(
        len(value)
        for value
        in all_hits.values()
    )

    for index in range(
        max_hits
    ):

        columns = []

        for name, _ in ANCHORS:

            hits = all_hits[
                name
            ]

            if index < len(
                hits
            ):

                columns.append(
                    f"{name}: "
                    f"0x{hits[index]:08X}"
                )

            else:

                columns.append(
                    f"{name}: -"
                )

        print(
            f"{index + 1:>2}  "
            + " | ".join(
                columns
            )
        )


if __name__ == "__main__":
    main()