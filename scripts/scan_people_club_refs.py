from __future__ import annotations

import csv
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

CONFIG = ROOT / "config" / "local.json"

MAP_FILE = (
    ROOT
    / "workspace"
    / "dumps"
    / "brazil_entity_map.csv"
)

OUTPUT = (
    ROOT
    / "workspace"
    / "dumps"
    / "people_club_refs.csv"
)

MAX_POSITIONS = 8


def find_all(
    data: bytes,
    needle: bytes,
    limit: int = MAX_POSITIONS,
):
    positions = []

    cursor = 0
    total = 0

    while True:

        pos = data.find(
            needle,
            cursor,
        )

        if pos == -1:
            break

        total += 1

        if len(
            positions
        ) < limit:
            positions.append(
                pos
            )

        cursor = pos + 1

    return total, positions


def pack_u32(
    value: int,
) -> bytes:
    return struct.pack(
        "<I",
        value,
    )


def format_positions(
    positions,
) -> str:
    return ",".join(
        f"0x{x:08X}"
        for x in positions
    )


def main():

    with CONFIG.open(
        "r",
        encoding="utf-8",
    ) as file:
        config = json.load(file)

    game_dir = Path(
        config["game_dir"]
    )

    people_path = (
        game_dir
        / "data"
        / "db"
        / "people_db.dat"
    )

    people = (
        people_path.read_bytes()
    )

    with MAP_FILE.open(
        "r",
        encoding="utf-8-sig",
    ) as file:

        mappings = [
            row
            for row in csv.DictReader(
                file,
                delimiter=";",
            )
            if row[
                "status"
            ] == "OK"
        ]

    results = []

    print("=" * 120)
    print(
        " FM06 BRASIL 2026 - "
        "PEOPLE_DB CLUB REFERENCE SCAN"
    )
    print("=" * 120)
    print()

    print(
        f"{'CLUBE':<20}"
        f"{'A':>6}"
        f"{'B':>7}"
        f"{'LANG':>7}"
        f"{'A hits':>10}"
        f"{'B hits':>10}"
        f"{'LANG hits':>12}"
        f"{'A+B':>8}"
        f"{'B+A':>8}"
    )

    print("-" * 120)

    for row in mappings:

        club = row[
            "short_name"
        ]

        field_a = int(
            row[
                "client_field_a"
            ]
        )

        field_b = int(
            row[
                "client_field_b"
            ]
        )

        lang_id = int(
            row[
                "lang_id"
            ]
        )

        a_count, a_pos = find_all(
            people,
            pack_u32(
                field_a
            ),
        )

        b_count, b_pos = find_all(
            people,
            pack_u32(
                field_b
            ),
        )

        lang_count, lang_pos = find_all(
            people,
            pack_u32(
                lang_id
            ),
        )

        ab_count, ab_pos = find_all(
            people,
            pack_u32(
                field_a
            )
            + pack_u32(
                field_b
            ),
        )

        ba_count, ba_pos = find_all(
            people,
            pack_u32(
                field_b
            )
            + pack_u32(
                field_a
            ),
        )

        result = {
            "club": club,

            "field_a": field_a,
            "field_b": field_b,
            "lang_id": lang_id,

            "field_a_hits":
                a_count,

            "field_b_hits":
                b_count,

            "lang_id_hits":
                lang_count,

            "a_b_pair_hits":
                ab_count,

            "b_a_pair_hits":
                ba_count,

            "field_a_positions":
                format_positions(
                    a_pos
                ),

            "field_b_positions":
                format_positions(
                    b_pos
                ),

            "lang_positions":
                format_positions(
                    lang_pos
                ),

            "a_b_positions":
                format_positions(
                    ab_pos
                ),

            "b_a_positions":
                format_positions(
                    ba_pos
                ),
        }

        results.append(
            result
        )

        print(
            f"{club:<20}"
            f"{field_a:>6}"
            f"{field_b:>7}"
            f"{lang_id:>7}"
            f"{a_count:>10}"
            f"{b_count:>10}"
            f"{lang_count:>12}"
            f"{ab_count:>8}"
            f"{ba_count:>8}"
        )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(
                results[0].keys()
            ),
            delimiter=";",
        )

        writer.writeheader()
        writer.writerows(
            results
        )

    print()
    print("=" * 120)
    print(
        " PARES DIRETOS ENCONTRADOS"
    )
    print("=" * 120)
    print()

    pair_results = [
        row
        for row in results
        if (
            row[
                "a_b_pair_hits"
            ]
            or row[
                "b_a_pair_hits"
            ]
        )
    ]

    if not pair_results:
        print(
            "Nenhum par A/B adjacente encontrado."
        )

    for row in pair_results:

        print(
            f"{row['club']:<20} "
            f"A+B={row['a_b_pair_hits']:<4} "
            f"B+A={row['b_a_pair_hits']:<4}"
        )

        if row[
            "a_b_positions"
        ]:
            print(
                "    A+B:",
                row[
                    "a_b_positions"
                ],
            )

        if row[
            "b_a_positions"
        ]:
            print(
                "    B+A:",
                row[
                    "b_a_positions"
                ],
            )

    print()
    print("CSV:")
    print(OUTPUT)


if __name__ == "__main__":
    main()