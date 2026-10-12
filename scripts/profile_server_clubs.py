from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(
    0,
    str(ROOT / "src"),
)

from fm06patch.server_db import (
    find_exact_string,
    parse_header,
    scan_serialized_strings,
)


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

OUTPUT = (
    ROOT
    / "workspace"
    / "dumps"
    / "server_club_schema.csv"
)

TOKENS_OUTPUT = (
    ROOT
    / "workspace"
    / "dumps"
    / "server_club_tokens.json"
)


SCAN_BYTES = 0x280


def parse_hex(
    value: str,
) -> int:
    return int(
        value,
        16,
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

    server_path = (
        game_dir
        / "data"
        / "db"
        / "server_db.dat"
    )

    server = (
        server_path.read_bytes()
    )

    with MAP_FILE.open(
        "r",
        encoding="utf-8-sig",
    ) as file:

        mappings = list(
            csv.DictReader(
                file,
                delimiter=";",
            )
        )

    mappings = [
        row
        for row in mappings
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

    rows = []
    all_tokens = {}

    print("=" * 120)
    print(
        " FM06 BRASIL 2026 - "
        "SERVER CLUB SCHEMA"
    )
    print("=" * 120)
    print()

    first_prefixes = []

    for index, row in enumerate(
        mappings
    ):

        offset = parse_hex(
            row[
                "server_offset"
            ]
        )

        if index + 1 < len(
            mappings
        ):
            next_offset = parse_hex(
                mappings[
                    index + 1
                ][
                    "server_offset"
                ]
            )

            end = min(
                next_offset,
                offset + SCAN_BYTES,
            )

        else:
            end = min(
                len(server),
                offset + SCAN_BYTES,
            )

        header = parse_header(
            server,
            offset,
        )

        tokens = (
            scan_serialized_strings(
                server,
                offset,
                end,
            )
        )

        full_name = row[
            "full_name"
        ]

        short_name = row[
            "short_name"
        ]

        full_token = (
            find_exact_string(
                tokens,
                full_name,
            )
        )

        short_token = (
            find_exact_string(
                tokens,
                short_name,
            )
        )

        if tokens:
            first_relative = (
                tokens[0].prefix_offset
                - offset
            )

            first_prefixes.append(
                first_relative
            )
        else:
            first_relative = None

        def relative(
            token,
            attribute: str,
        ):
            if token is None:
                return None

            return (
                getattr(
                    token,
                    attribute,
                )
                - offset
            )

        output_row = {
            "club": short_name,

            "lang_id": int(
                row[
                    "lang_id"
                ]
            ),

            "server_offset": (
                f"0x{offset:08X}"
            ),

            "field_a": (
                header.field_a
            ),

            "field_b": (
                header.field_b
            ),

            "zero_flag": (
                header.zero_flag
            ),

            "group_marker": (
                header.group_marker
            ),

            "first_string_prefix_rel": (
                first_relative
            ),

            "full_prefix_rel": (
                relative(
                    full_token,
                    "prefix_offset",
                )
            ),

            "full_text_rel": (
                relative(
                    full_token,
                    "text_offset",
                )
            ),

            "short_prefix_rel": (
                relative(
                    short_token,
                    "prefix_offset",
                )
            ),

            "short_text_rel": (
                relative(
                    short_token,
                    "text_offset",
                )
            ),

            "string_count": (
                len(tokens)
            ),
        }

        rows.append(
            output_row
        )

        formatted_tokens = []

        for token in tokens:

            formatted_tokens.append(
                {
                    "prefix_rel": (
                        token.prefix_offset
                        - offset
                    ),
                    "text_rel": (
                        token.text_offset
                        - offset
                    ),
                    "length": (
                        token.length
                    ),
                    "text": (
                        token.text
                    ),
                }
            )

        all_tokens[
            short_name
        ] = formatted_tokens

        full_rel = (
            output_row[
                "full_text_rel"
            ]
        )

        short_rel = (
            output_row[
                "short_text_rel"
            ]
        )

        print(
            f"{short_name:<20} "
            f"KEY=("
            f"{header.field_a},"
            f"{header.field_b},"
            f"{header.group_marker}"
            f")  "
            f"FIRST="
            f"{str(first_relative):>4}  "
            f"FULL="
            f"{str(full_rel):>4}  "
            f"SHORT="
            f"{str(short_rel):>4}  "
            f"STRINGS="
            f"{len(tokens):>2}"
        )

    print()
    print("=" * 120)
    print(
        " ESTRUTURA COMUM"
    )
    print("=" * 120)
    print()

    print(
        "Primeiro prefixo de string:"
    )

    counts = {}

    for value in first_prefixes:
        counts[value] = (
            counts.get(
                value,
                0,
            )
            + 1
        )

    for value, count in sorted(
        counts.items()
    ):
        print(
            f"  +0x{value:X}: "
            f"{count}/"
            f"{len(first_prefixes)} clubes"
        )

    print()
    print("=" * 120)
    print(
        " FLAMENGO - TOKENS REAIS"
    )
    print("=" * 120)
    print()

    for token in all_tokens.get(
        "Flamengo",
        [],
    ):

        print(
            f"+0x"
            f"{token['prefix_rel']:03X} "
            f"len={token['length']:>2} "
            f"text=+0x"
            f"{token['text_rel']:03X}  "
            f"{token['text']!r}"
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
                rows[0].keys()
            ),
            delimiter=";",
        )

        writer.writeheader()
        writer.writerows(
            rows
        )

    with TOKENS_OUTPUT.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            all_tokens,
            file,
            ensure_ascii=False,
            indent=4,
        )

    print()
    print("CSV:")
    print(OUTPUT)

    print()
    print("Tokens:")
    print(TOKENS_OUTPUT)


if __name__ == "__main__":
    main()