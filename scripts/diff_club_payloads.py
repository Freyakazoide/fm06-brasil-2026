from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(
    0,
    str(ROOT / "src"),
)

from fm06patch.server_db import (
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
    / "club_payload_diff.csv"
)

MAX_SCAN = 0x300


def parse_hex(value: str) -> int:
    return int(
        value,
        16,
    )


def format_counter(
    counter: Counter,
) -> str:

    values = []

    for text, count in counter.items():

        if count == 1:
            values.append(text)
        else:
            values.append(
                f"{text} x{count}"
            )

    return " | ".join(values)


def scan_record(
    data: bytes,
    offset: int,
    next_offset: int | None,
):
    if next_offset is None:
        end = min(
            len(data),
            offset + MAX_SCAN,
        )
    else:
        end = min(
            len(data),
            next_offset,
            offset + MAX_SCAN,
        )

    return scan_serialized_strings(
        data,
        offset,
        end,
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

    client = (
        game_dir
        / "data"
        / "db"
        / "client_db.dat"
    ).read_bytes()

    server = (
        game_dir
        / "data"
        / "db"
        / "server_db.dat"
    ).read_bytes()

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
                and row["client_offset"]
                and row["server_offset"]
            )
        ]

    client_sorted = sorted(
        mappings,
        key=lambda row:
        parse_hex(
            row["client_offset"]
        ),
    )

    server_sorted = sorted(
        mappings,
        key=lambda row:
        parse_hex(
            row["server_offset"]
        ),
    )

    next_client = {}

    for index, row in enumerate(
        client_sorted
    ):
        offset = parse_hex(
            row["client_offset"]
        )

        if index + 1 < len(
            client_sorted
        ):
            next_client[offset] = parse_hex(
                client_sorted[
                    index + 1
                ][
                    "client_offset"
                ]
            )
        else:
            next_client[offset] = None

    next_server = {}

    for index, row in enumerate(
        server_sorted
    ):
        offset = parse_hex(
            row["server_offset"]
        )

        if index + 1 < len(
            server_sorted
        ):
            next_server[offset] = parse_hex(
                server_sorted[
                    index + 1
                ][
                    "server_offset"
                ]
            )
        else:
            next_server[offset] = None

    results = []

    print("=" * 110)
    print(
        " FM06 BRASIL 2026 - "
        "CLIENT x SERVER CLUB PAYLOAD"
    )
    print("=" * 110)

    for row in mappings:

        name = row["short_name"]

        client_offset = parse_hex(
            row["client_offset"]
        )

        server_offset = parse_hex(
            row["server_offset"]
        )

        client_tokens = scan_record(
            client,
            client_offset,
            next_client[
                client_offset
            ],
        )

        server_tokens = scan_record(
            server,
            server_offset,
            next_server[
                server_offset
            ],
        )

        client_counter = Counter(
            token.text
            for token in client_tokens
        )

        server_counter = Counter(
            token.text
            for token in server_tokens
        )

        shared = (
            client_counter
            & server_counter
        )

        server_only = (
            server_counter
            - client_counter
        )

        client_only = (
            client_counter
            - server_counter
        )

        result = {
            "club": name,
            "client_strings":
                format_counter(
                    client_counter
                ),
            "server_strings":
                format_counter(
                    server_counter
                ),
            "shared":
                format_counter(
                    shared
                ),
            "server_only":
                format_counter(
                    server_only
                ),
            "client_only":
                format_counter(
                    client_only
                ),
        }

        results.append(
            result
        )

        print()
        print(name)
        print("-" * len(name))

        print(
            "CLIENT :",
            result[
                "client_strings"
            ],
        )

        print(
            "SERVER+ :",
            result[
                "server_only"
            ] or "(nenhum)",
        )

        if result[
            "client_only"
        ]:
            print(
                "CLIENT+:",
                result[
                    "client_only"
                ],
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
    print("=" * 110)
    print("CSV:")
    print(OUTPUT)


if __name__ == "__main__":
    main()