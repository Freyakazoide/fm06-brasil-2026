from __future__ import annotations

import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

CONFIG = (
    ROOT
    / "config"
    / "local.json"
)


PLAYERS = [
    {
        "name": "Sávio",
        "player_uid": 104318,

        "club": "Zaragoza",
        "club_uid": 1749,

        "field_a": 1324,
        "field_b": 1746,

        "nation_internal_id": 170,
    },

    {
        "name": "Fred",
        "player_uid": 321081,

        "club": "Lyon",
        "club_uid": 865,

        "field_a": 589,
        "field_b": 864,

        "nation_internal_id": 143,
    },

    {
        "name": "Rogério Ceni",
        "player_uid": 3300977,

        "club": "São Paulo",
        "club_uid": 337,

        "field_a": 212,
        "field_b": 336,

        "nation_internal_id": 189,
    },
]


RADIUS = 4096


def pack_u16(
    value: int,
) -> bytes:
    return struct.pack(
        "<H",
        value,
    )


def pack_u32(
    value: int,
) -> bytes:
    return struct.pack(
        "<I",
        value,
    )


def find_all(
    data: bytes,
    needle: bytes,
):
    result = []

    cursor = 0

    while True:

        position = data.find(
            needle,
            cursor,
        )

        if position == -1:
            break

        result.append(
            position
        )

        cursor = (
            position + 1
        )

    return result


def find_inside(
    block: bytes,
    needle: bytes,
):
    result = []

    cursor = 0

    while True:

        position = block.find(
            needle,
            cursor,
        )

        if position == -1:
            break

        result.append(
            position
        )

        cursor = (
            position + 1
        )

    return result


def nearest(
    values: list[int],
):
    if not values:
        return None

    return min(
        values,
        key=lambda value:
            abs(value),
    )


def inspect_hit(
    data: bytes,
    player_offset: int,
    player: dict,
):

    start = max(
        0,
        player_offset - RADIUS,
    )

    end = min(
        len(data),
        player_offset + RADIUS,
    )

    block = data[
        start:end
    ]

    relative_center = (
        player_offset - start
    )

    field_a = player[
        "field_a"
    ]

    field_b = player[
        "field_b"
    ]

    club_uid = player[
        "club_uid"
    ]

    nation_internal = player[
        "nation_internal_id"
    ]

    patterns = {
        "A_u32":
            pack_u32(
                field_a
            ),

        "B_u32":
            pack_u32(
                field_b
            ),

        "A_u16":
            pack_u16(
                field_a
            ),

        "B_u16":
            pack_u16(
                field_b
            ),

        "UID_u32":
            pack_u32(
                club_uid
            ),

        "NATION_u32":
            pack_u32(
                nation_internal
            ),

        "A32_B32":
            (
                pack_u32(
                    field_a
                )
                + pack_u32(
                    field_b
                )
            ),

        "B32_A32":
            (
                pack_u32(
                    field_b
                )
                + pack_u32(
                    field_a
                )
            ),

        "A16_B16":
            (
                pack_u16(
                    field_a
                )
                + pack_u16(
                    field_b
                )
            ),

        "B16_A16":
            (
                pack_u16(
                    field_b
                )
                + pack_u16(
                    field_a
                )
            ),

        # Mesmo formato observado no
        # header dos clubes:
        #
        # field_a
        # field_b
        # 00
        # nation_internal
        "CLUB_KEY":
            (
                pack_u32(
                    field_a
                )
                + pack_u32(
                    field_b
                )
                + b"\x00"
                + pack_u32(
                    nation_internal
                )
            ),
    }

    matches = {}

    for name, pattern in (
        patterns.items()
    ):

        local_hits = find_inside(
            block,
            pattern,
        )

        relatives = [
            local
            - relative_center
            for local in local_hits
        ]

        matches[
            name
        ] = relatives

    # -------------------------------------------------
    # SCORE
    # -------------------------------------------------

    score = 0

    if matches[
        "CLUB_KEY"
    ]:
        score += 1000

    if matches[
        "A32_B32"
    ]:
        score += 500

    if matches[
        "B32_A32"
    ]:
        score += 500

    if matches[
        "A16_B16"
    ]:
        score += 250

    if matches[
        "B16_A16"
    ]:
        score += 250

    if matches[
        "A_u32"
    ]:
        score += 40

    if matches[
        "B_u32"
    ]:
        score += 40

    if matches[
        "A_u16"
    ]:
        score += 10

    if matches[
        "B_u16"
    ]:
        score += 10

    if matches[
        "UID_u32"
    ]:
        score += 20

    return {
        "player_offset":
            player_offset,

        "score":
            score,

        "matches":
            matches,
    }


def format_nearest(
    values,
):
    value = nearest(
        values
    )

    if value is None:
        return "-"

    return (
        f"{value:+d}"
        f" (0x{abs(value):X})"
    )


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

    print("=" * 125)
    print(
        " FM06 BRASIL 2026 - "
        "CURRENT CLUB INTERNAL TRACE"
    )
    print("=" * 125)

    for player in PLAYERS:

        player_uid = (
            player[
                "player_uid"
            ]
        )

        hits = find_all(
            people,
            pack_u32(
                player_uid
            ),
        )

        results = [
            inspect_hit(
                people,
                hit,
                player,
            )
            for hit in hits
        ]

        results.sort(
            key=lambda item: (
                -item[
                    "score"
                ],
                item[
                    "player_offset"
                ],
            )
        )

        print()
        print("=" * 125)

        print(
            f"{player['name']} "
            f"(player_uid="
            f"{player_uid})"
        )

        print(
            f"CURRENT CLUB: "
            f"{player['club']} "
            f"uid="
            f"{player['club_uid']} "
            f"KEY=("
            f"{player['field_a']},"
            f"{player['field_b']},"
            f"{player['nation_internal_id']}"
            f")"
        )

        print("=" * 125)

        print()
        print(
            f"{'#':>2} "
            f"{'PLAYER OFFSET':>12} "
            f"{'SCORE':>6} "
            f"{'A32':>14} "
            f"{'B32':>14} "
            f"{'A+B32':>14} "
            f"{'A+B16':>14} "
            f"{'PUBLIC UID':>14}"
        )

        print("-" * 125)

        for index, result in enumerate(
            results,
            start=1,
        ):

            matches = (
                result[
                    "matches"
                ]
            )

            print(
                f"{index:>2} "
                f"0x"
                f"{result['player_offset']:08X} "
                f"{result['score']:>6} "
                f"{format_nearest(matches['A_u32']):>14} "
                f"{format_nearest(matches['B_u32']):>14} "
                f"{format_nearest(matches['A32_B32']):>14} "
                f"{format_nearest(matches['A16_B16']):>14} "
                f"{format_nearest(matches['UID_u32']):>14}"
            )

        if not results:
            continue

        best = results[
            0
        ]

        print()
        print(
            "MELHOR CANDIDATO"
        )

        print("-" * 125)

        print(
            f"player UID @ "
            f"0x"
            f"{best['player_offset']:08X}"
        )

        print(
            f"score: "
            f"{best['score']}"
        )

        for name, values in (
            best[
                "matches"
            ].items()
        ):

            if not values:
                continue

            formatted = (
                ", ".join(
                    f"{value:+d}"
                    for value
                    in values[:20]
                )
            )

            print(
                f"{name:<14}: "
                f"{formatted}"
            )


if __name__ == "__main__":
    main()