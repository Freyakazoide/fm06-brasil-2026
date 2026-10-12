from __future__ import annotations

import csv
import json
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(
    0,
    str(ROOT / "src"),
)

from fm06patch.server_db import (
    scan_serialized_strings,
)


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
    / "person_entity_locations.json"
)


PEOPLE = [
    (
        "Sávio",
        "Bortolini Pimentel",
    ),
    (
        "Rogério",
        "Ceni",
    ),
    (
        "Ronaldo",
        "Soares Giovanelli",
    ),
    (
        "Frederico",
        "Chaves Guedes",
    ),
    (
        "Romário",
        "de Souza Fariashe",
    ),
    (
        "Evair",
        "Aparecido Paulino",
    ),
    (
        "Danrlei",
        "de Deus Hinterholtz",
    ),
]


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

        cursor = pos + 1

    return hits


def parse_hex(
    value: str,
) -> int:
    return int(
        value,
        16,
    )


def classify_server_hit(
    offset: int,
    ranges,
):
    for item in ranges:

        if (
            item["start"]
            <= offset
            < item["end"]
        ):
            return (
                "club_history",
                item["club"],
            )

    return (
        "other",
        None,
    )


def nearby_strings(
    data: bytes,
    center: int,
):

    start = max(
        0,
        center - 160,
    )

    end = min(
        len(data),
        center + 320,
    )

    tokens = scan_serialized_strings(
        data,
        start,
        end,
    )

    return [
        {
            "offset":
                token.prefix_offset,

            "offset_hex":
                f"0x{token.prefix_offset:08X}",

            "relative":
                token.prefix_offset
                - center,

            "text":
                token.text,
        }
        for token in tokens
    ]


def nearby_u32(
    data: bytes,
    center: int,
):

    result = []

    for relative in range(
        -64,
        68,
        4,
    ):

        pos = (
            center
            + relative
        )

        if (
            pos < 0
            or pos + 4
            > len(data)
        ):
            continue

        value = struct.unpack_from(
            "<I",
            data,
            pos,
        )[0]

        result.append(
            {
                "relative":
                    relative,

                "offset":
                    pos,

                "offset_hex":
                    f"0x{pos:08X}",

                "value":
                    value,

                "value_hex":
                    f"0x{value:08X}",
            }
        )

    return result


def main():

    with CONFIG.open(
        "r",
        encoding="utf-8",
    ) as file:
        config = json.load(file)

    game_dir = Path(
        config["game_dir"]
    )

    paths = {
        "server_db":
            game_dir
            / "data"
            / "db"
            / "server_db.dat",

        "client_db":
            game_dir
            / "data"
            / "db"
            / "client_db.dat",

        "lang_db":
            game_dir
            / "data"
            / "db"
            / "lang_db.dat",

        "people_db":
            game_dir
            / "data"
            / "db"
            / "people_db.dat",
    }

    data = {
        name: path.read_bytes()
        for name, path
        in paths.items()
    }

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
            if (
                row["status"] == "OK"
                and row[
                    "server_offset"
                ]
            )
        ]

    mappings.sort(
        key=lambda row:
        parse_hex(
            row[
                "server_offset"
            ]
        )
    )

    ranges = []

    for index, row in enumerate(
        mappings
    ):

        start = parse_hex(
            row[
                "server_offset"
            ]
        )

        if index + 1 < len(
            mappings
        ):
            end = parse_hex(
                mappings[
                    index + 1
                ][
                    "server_offset"
                ]
            )
        else:
            end = (
                start + 0x400
            )

        ranges.append(
            {
                "club":
                    row[
                        "short_name"
                    ],
                "start":
                    start,
                "end":
                    end,
            }
        )

    output = {}

    print("=" * 110)
    print(
        " FM06 BRASIL 2026 - "
        "PERSON ENTITY LOCATOR"
    )
    print("=" * 110)

    for first, last in PEOPLE:

        full_label = (
            f"{first} {last}"
        )

        pair = (
            serialized_token(
                first
            )
            + serialized_token(
                last
            )
        )

        print()
        print(full_label)
        print("-" * len(full_label))

        person_result = {}

        for source_name in [
            "server_db",
            "client_db",
            "lang_db",
            "people_db",
        ]:

            hits = find_all(
                data[
                    source_name
                ],
                pair,
            )

            print(
                f"{source_name:<10}: "
                f"{len(hits)}"
            )

            source_hits = []

            for hit in hits:

                item = {
                    "offset":
                        hit,

                    "offset_hex":
                        f"0x{hit:08X}",
                }

                if source_name == "server_db":

                    kind, club = (
                        classify_server_hit(
                            hit,
                            ranges,
                        )
                    )

                    item[
                        "kind"
                    ] = kind

                    item[
                        "club"
                    ] = club

                    if kind == "other":

                        item[
                            "nearby_strings"
                        ] = nearby_strings(
                            data[
                                source_name
                            ],
                            hit,
                        )

                        item[
                            "nearby_u32"
                        ] = nearby_u32(
                            data[
                                source_name
                            ],
                            hit,
                        )

                source_hits.append(
                    item
                )

                suffix = ""

                if source_name == "server_db":

                    kind = item.get(
                        "kind"
                    )

                    club = item.get(
                        "club"
                    )

                    if kind == "club_history":
                        suffix = (
                            f"  CLUB_HISTORY "
                            f"[{club}]"
                        )
                    else:
                        suffix = (
                            "  OTHER"
                        )

                print(
                    f"    "
                    f"0x{hit:08X}"
                    f"{suffix}"
                )

            person_result[
                source_name
            ] = source_hits

        output[
            full_label
        ] = person_result

    print()
    print("=" * 110)
    print(
        " SERVER_DB - OCORRÊNCIAS FORA "
        "DOS REGISTROS DE CLUBE"
    )
    print("=" * 110)

    found_other = False

    for name, sources in (
        output.items()
    ):

        for hit in sources[
            "server_db"
        ]:

            if hit.get(
                "kind"
            ) != "other":
                continue

            found_other = True

            print()
            print(
                name,
                hit[
                    "offset_hex"
                ],
            )

            print(
                "  strings próximas:"
            )

            for item in hit.get(
                "nearby_strings",
                [],
            ):

                print(
                    f"    "
                    f"{item['relative']:+5} "
                    f"{item['offset_hex']} "
                    f"{item['text']!r}"
                )

            print(
                "  u32 próximos:"
            )

            for item in hit.get(
                "nearby_u32",
                [],
            ):

                value = item[
                    "value"
                ]

                if (
                    0
                    < value
                    < 50_000_000
                ):

                    print(
                        f"    "
                        f"{item['relative']:+4} "
                        f"{value:<10} "
                        f"{item['value_hex']}"
                    )

    if not found_other:
        print()
        print(
            "Nenhuma ocorrência adicional "
            "encontrada."
        )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=4,
        )

    print()
    print("JSON:")
    print(OUTPUT)


if __name__ == "__main__":
    main()