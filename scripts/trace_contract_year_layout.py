from __future__ import annotations

import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "local.json"

RADIUS = 4096
MAX_RESULTS = 12


PLAYERS = [
    {
        "name": "Sávio",
        "uid": 104318,
        "start_year": 2003,
        "end_year": 2007,
    },
    {
        "name": "Zinedine Zidane",
        "uid": 8076,
        "start_year": 2004,
        "end_year": 2007,
    },
    {
        "name": "Rogério Ceni",
        "uid": 3300977,
        "start_year": 2004,
        "end_year": 2008,
    },
]


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


def find_pattern(
    block: bytes,
    pattern: bytes,
):
    result = []
    cursor = 0

    while True:

        pos = block.find(
            pattern,
            cursor,
        )

        if pos == -1:
            break

        result.append(pos)
        cursor = pos + 1

    return result


def year_patterns(
    year: int,
):
    return {
        "u16":
            struct.pack(
                "<H",
                year,
            ),

        "u32":
            struct.pack(
                "<I",
                year,
            ),
    }


def year_hits(
    data: bytes,
    region_start: int,
    region_end: int,
    center: int,
    year: int,
):
    block = data[
        region_start:
        region_end
    ]

    results = []

    for kind, pattern in (
        year_patterns(
            year
        ).items()
    ):

        for local in find_pattern(
            block,
            pattern,
        ):

            absolute = (
                region_start + local
            )

            results.append(
                {
                    "kind":
                        kind,

                    "offset":
                        absolute,

                    "relative":
                        absolute - center,
                }
            )

    return results


def context_hex(
    data: bytes,
    offset: int,
    before: int = 12,
    after: int = 20,
):
    start = max(
        0,
        offset - before,
    )

    end = min(
        len(data),
        offset + after,
    )

    chunk = data[
        start:end
    ]

    return (
        start,
        " ".join(
            f"{value:02X}"
            for value in chunk
        ),
    )


def build_pairs(
    starts,
    ends,
):
    pairs = []

    for start in starts:

        for end in ends:

            distance = (
                end["offset"]
                - start["offset"]
            )

            # Contrato provavelmente guarda
            # as duas datas razoavelmente perto.
            if abs(distance) > 256:
                continue

            score = 0

            # Mesmo tipo de representação é
            # mais interessante.
            if (
                start["kind"]
                == end["kind"]
            ):
                score += 100

            # Quanto mais próximas, melhor.
            score += max(
                0,
                256 - abs(distance),
            )

            pairs.append(
                {
                    "score":
                        score,

                    "start":
                        start,

                    "end":
                        end,

                    "distance":
                        distance,
                }
            )

    pairs.sort(
        key=lambda item: (
            -item["score"],
            abs(
                item["distance"]
            ),
        )
    )

    return pairs


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

    print("=" * 120)
    print(
        " FM06 BRASIL 2026 - "
        "CONTRACT YEAR LAYOUT TRACE"
    )
    print("=" * 120)

    for player in PLAYERS:

        uid_bytes = struct.pack(
            "<I",
            player["uid"],
        )

        uid_hits = find_all(
            people,
            uid_bytes,
        )

        results = []

        for uid_hit in uid_hits:

            region_start = max(
                0,
                uid_hit - RADIUS,
            )

            region_end = min(
                len(people),
                uid_hit + RADIUS,
            )

            starts = year_hits(
                people,
                region_start,
                region_end,
                uid_hit,
                player[
                    "start_year"
                ],
            )

            ends = year_hits(
                people,
                region_start,
                region_end,
                uid_hit,
                player[
                    "end_year"
                ],
            )

            pairs = build_pairs(
                starts,
                ends,
            )

            if not pairs:
                continue

            best_pair = pairs[0]

            results.append(
                {
                    "uid_hit":
                        uid_hit,

                    "score":
                        best_pair[
                            "score"
                        ],

                    "pair":
                        best_pair,

                    "all_pairs":
                        pairs,
                }
            )

        results.sort(
            key=lambda item: (
                -item["score"],
                item["uid_hit"],
            )
        )

        print()
        print("=" * 120)

        print(
            f"{player['name']} "
            f"(UID {player['uid']})"
        )

        print(
            f"start_year="
            f"{player['start_year']} "
            f"end_year="
            f"{player['end_year']}"
        )

        print(
            f"UID hits="
            f"{len(uid_hits)} "
            f"candidatos="
            f"{len(results)}"
        )

        print("=" * 120)

        for index, result in enumerate(
            results[:MAX_RESULTS],
            start=1,
        ):

            pair = result[
                "pair"
            ]

            start = pair[
                "start"
            ]

            end = pair[
                "end"
            ]

            print()
            print(
                f"#{index} "
                f"UID @ "
                f"0x"
                f"{result['uid_hit']:08X} "
                f"score="
                f"{result['score']}"
            )

            print(
                f"   START "
                f"{start['kind']:<3} "
                f"@ "
                f"0x"
                f"{start['offset']:08X} "
                f"rel="
                f"{start['relative']:+d}"
            )

            print(
                f"   END   "
                f"{end['kind']:<3} "
                f"@ "
                f"0x"
                f"{end['offset']:08X} "
                f"rel="
                f"{end['relative']:+d}"
            )

            print(
                f"   distância START→END: "
                f"{pair['distance']:+d}"
            )

            start_context_offset, (
                start_context
            ) = context_hex(
                people,
                start[
                    "offset"
                ],
            )

            end_context_offset, (
                end_context
            ) = context_hex(
                people,
                end[
                    "offset"
                ],
            )

            print(
                f"   START HEX "
                f"0x"
                f"{start_context_offset:08X}:"
            )

            print(
                f"      "
                f"{start_context}"
            )

            print(
                f"   END HEX   "
                f"0x"
                f"{end_context_offset:08X}:"
            )

            print(
                f"      "
                f"{end_context}"
            )


if __name__ == "__main__":
    main()