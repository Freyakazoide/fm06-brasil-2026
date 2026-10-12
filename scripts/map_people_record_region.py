from __future__ import annotations

import json
import struct
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

CONFIG = (
    ROOT
    / "config"
    / "local.json"
)

OUTPUT = (
    ROOT
    / "workspace"
    / "dumps"
    / "people_record_region.json"
)


REGION_START = 0x03D00000
REGION_END = 0x03D40000


ANCHORS = [
    {
        "name": "Sávio",
        "uid": 104318,
    },
    {
        "name": "Fred",
        "uid": 321081,
    },
    {
        "name": "Rogério Ceni",
        "uid": 3300977,
    },
]


def u16(
    data: bytes,
    offset: int,
) -> int:

    return struct.unpack_from(
        "<H",
        data,
        offset,
    )[0]


def u32(
    data: bytes,
    offset: int,
) -> int:

    return struct.unpack_from(
        "<I",
        data,
        offset,
    )[0]


def find_all(
    data: bytes,
    needle: bytes,
    start: int = 0,
    end: int | None = None,
):
    if end is None:
        end = len(data)

    result = []

    cursor = start

    while True:

        pos = data.find(
            needle,
            cursor,
            end,
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


def load_history_uids(
    index_data: bytes,
):
    """
    pl_hist_index.dat:

        +0x0D
        uint32 uid
        uint32 history_slot
    """

    values = []

    for offset in range(
        13,
        len(index_data),
        8,
    ):

        values.append(
            u32(
                index_data,
                offset,
            )
        )

    return (
        set(values),
        Counter(values),
    )


def looks_like_person_record(
    data: bytes,
    uid_offset: int,
    valid_uids: set[int],
) -> bool:
    """
    Assinatura descoberta nos três jogadores.

    Ainda NÃO estamos atribuindo semântica
    aos campos.

    candidate_start = uid_offset - 19

    candidate_start +0:
        u32 valor pequeno/plausível

    candidate_start +4:
        u32 == 255

    candidate_start +19:
        u32 UID

    Também observamos byte UID+8 == 1
    nos três jogadores conhecidos.
    """

    if (
        uid_offset < 19
        or uid_offset + 9
        >= len(data)
    ):
        return False

    uid = u32(
        data,
        uid_offset,
    )

    if uid not in valid_uids:
        return False

    candidate_start = (
        uid_offset - 19
    )

    field_0 = u32(
        data,
        candidate_start,
    )

    marker_255 = u32(
        data,
        candidate_start + 4,
    )

    flag_after_uid = data[
        uid_offset + 8
    ]

    # O primeiro campo precisa parecer
    # um UID/referência pequena.
    if not (
        1 <= field_0 <= 10000
    ):
        return False

    # Esse valor foi idêntico nos três
    # jogadores que conhecemos.
    if marker_255 != 255:
        return False

    # Também foi idêntico nas três âncoras.
    # Mantemos como parte da assinatura,
    # ainda sem nomear sua função.
    if flag_after_uid != 1:
        return False

    return True


def scan_person_records(
    data: bytes,
    start: int,
    end: int,
    valid_uids: set[int],
):
    result = []

    start = max(
        19,
        start,
    )

    end = min(
        len(data) - 9,
        end,
    )

    for uid_offset in range(
        start,
        end,
    ):

        if not looks_like_person_record(
            data,
            uid_offset,
            valid_uids,
        ):
            continue

        uid = u32(
            data,
            uid_offset,
        )

        candidate_start = (
            uid_offset - 19
        )

        result.append(
            {
                "start":
                    candidate_start,

                "uid_offset":
                    uid_offset,

                "uid":
                    uid,

                "field_0":
                    u32(
                        data,
                        candidate_start,
                    ),

                "marker_255":
                    u32(
                        data,
                        candidate_start + 4,
                    ),

                "flag_after_uid":
                    data[
                        uid_offset + 8
                    ],
            }
        )

    return result


def dump_anchor_fields(
    data: bytes,
    uid_offset: int,
):
    """
    Mostra os campos ao redor da assinatura
    sem atribuir semântica ainda.
    """

    start = (
        uid_offset - 19
    )

    return {
        "candidate_start":
            start,

        "candidate_start_hex":
            f"0x{start:08X}",

        "field_start_u32":
            u32(
                data,
                start,
            ),

        "field_start_plus4_u32":
            u32(
                data,
                start + 4,
            ),

        "field_minus11_u16":
            u16(
                data,
                uid_offset - 11,
            ),

        "field_minus9_u16":
            u16(
                data,
                uid_offset - 9,
            ),

        "field_minus7_u32":
            u32(
                data,
                uid_offset - 7,
            ),

        "field_minus4_u32":
            u32(
                data,
                uid_offset - 4,
            ),

        "uid":
            u32(
                data,
                uid_offset,
            ),

        "plus4_u32":
            u32(
                data,
                uid_offset + 4,
            ),

        "plus8_u8":
            data[
                uid_offset + 8
            ],

        "plus9_u16":
            u16(
                data,
                uid_offset + 9,
            ),

        "plus11_u16":
            u16(
                data,
                uid_offset + 11,
            ),

        "plus13_u16":
            u16(
                data,
                uid_offset + 13,
            ),

        "plus15_u16":
            u16(
                data,
                uid_offset + 15,
            ),

        "plus17_u16":
            u16(
                data,
                uid_offset + 17,
            ),
    }


def hex_dump(
    data: bytes,
    center: int,
    before: int = 32,
    after: int = 96,
):
    lines = []

    start = max(
        0,
        center - before,
    )

    end = min(
        len(data),
        center + after,
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

        lines.append(
            {
                "offset":
                    offset,

                "relative":
                    offset - center,

                "hex":
                    " ".join(
                        f"{value:02X}"
                        for value in chunk
                    ),
            }
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

    db_dir = (
        Path(
            config["game_dir"]
        )
        / "data"
        / "db"
    )

    people = (
        db_dir
        / "people_db.dat"
    ).read_bytes()

    hist_index = (
        db_dir
        / "pl_hist_index.dat"
    ).read_bytes()

    valid_uids, uid_counts = (
        load_history_uids(
            hist_index
        )
    )

    records = scan_person_records(
        people,
        REGION_START,
        REGION_END,
        valid_uids,
    )

    print("=" * 120)
    print(
        " FM06 BRASIL 2026 - "
        "PEOPLE RECORD SIGNATURE"
    )
    print("=" * 120)

    print()
    print(
        f"UIDs no histórico : "
        f"{len(valid_uids):,}"
    )

    print(
        f"Registros com assinatura "
        f"na região: "
        f"{len(records):,}"
    )

    print()

    output = {
        "region": {
            "start":
                REGION_START,

            "end":
                REGION_END,

            "record_count":
                len(records),
        },

        "anchors": {},
    }

    for anchor in ANCHORS:

        name = anchor[
            "name"
        ]

        uid = anchor[
            "uid"
        ]

        raw_hits = find_all(
            people,
            struct.pack(
                "<I",
                uid,
            ),
            REGION_START,
            REGION_END,
        )

        hits = [
            offset
            for offset in raw_hits
            if looks_like_person_record(
                people,
                offset,
                valid_uids,
            )
        ]

        print("=" * 120)

        print(
            f"{name} "
            f"(UID {uid})"
        )

        print("=" * 120)

        print(
            f"raw hits      : "
            f"{len(raw_hits)}"
        )

        print(
            f"signature hits: "
            f"{len(hits)}"
        )

        if not hits:

            print(
                "Nenhum registro válido."
            )

            continue

        for uid_offset in hits:

            fields = dump_anchor_fields(
                people,
                uid_offset,
            )

            record_index = None

            for index, record in enumerate(
                records
            ):

                if (
                    record[
                        "uid_offset"
                    ]
                    == uid_offset
                ):
                    record_index = index
                    break

            print()
            print(
                f"UID offset     : "
                f"0x{uid_offset:08X}"
            )

            print(
                f"candidate start: "
                f"{fields['candidate_start_hex']}"
            )

            print()
            print(
                "CAMPOS ALINHADOS"
            )

            print("-" * 120)

            print(
                f"start +0   u32 = "
                f"{fields['field_start_u32']}"
            )

            print(
                f"start +4   u32 = "
                f"{fields['field_start_plus4_u32']}"
            )

            print(
                f"UID -11    u16 = "
                f"{fields['field_minus11_u16']}"
            )

            print(
                f"UID -9     u16 = "
                f"{fields['field_minus9_u16']}"
            )

            print(
                f"UID -7     u32 = "
                f"{fields['field_minus7_u32']}"
            )

            print(
                f"UID -4     u32 = "
                f"{fields['field_minus4_u32']}"
            )

            print(
                f"UID +0     u32 = "
                f"{fields['uid']}"
            )

            print(
                f"UID +4     u32 = "
                f"{fields['plus4_u32']}"
            )

            print(
                f"UID +8     u8  = "
                f"{fields['plus8_u8']}"
            )

            print(
                f"UID +9     u16 = "
                f"{fields['plus9_u16']}"
            )

            print(
                f"UID +11    u16 = "
                f"{fields['plus11_u16']}"
            )

            print(
                f"UID +13    u16 = "
                f"{fields['plus13_u16']}"
            )

            print(
                f"UID +15    u16 = "
                f"{fields['plus15_u16']}"
            )

            print(
                f"UID +17    u16 = "
                f"{fields['plus17_u16']}"
            )

            print()
            print(
                "REGISTROS COM A MESMA "
                "ASSINATURA AO REDOR"
            )

            print("-" * 120)

            previous_record = None
            next_record = None

            if record_index is not None:

                if record_index > 0:
                    previous_record = (
                        records[
                            record_index - 1
                        ]
                    )

                if (
                    record_index + 1
                    < len(records)
                ):
                    next_record = (
                        records[
                            record_index + 1
                        ]
                    )

            if previous_record:

                delta = (
                    previous_record[
                        "uid_offset"
                    ]
                    - uid_offset
                )

                print(
                    f"anterior: "
                    f"uid="
                    f"{previous_record['uid']} "
                    f"offset="
                    f"0x"
                    f"{previous_record['uid_offset']:08X} "
                    f"delta="
                    f"{delta:+d}"
                )

            else:

                print(
                    "anterior: -"
                )

            if next_record:

                delta = (
                    next_record[
                        "uid_offset"
                    ]
                    - uid_offset
                )

                print(
                    f"próximo : "
                    f"uid="
                    f"{next_record['uid']} "
                    f"offset="
                    f"0x"
                    f"{next_record['uid_offset']:08X} "
                    f"delta="
                    f"{delta:+d}"
                )

            else:

                print(
                    "próximo : -"
                )

            print()
            print(
                "HEX"
            )

            print("-" * 120)

            dump = hex_dump(
                people,
                uid_offset,
            )

            for line in dump:

                print(
                    f"{line['relative']:+5} "
                    f"0x"
                    f"{line['offset']:08X}  "
                    f"{line['hex']}"
                )

            output[
                "anchors"
            ][
                name
            ] = {
                "uid":
                    uid,

                "uid_offset":
                    uid_offset,

                "uid_offset_hex":
                    f"0x{uid_offset:08X}",

                "fields":
                    fields,

                "previous_record":
                    previous_record,

                "next_record":
                    next_record,

                "hex":
                    dump,
            }

            print()

    print("=" * 120)
    print(
        " COMPARAÇÃO DAS ÂNCORAS"
    )
    print("=" * 120)
    print()

    field_names = [
        "field_start_u32",
        "field_start_plus4_u32",
        "field_minus11_u16",
        "field_minus9_u16",
        "field_minus7_u32",
        "field_minus4_u32",
        "plus4_u32",
        "plus8_u8",
        "plus9_u16",
        "plus11_u16",
        "plus13_u16",
        "plus15_u16",
        "plus17_u16",
    ]

    available = [
        anchor
        for anchor in ANCHORS
        if anchor["name"]
        in output["anchors"]
    ]

    print(
        f"{'FIELD':<26}"
        + "".join(
            f"{anchor['name']:>20}"
            for anchor in available
        )
    )

    print("-" * 120)

    for field_name in field_names:

        line = (
            f"{field_name:<26}"
        )

        for anchor in available:

            value = (
                output[
                    "anchors"
                ][
                    anchor["name"]
                ][
                    "fields"
                ][
                    field_name
                ]
            )

            line += (
                f"{value:>20}"
            )

        print(line)

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