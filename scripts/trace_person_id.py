from __future__ import annotations

import argparse
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

OUTPUT_DIR = (
    ROOT
    / "workspace"
    / "dumps"
    / "people_traces"
)


FILES = [
    "server_db.dat",
    "client_db.dat",
    "people_db.dat",
    "lang_db.dat",
    "pl_hist_id.dat",
    "pl_hist_index.dat",
    "pl_hist_dt.dat",
]


def find_all(
    data: bytes,
    needle: bytes,
):
    positions = []

    cursor = 0

    while True:

        pos = data.find(
            needle,
            cursor,
        )

        if pos == -1:
            break

        positions.append(
            pos
        )

        cursor = pos + 1

    return positions


def person_id_bytes(
    person_id: int,
) -> bytes:

    return struct.pack(
        "<I",
        person_id,
    )


def string_token(
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


def hex_dump(
    data: bytes,
    start: int,
    end: int,
) -> list[str]:

    result = []

    start = max(
        0,
        start,
    )

    end = min(
        len(data),
        end,
    )

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

        hex_part = " ".join(
            f"{byte:02X}"
            for byte in chunk
        )

        result.append(
            f"{offset:08X}  "
            f"{hex_part}"
        )

    return result


def u32_context(
    data: bytes,
    center: int,
):

    result = []

    for relative in range(
        -48,
        52,
        4,
    ):

        offset = (
            center
            + relative
        )

        if (
            offset < 0
            or offset + 4
            > len(data)
        ):
            continue

        value = struct.unpack_from(
            "<I",
            data,
            offset,
        )[0]

        result.append(
            {
                "relative":
                    relative,

                "offset":
                    offset,

                "offset_hex":
                    f"0x{offset:08X}",

                "value":
                    value,

                "value_hex":
                    f"0x{value:08X}",
            }
        )

    return result


def date_patterns(
    year: int,
    month: int,
    day: int,
):
    return {
        "u16_year_month_day":
            struct.pack(
                "<HBB",
                year,
                month,
                day,
            ),

        "u16_year_day_month":
            struct.pack(
                "<HBB",
                year,
                day,
                month,
            ),

        "day_month_u16_year":
            struct.pack(
                "<BBH",
                day,
                month,
                year,
            ),

        "month_day_u16_year":
            struct.pack(
                "<BBH",
                month,
                day,
                year,
            ),

        "u32_year_month_day":
            struct.pack(
                "<III",
                year,
                month,
                day,
            ),

        "u32_day_month_year":
            struct.pack(
                "<III",
                day,
                month,
                year,
            ),
    }


def search_date_near(
    data: bytes,
    center: int,
    year: int,
    month: int,
    day: int,
    radius: int = 2048,
):

    start = max(
        0,
        center - radius,
    )

    end = min(
        len(data),
        center + radius,
    )

    segment = data[
        start:end
    ]

    result = []

    for (
        name,
        pattern,
    ) in date_patterns(
        year,
        month,
        day,
    ).items():

        cursor = 0

        while True:

            pos = segment.find(
                pattern,
                cursor,
            )

            if pos == -1:
                break

            absolute = (
                start + pos
            )

            result.append(
                {
                    "pattern":
                        name,

                    "offset":
                        absolute,

                    "offset_hex":
                        f"0x{absolute:08X}",

                    "relative":
                        absolute
                        - center,
                }
            )

            cursor = pos + 1

    return result


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "person_id",
        type=int,
    )

    parser.add_argument(
        "--first",
    )

    parser.add_argument(
        "--last",
    )

    parser.add_argument(
        "--dob",
        help="YYYY-MM-DD",
    )

    args = parser.parse_args()

    with CONFIG.open(
        "r",
        encoding="utf-8",
    ) as file:
        config = json.load(file)

    db_dir = (
        Path(
            config["game_dir"]
        )
        / "data"
        / "db"
    )

    pid_bytes = person_id_bytes(
        args.person_id
    )

    print("=" * 100)
    print(
        " FM06 BRASIL 2026 - "
        "PERSON ID TRACE"
    )
    print("=" * 100)

    print()
    print(
        f"Person ID : "
        f"{args.person_id}"
    )

    print(
        f"Hex       : "
        f"0x{args.person_id:08X}"
    )

    print(
        "Bytes LE  : "
        + " ".join(
            f"{byte:02X}"
            for byte in pid_bytes
        )
    )

    dob = None

    if args.dob:

        year, month, day = [
            int(part)
            for part
            in args.dob.split("-")
        ]

        dob = (
            year,
            month,
            day,
        )

    output = {
        "person_id":
            args.person_id,

        "person_id_hex":
            f"0x{args.person_id:08X}",

        "name":
            (
                f"{args.first or ''} "
                f"{args.last or ''}"
            ).strip(),

        "files":
            {},
    }

    file_data = {}

    print()
    print("=" * 100)
    print(
        " OCORRÊNCIAS DO ID"
    )
    print("=" * 100)

    for filename in FILES:

        path = (
            db_dir
            / filename
        )

        data = (
            path.read_bytes()
        )

        file_data[
            filename
        ] = data

        hits = find_all(
            data,
            pid_bytes,
        )

        output[
            "files"
        ][
            filename
        ] = {
            "hit_count":
                len(hits),

            "hits":
                [
                    {
                        "offset":
                            hit,

                        "offset_hex":
                            f"0x{hit:08X}",
                    }
                    for hit in hits
                ],
        }

        offsets = ", ".join(
            f"0x{hit:08X}"
            for hit in hits[:15]
        )

        if len(hits) > 15:
            offsets += " ..."

        print(
            f"{filename:<20} "
            f"{len(hits):>5}  "
            f"{offsets}"
        )

    # -------------------------------------------------
    # CORRELAÇÃO COM NOME NO SERVER_DB
    # -------------------------------------------------

    if (
        args.first
        and args.last
    ):

        server = file_data[
            "server_db.dat"
        ]

        pair = (
            string_token(
                args.first
            )
            + string_token(
                args.last
            )
        )

        name_hits = find_all(
            server,
            pair,
        )

        print()
        print("=" * 100)
        print(
            " NOME NO SERVER_DB "
            "x PERSON_ID"
        )
        print("=" * 100)

        output[
            "server_name_hits"
        ] = []

        for hit in name_hits:

            nearby_start = max(
                0,
                hit - 96,
            )

            nearby_end = min(
                len(server),
                hit + len(pair) + 96,
            )

            segment = server[
                nearby_start:
                nearby_end
            ]

            local_ids = find_all(
                segment,
                pid_bytes,
            )

            absolute_ids = [
                nearby_start + pos
                for pos in local_ids
            ]

            print()
            print(
                f"Nome em "
                f"0x{hit:08X}"
            )

            if absolute_ids:

                for id_offset in (
                    absolute_ids
                ):

                    print(
                        f"  ID em "
                        f"0x{id_offset:08X} "
                        f"relative="
                        f"{id_offset-hit:+d}"
                    )

            else:
                print(
                    "  nenhum ID próximo"
                )

            output[
                "server_name_hits"
            ].append(
                {
                    "name_offset":
                        hit,

                    "name_offset_hex":
                        f"0x{hit:08X}",

                    "person_id_offsets":
                        [
                            {
                                "offset":
                                    value,

                                "offset_hex":
                                    f"0x{value:08X}",

                                "relative":
                                    value - hit,
                            }
                            for value
                            in absolute_ids
                        ],
                }
            )

    # -------------------------------------------------
    # PEOPLE_DB CONTEXT
    # -------------------------------------------------

    people = file_data[
        "people_db.dat"
    ]

    people_hits = [
        item[
            "offset"
        ]
        for item in output[
            "files"
        ][
            "people_db.dat"
        ][
            "hits"
        ]
    ]

    print()
    print("=" * 100)
    print(
        " PEOPLE_DB - "
        "CANDIDATOS"
    )
    print("=" * 100)

    output[
        "people_candidates"
    ] = []

    if not people_hits:

        print(
            "Nenhuma ocorrência direta "
            "do person_id."
        )

    for index, hit in enumerate(
        people_hits[:12],
        start=1,
    ):

        print()
        print(
            f"[{index}] "
            f"0x{hit:08X}"
        )

        dates = []

        if dob is not None:

            dates = search_date_near(
                people,
                hit,
                *dob,
            )

            if dates:

                print(
                    "  padrões de DOB:"
                )

                for date in dates:

                    print(
                        f"    "
                        f"{date['pattern']:<22} "
                        f"{date['offset_hex']} "
                        f"relative="
                        f"{date['relative']:+d}"
                    )

            else:

                print(
                    "  DOB simples não "
                    "encontrado em ±2048"
                )

        numbers = u32_context(
            people,
            hit,
        )

        print(
            "  u32 alinhados em torno do ID:"
        )

        for item in numbers:

            if (
                item[
                    "relative"
                ] == 0
            ):
                marker = " <ID>"
            else:
                marker = ""

            print(
                f"    "
                f"{item['relative']:+4} "
                f"{item['value']:<12} "
                f"{item['value_hex']}"
                f"{marker}"
            )

        dump_start = max(
            0,
            hit - 64,
        )

        dump_end = min(
            len(people),
            hit + 128,
        )

        dump = hex_dump(
            people,
            dump_start,
            dump_end,
        )

        output[
            "people_candidates"
        ].append(
            {
                "offset":
                    hit,

                "offset_hex":
                    f"0x{hit:08X}",

                "dob_patterns":
                    dates,

                "u32":
                    numbers,

                "hex_dump":
                    dump,
            }
        )

    # -------------------------------------------------
    # HIST INDEX
    # -------------------------------------------------

    print()
    print("=" * 100)
    print(
        " PLAYER HISTORY"
    )
    print("=" * 100)

    for filename in [
        "pl_hist_id.dat",
        "pl_hist_index.dat",
        "pl_hist_dt.dat",
    ]:

        hits = output[
            "files"
        ][
            filename
        ][
            "hits"
        ]

        print(
            f"{filename:<20} "
            f"{len(hits)} hit(s)"
        )

        for item in hits[:15]:

            print(
                f"    "
                f"{item['offset_hex']}"
            )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIR
        / f"{args.person_id}.json"
    )

    with output_path.open(
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
    print(output_path)


if __name__ == "__main__":
    main()