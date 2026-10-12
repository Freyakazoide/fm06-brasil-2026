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

from fm06patch.player_history import (
    HISTORY_RECORD_SIZE,
    PlayerHistoryDatabase,
)


CONFIG = (
    ROOT
    / "config"
    / "local.json"
)


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


def indexed_hex(
    data: bytes,
) -> str:

    return " ".join(
        f"{index:02X}:{value:02X}"
        for index, value
        in enumerate(data)
    )


def u16_candidates(
    data: bytes,
):

    result = []

    for offset in range(
        0,
        len(data) - 1,
    ):

        value = struct.unpack_from(
            "<H",
            data,
            offset,
        )[0]

        result.append(
            (
                offset,
                value,
            )
        )

    return result


def main():

    parser = (
        argparse.ArgumentParser()
    )

    parser.add_argument(
        "player_uid",
        type=int,
    )

    parser.add_argument(
        "--known-club-id",
        type=int,
        action="append",
        default=[],
    )

    args = parser.parse_args()

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

    db = PlayerHistoryDatabase(
        index_data=(
            db_dir
            / "pl_hist_index.dat"
        ).read_bytes(),

        spans_data=(
            db_dir
            / "pl_hist_id.dat"
        ).read_bytes(),

        history_data=(
            db_dir
            / "pl_hist_dt.dat"
        ).read_bytes(),
    )

    entries = (
        db.entries_for_uid(
            args.player_uid
        )
    )

    print("=" * 110)
    print(
        " FM06 BRASIL 2026 - "
        "PLAYER HISTORY"
    )
    print("=" * 110)

    print()
    print(
        f"Player UID : "
        f"{args.player_uid}"
    )

    if not entries:

        print(
            "Não encontrado no "
            "pl_hist_index.dat."
        )

        return

    print(
        f"Index entries: "
        f"{len(entries)}"
    )

    total_records = 0

    for entry_number, entry in enumerate(
        entries,
        start=1,
    ):

        span = db.span(
            entry.history_slot
        )

        records = (
            db.records_for_entry(
                entry
            )
        )

        total_records += len(
            records
        )

        print()
        print("=" * 110)

        print(
            f"ENTRY #{entry_number}"
        )

        print("=" * 110)

        print(
            f"index ordinal : "
            f"{entry.ordinal}"
        )

        print(
            f"index offset  : "
            f"{entry.file_offset_hex}"
        )

        print(
            f"history slot  : "
            f"{entry.history_slot}"
        )

        print(
            f"start relative: "
            f"{span.start_relative}"
            f" "
            f"(0x{span.start_relative:X})"
        )

        print(
            f"end relative  : "
            f"{span.end_relative}"
            f" "
            f"(0x{span.end_relative:X})"
        )

        print(
            f"records       : "
            f"{span.record_count}"
        )

        print()

        for record_number, record in (
            enumerate(
                records,
                start=1,
            )
        ):

            print("-" * 110)

            print(
                f"[{record_number}] "
                f"sequence="
                f"{record.sequence} "
                f"file="
                f"{record.file_offset_hex}"
            )

            print(
                indexed_hex(
                    record.data
                )
            )

            first_u16 = (
                struct.unpack_from(
                    "<H",
                    record.data,
                    0,
                )[0]
            )

            print(
                f"  u16@00 = "
                f"{first_u16}"
            )

            # --------------------------------------
            # CLUB IDs CONHECIDOS
            # --------------------------------------

            for club_id in (
                args.known_club_id
            ):

                matches = []

                if (
                    0
                    <= club_id
                    <= 0xFFFF
                ):

                    needle16 = (
                        struct.pack(
                            "<H",
                            club_id,
                        )
                    )

                    for relative in find_all(
                        record.data,
                        needle16,
                    ):

                        matches.append(
                            (
                                "u16",
                                relative,
                            )
                        )

                needle32 = (
                    struct.pack(
                        "<I",
                        club_id,
                    )
                )

                for relative in find_all(
                    record.data,
                    needle32,
                ):

                    matches.append(
                        (
                            "u32",
                            relative,
                        )
                    )

                if matches:

                    print(
                        f"  CLUB UID "
                        f"{club_id}:"
                    )

                    for (
                        kind,
                        relative,
                    ) in matches:

                        print(
                            f"    "
                            f"{kind} "
                            f"+0x"
                            f"{relative:X}"
                        )

            # --------------------------------------
            # POSSÍVEIS ANOS
            # --------------------------------------

            years = [
                (
                    offset,
                    value,
                )
                for (
                    offset,
                    value,
                ) in u16_candidates(
                    record.data
                )
                if (
                    1900
                    <= value
                    <= 2030
                )
            ]

            if years:

                print(
                    "  anos candidatos:"
                )

                print(
                    "    "
                    + ", ".join(
                        f"+0x{offset:X}"
                        f"={value}"
                        for (
                            offset,
                            value,
                        )
                        in years
                    )
                )

    print()
    print("=" * 110)

    print(
        f"Total de registros: "
        f"{total_records}"
    )

    print(
        f"Tamanho de cada "
        f"registro: "
        f"{HISTORY_RECORD_SIZE} bytes"
    )


if __name__ == "__main__":
    main()