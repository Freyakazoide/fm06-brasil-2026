from __future__ import annotations

import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "local.json"

INDEX_HEADER = 13
ID_HEADER = 13
DT_HEADER = 9
DT_RECORD_SIZE = 17

ANCHORS = [
    ("Sávio", 104318),
    ("Fred", 321081),
    ("Rogério Ceni", 3300977),
]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def monotonic_ratio(values):
    if len(values) < 2:
        return 1.0

    ok = sum(
        1
        for a, b in zip(values, values[1:])
        if b >= a
    )

    return ok / (len(values) - 1)


def main():

    with CONFIG.open("r", encoding="utf-8") as f:
        config = json.load(f)

    db_dir = (
        Path(config["game_dir"])
        / "data"
        / "db"
    )

    index_data = (
        db_dir
        / "pl_hist_index.dat"
    ).read_bytes()

    id_data = (
        db_dir
        / "pl_hist_id.dat"
    ).read_bytes()

    dt_data = (
        db_dir
        / "pl_hist_dt.dat"
    ).read_bytes()

    if (
        len(index_data) - INDEX_HEADER
    ) % 8:
        raise RuntimeError(
            "pl_hist_index framing inesperado"
        )

    pairs = []

    for offset in range(
        INDEX_HEADER,
        len(index_data),
        8,
    ):
        pairs.append(
            (
                u32(index_data, offset),
                u32(index_data, offset + 4),
                offset,
            )
        )

    col_a = [
        pair[0]
        for pair in pairs
    ]

    col_b = [
        pair[1]
        for pair in pairs
    ]

    id_values = [
        u32(id_data, offset)
        for offset in range(
            ID_HEADER,
            len(id_data),
            4,
        )
    ]

    print("=" * 110)
    print(
        " FM06 BRASIL 2026 - "
        "PLAYER HISTORY INDEX STRUCTURE"
    )
    print("=" * 110)

    print()
    print("pl_hist_index")
    print(f"  entries      : {len(pairs)}")
    print(
        f"  coluna A     : "
        f"min={min(col_a)} "
        f"max={max(col_a)} "
        f"unique={len(set(col_a))} "
        f"mono={monotonic_ratio(col_a):.6f}"
    )
    print(
        f"  coluna B     : "
        f"min={min(col_b)} "
        f"max={max(col_b)} "
        f"unique={len(set(col_b))} "
        f"mono={monotonic_ratio(col_b):.6f}"
    )

    print()
    print("pl_hist_id")
    print(
        f"  entries      : "
        f"{len(id_values)}"
    )
    print(
        f"  mono         : "
        f"{monotonic_ratio(id_values):.6f}"
    )
    print(
        f"  múltiplos 17 : "
        f"{sum(v % 17 == 0 for v in id_values)}"
        f"/{len(id_values)}"
    )
    print(
        f"  min/max      : "
        f"{min(id_values)} / "
        f"{max(id_values)}"
    )

    print()
    print("pl_hist_dt")
    print(
        f"  size         : "
        f"{len(dt_data)}"
    )
    print(
        f"  payload      : "
        f"{len(dt_data)-DT_HEADER}"
    )
    print(
        f"  payload / 17 : "
        f"{(len(dt_data)-DT_HEADER)/17}"
    )
    print(
        f"  resto        : "
        f"{(len(dt_data)-DT_HEADER)%17}"
    )

    print()
    print("=" * 110)
    print(" ÂNCORAS")
    print("=" * 110)

    for name, uid in ANCHORS:

        print()
        print(
            f"{name} "
            f"(UID {uid})"
        )

        matches = []

        for ordinal, (
            a,
            b,
            offset,
        ) in enumerate(pairs):

            if a == uid:
                matches.append(
                    (
                        ordinal,
                        "A",
                        b,
                        offset,
                    )
                )

            if b == uid:
                matches.append(
                    (
                        ordinal,
                        "B",
                        a,
                        offset + 4,
                    )
                )

        if not matches:
            print("  nenhum")
            continue

        for (
            ordinal,
            column,
            other,
            hit_offset,
        ) in matches:

            print()
            print(
                f"  ordinal={ordinal}"
            )
            print(
                f"  coluna={column}"
            )
            print(
                f"  hit=0x{hit_offset:08X}"
            )
            print(
                f"  outro valor={other}"
            )

            if column == "A":
                print(
                    f"  outro cabe em "
                    f"pl_hist_id? "
                    f"{0 <= other < len(id_values)}"
                )

            print("  vizinhança:")

            start = max(
                0,
                ordinal - 3,
            )

            end = min(
                len(pairs),
                ordinal + 4,
            )

            for i in range(
                start,
                end,
            ):
                a, b, off = pairs[i]

                marker = (
                    " <--"
                    if i == ordinal
                    else ""
                )

                print(
                    f"    "
                    f"{i:6d} "
                    f"0x{off:08X} "
                    f"A={a:<10} "
                    f"B={b:<10}"
                    f"{marker}"
                )


if __name__ == "__main__":
    main()