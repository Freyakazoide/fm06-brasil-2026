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

PAIR_DISTANCE = 14
SEARCH_RADIUS = 4096
MAX_RESULTS = 12


PLAYERS = [
    {
        "name": "Sávio",
        "uid": 104318,

        "start_year": 2003,
        "end_year": 2007,

        "club_uid": 1749,
        "field_a": 1324,
        "field_b": 1746,
        "nation_internal_id": 170,
    },

    {
        "name": "Zinedine Zidane",
        "uid": 8076,

        "start_year": 2004,
        "end_year": 2007,

        "club_uid": 1736,
        "field_a": 1313,
        "field_b": 1733,
        "nation_internal_id": 170,
    },

    {
        "name": "Rogério Ceni",
        "uid": 3300977,

        "start_year": 2004,
        "end_year": 2008,

        "club_uid": 337,
        "field_a": 212,
        "field_b": 336,
        "nation_internal_id": 189,
    },
]


def p16(
    value: int,
) -> bytes:
    return struct.pack(
        "<H",
        value,
    )


def p32(
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

        pos = data.find(
            needle,
            cursor,
        )

        if pos == -1:
            break

        result.append(
            pos
        )

        cursor = (
            pos + 1
        )

    return result


def find_contract_year_pairs(
    data: bytes,
    start_year: int,
    end_year: int,
):
    """
    Estrutura observada em Zidane e Ceni:

        offset +0x00 = END YEAR  (u16)
        offset +0x0E = START YEAR (u16)
    """

    end_pattern = p16(
        end_year
    )

    start_pattern = p16(
        start_year
    )

    candidates = []

    for end_offset in find_all(
        data,
        end_pattern,
    ):

        start_offset = (
            end_offset
            + PAIR_DISTANCE
        )

        if (
            start_offset + 2
            > len(data)
        ):
            continue

        if (
            data[
                start_offset:
                start_offset + 2
            ]
            != start_pattern
        ):
            continue

        candidates.append(
            {
                "end_offset":
                    end_offset,

                "start_offset":
                    start_offset,
            }
        )

    return candidates


def nearest_distance(
    positions: list[int],
    center: int,
):
    if not positions:
        return None

    nearest = min(
        positions,
        key=lambda position:
            abs(
                position - center
            ),
    )

    return (
        nearest,
        nearest - center,
    )


def hits_near(
    data: bytes,
    center: int,
    needle: bytes,
    radius: int = SEARCH_RADIUS,
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

    cursor = 0

    while True:

        local = block.find(
            needle,
            cursor,
        )

        if local == -1:
            break

        absolute = (
            start + local
        )

        result.append(
            absolute
        )

        cursor = (
            local + 1
        )

    return result


def score_candidate(
    data: bytes,
    candidate: dict,
    player: dict,
    core_offset: int,
):
    center = candidate[
        "end_offset"
    ]

    details = {}

    patterns = {
        "player_uid":
            p32(
                player["uid"]
            ),

        "club_uid":
            p32(
                player["club_uid"]
            ),

        "field_a_u32":
            p32(
                player["field_a"]
            ),

        "field_b_u32":
            p32(
                player["field_b"]
            ),

        "nation_u32":
            p32(
                player[
                    "nation_internal_id"
                ]
            ),
    }

    score = 0

    for name, needle in (
        patterns.items()
    ):

        positions = hits_near(
            data,
            center,
            needle,
        )

        nearest = nearest_distance(
            positions,
            center,
        )

        details[
            name
        ] = nearest

    # ---------------------------------------------
    # CORE RECORD PRÓXIMO
    # ---------------------------------------------

    core_distance = (
        core_offset
        - center
    )

    details[
        "core_distance"
    ] = core_distance

    if (
        abs(core_distance)
        <= SEARCH_RADIUS
    ):
        score += 500

        # Quanto mais perto do core,
        # melhor.
        score += max(
            0,
            200
            - (
                abs(core_distance)
                // 16
            ),
        )

    # ---------------------------------------------
    # UID DO JOGADOR
    # ---------------------------------------------

    uid_match = details[
        "player_uid"
    ]

    if uid_match is not None:

        _, relative = uid_match

        score += 400

        score += max(
            0,
            100
            - (
                abs(relative)
                // 16
            ),
        )

    # ---------------------------------------------
    # CLUBE
    # ---------------------------------------------

    if details[
        "club_uid"
    ] is not None:
        score += 120

    if details[
        "field_a_u32"
    ] is not None:
        score += 80

    if details[
        "field_b_u32"
    ] is not None:
        score += 80

    if details[
        "nation_u32"
    ] is not None:
        score += 20

    return (
        score,
        details,
    )


def format_nearest(
    value,
):
    if value is None:
        return "-"

    absolute, relative = value

    return (
        f"0x{absolute:08X} "
        f"({relative:+d})"
    )


def hex_block(
    data: bytes,
    center: int,
    before: int = 24,
    after: int = 64,
):
    start = max(
        0,
        center - before,
    )

    end = min(
        len(data),
        center + after,
    )

    lines = []

    for offset in range(
        start,
        end,
        16,
    ):

        chunk = data[
            offset:
            min(
                end,
                offset + 16,
            )
        ]

        lines.append(
            (
                offset,
                offset - center,
                " ".join(
                    f"{byte:02X}"
                    for byte in chunk
                ),
            )
        )

    return lines


def main():

    with CONFIG.open(
        "r",
        encoding="utf-8",
    ) as file:

        config = json.load(
            file
        )

    people_path = (
        Path(
            config["game_dir"]
        )
        / "data"
        / "db"
        / "people_db.dat"
    )

    people = (
        people_path.read_bytes()
    )

    people_db = PeopleDatabase(
        people
    )

    print("=" * 125)
    print(
        " FM06 BRASIL 2026 - "
        "CONTRACT BLOCK LOCATOR"
    )
    print("=" * 125)

    for player in PLAYERS:

        core = people_db.player(
            player["uid"]
        )

        candidates = (
            find_contract_year_pairs(
                people,
                player[
                    "start_year"
                ],
                player[
                    "end_year"
                ],
            )
        )

        ranked = []

        for candidate in candidates:

            score, details = (
                score_candidate(
                    people,
                    candidate,
                    player,
                    core.uid_offset,
                )
            )

            ranked.append(
                {
                    **candidate,
                    "score":
                        score,
                    "details":
                        details,
                }
            )

        ranked.sort(
            key=lambda item: (
                -item[
                    "score"
                ],
                abs(
                    item[
                        "details"
                    ][
                        "core_distance"
                    ]
                ),
                item[
                    "end_offset"
                ],
            )
        )

        print()
        print("=" * 125)

        print(
            f"{player['name']} "
            f"(UID {player['uid']})"
        )

        print(
            f"Contrato: "
            f"{player['start_year']} "
            f"→ "
            f"{player['end_year']}"
        )

        print(
            f"Player core: "
            f"{core.uid_offset_hex}"
        )

        print(
            f"pares globais encontrados: "
            f"{len(candidates)}"
        )

        print("=" * 125)

        for index, item in enumerate(
            ranked[:MAX_RESULTS],
            start=1,
        ):

            details = item[
                "details"
            ]

            print()
            print(
                f"#{index} "
                f"END_YEAR @ "
                f"0x"
                f"{item['end_offset']:08X} "
                f"START_YEAR @ "
                f"0x"
                f"{item['start_offset']:08X} "
                f"score="
                f"{item['score']}"
            )

            print(
                f"   core distance : "
                f"{details['core_distance']:+d}"
            )

            print(
                f"   player UID    : "
                f"{format_nearest(details['player_uid'])}"
            )

            print(
                f"   club UID      : "
                f"{format_nearest(details['club_uid'])}"
            )

            print(
                f"   field A       : "
                f"{format_nearest(details['field_a_u32'])}"
            )

            print(
                f"   field B       : "
                f"{format_nearest(details['field_b_u32'])}"
            )

            print(
                f"   nation        : "
                f"{format_nearest(details['nation_u32'])}"
            )

            if index == 1:

                print()
                print(
                    "   HEX DO MELHOR CANDIDATO"
                )

                for (
                    offset,
                    relative,
                    text,
                ) in hex_block(
                    people,
                    item[
                        "end_offset"
                    ],
                ):

                    print(
                        f"   {relative:+5} "
                        f"0x{offset:08X}  "
                        f"{text}"
                    )


if __name__ == "__main__":
    main()