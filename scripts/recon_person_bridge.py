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


FIRST_NAME = "Sávio"
LAST_NAME = "Bortolini Pimentel"

MAX_PAIR_DISTANCE = 256
MAX_ID_HITS = 50


def u32(
    data: bytes,
    offset: int,
) -> int:
    return struct.unpack_from(
        "<I",
        data,
        offset,
    )[0]


def serialized_token(
    text: str,
) -> bytes:

    raw = text.encode(
        "utf-16le"
    )

    return (
        struct.pack(
            "<I",
            len(raw) // 2,
        )
        + raw
        + b"\x00\x00"
    )


def find_all(
    data: bytes,
    needle: bytes,
    max_hits: int | None = None,
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

        hits.append(
            pos
        )

        if (
            max_hits is not None
            and len(hits)
            >= max_hits
        ):
            break

        cursor = (
            pos + 1
        )

    return hits


def raw_searches(
    data: bytes,
    text: str,
):
    result = {}

    encodings = [
        "utf-16le",
        "utf-8",
        "cp1252",
    ]

    for encoding in encodings:

        try:
            needle = text.encode(
                encoding
            )
        except UnicodeEncodeError:
            continue

        hits = find_all(
            data,
            needle,
            max_hits=20,
        )

        result[
            encoding
        ] = hits

    return result


def count_id_hits(
    data: bytes,
    value: int,
):
    if not (
        1 <= value <= 100_000_000
    ):
        return []

    needle = struct.pack(
        "<I",
        value,
    )

    return find_all(
        data,
        needle,
        max_hits=MAX_ID_HITS,
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

    lang_path = (
        game_dir
        / "data"
        / "db"
        / "lang_db.dat"
    )

    people_path = (
        game_dir
        / "data"
        / "db"
        / "people_db.dat"
    )

    lang = (
        lang_path.read_bytes()
    )

    people = (
        people_path.read_bytes()
    )

    print("=" * 100)
    print(
        " FM06 BRASIL 2026 - "
        "PERSON ENTITY BRIDGE"
    )
    print("=" * 100)

    print()
    print(
        "1. BUSCA CRUA NO PEOPLE_DB"
    )
    print("-" * 100)

    for text in [
        FIRST_NAME,
        LAST_NAME,
    ]:

        print()
        print(repr(text))

        searches = raw_searches(
            people,
            text,
        )

        for (
            encoding,
            hits,
        ) in searches.items():

            offsets = ", ".join(
                f"0x{x:08X}"
                for x in hits
            )

            print(
                f"  {encoding:<10} "
                f"{len(hits):>2} "
                f"{offsets}"
            )

    first_token = serialized_token(
        FIRST_NAME
    )

    last_token = serialized_token(
        LAST_NAME
    )

    first_hits = find_all(
        lang,
        first_token,
    )

    last_hits = find_all(
        lang,
        last_token,
    )

    print()
    print(
        "2. STRINGS SERIALIZADAS NO LANG_DB"
    )
    print("-" * 100)

    print(
        f"{FIRST_NAME!r}: "
        f"{len(first_hits)}"
    )

    print(
        f"{LAST_NAME!r}: "
        f"{len(last_hits)}"
    )

    pairs = []

    for first in first_hits:

        nearest = None

        for last in last_hits:

            distance = (
                last - first
            )

            if not (
                0 < distance
                <= MAX_PAIR_DISTANCE
            ):
                continue

            if (
                nearest is None
                or distance
                < nearest[0]
            ):
                nearest = (
                    distance,
                    last,
                )

        if nearest is not None:
            pairs.append(
                (
                    first,
                    nearest[1],
                    nearest[0],
                )
            )

    print()
    print(
        f"Pares próximos: "
        f"{len(pairs)}"
    )

    candidates = []

    for pair_index, (
        first,
        last,
        distance,
    ) in enumerate(
        pairs,
        start=1,
    ):

        candidate_values = []

        for relative in [
            -4,
            -8,
            -12,
            -16,
        ]:

            pos = (
                first + relative
            )

            if pos < 0:
                continue

            value = u32(
                lang,
                pos,
            )

            hits = count_id_hits(
                people,
                value,
            )

            candidate_values.append(
                {
                    "relative": relative,
                    "value": value,
                    "people_hits": hits,
                }
            )

        nonzero = [
            item
            for item in candidate_values
            if item[
                "people_hits"
            ]
        ]

        if nonzero:

            best_hit_count = min(
                len(
                    item[
                        "people_hits"
                    ]
                )
                for item in nonzero
            )

        else:
            best_hit_count = 999999

        candidates.append(
            {
                "pair_index": pair_index,
                "first": first,
                "last": last,
                "distance": distance,
                "values":
                    candidate_values,
                "best_hit_count":
                    best_hit_count,
            }
        )

    candidates.sort(
        key=lambda item: (
            item[
                "best_hit_count"
            ],
            item[
                "first"
            ],
        )
    )

    print()
    print(
        "3. CANDIDATOS DE ID"
    )
    print("-" * 100)

    if not candidates:
        print(
            "Nenhum par de nomes encontrado."
        )
        return

    for candidate in (
        candidates[:30]
    ):

        print()
        print(
            f"LANG pair #{candidate['pair_index']}"
        )

        print(
            f"  first prefix : "
            f"0x{candidate['first']:08X}"
        )

        print(
            f"  last prefix  : "
            f"0x{candidate['last']:08X}"
        )

        print(
            f"  distância    : "
            f"0x{candidate['distance']:X}"
        )

        for item in (
            candidate["values"]
        ):

            hits = item[
                "people_hits"
            ]

            hit_text = ", ".join(
                f"0x{x:08X}"
                for x in hits[:8]
            )

            if len(hits) == MAX_ID_HITS:
                count_text = (
                    f">={MAX_ID_HITS}"
                )
            else:
                count_text = str(
                    len(hits)
                )

            print(
                f"  "
                f"{item['relative']:+4} "
                f"value={item['value']:<10} "
                f"people_hits={count_text:<4} "
                f"{hit_text}"
            )


if __name__ == "__main__":
    main()