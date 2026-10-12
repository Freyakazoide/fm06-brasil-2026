from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

sys.path.insert(
    0,
    str(ROOT / "src"),
)

sys.path.insert(
    0,
    str(SCRIPTS),
)


from fm06patch.people_db import PeopleDatabase

from live_player_memory import (
    find_process_id,
    open_process,
    scan_value,
    read_memory,
    kernel32,
)


CONFIG = ROOT / "config" / "local.json"


CA_REL = -204
PA_REL = -202

DUMP_START = -240
DUMP_END = -150


def u16(
    data: bytes,
    offset: int,
) -> int:

    return struct.unpack_from(
        "<H",
        data,
        offset,
    )[0]


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "player_uid",
        type=int,
    )

    parser.add_argument(
        "--name",
        default="",
    )

    args = parser.parse_args()

    with CONFIG.open(
        "r",
        encoding="utf-8",
    ) as file:
        config = json.load(file)

    db_path = (
        Path(config["game_dir"])
        / "data"
        / "db"
        / "people_db.dat"
    )

    db_data = db_path.read_bytes()

    people_db = PeopleDatabase(
        db_data
    )

    source = people_db.player(
        args.player_uid
    )

    pid = find_process_id(
        "fm.exe"
    )

    handle = open_process(
        pid
    )

    try:

        needle = struct.pack(
            "<I",
            args.player_uid,
        )

        hits = scan_value(
            handle,
            needle,
        )

        candidates = []

        for address in hits:

            start = (
                address - 300
            )

            block = read_memory(
                handle,
                start,
                600,
            )

            if (
                block is None
                or len(block) < 600
            ):
                continue

            uid_local = (
                address - start
            )

            ca_local = (
                uid_local
                + CA_REL
            )

            pa_local = (
                uid_local
                + PA_REL
            )

            if (
                ca_local < 0
                or pa_local < 0
                or pa_local + 2
                > len(block)
            ):
                continue

            live_ca = u16(
                block,
                ca_local,
            )

            live_pa = u16(
                block,
                pa_local,
            )

            score = 0

            if (
                1 <= live_ca <= 200
            ):
                score += 100

            if (
                1 <= live_pa <= 200
            ):
                score += 100

            ca_delta = abs(
                live_ca
                - source.current_ability
            )

            pa_delta = abs(
                live_pa
                - source.potential_ability
            )

            if ca_delta == 0:
                score += 500
            elif ca_delta <= 2:
                score += 300
            elif ca_delta <= 10:
                score += 100

            if pa_delta == 0:
                score += 500
            elif pa_delta <= 2:
                score += 300
            elif pa_delta <= 10:
                score += 100

            if (
                1 <= live_ca <= 200
                and
                1 <= live_pa <= 200
                and
                live_pa >= live_ca
            ):
                score += 50

            candidates.append(
                {
                    "address":
                        address,

                    "score":
                        score,

                    "live_ca":
                        live_ca,

                    "live_pa":
                        live_pa,

                    "ca_delta":
                        ca_delta,

                    "pa_delta":
                        pa_delta,

                    "block":
                        block,

                    "uid_local":
                        uid_local,
                }
            )

        candidates.sort(
            key=lambda item: (
                -item["score"],
                item["address"],
            )
        )

        print("=" * 100)
        print(
            " FM06 LIVE PLAYER LAYOUT"
        )
        print("=" * 100)

        print(
            f"Nome              : "
            f"{args.name or '-'}"
        )

        print(
            f"Player UID        : "
            f"{args.player_uid}"
        )

        print(
            f"people_db offset  : "
            f"0x{source.uid_offset:08X}"
        )

        print()
        print(
            "SOURCE DATABASE"
        )

        print(
            f"  CA              : "
            f"{source.current_ability}"
        )

        print(
            f"  PA              : "
            f"{source.potential_ability}"
        )

        print(
            f"  Rating #1       : "
            f"{source.reputation_1}"
        )

        print(
            f"  Rating #2       : "
            f"{source.reputation_2}"
        )

        print(
            f"  Rating #3       : "
            f"{source.reputation_3}"
        )

        print()
        print(
            f"RAM UID hits      : "
            f"{len(hits)}"
        )

        print()

        print(
            f"{'#':>3} "
            f"{'UID ADDRESS':>12} "
            f"{'SCORE':>6} "
            f"{'CA':>5} "
            f"{'ΔCA':>5} "
            f"{'PA':>5} "
            f"{'ΔPA':>5}"
        )

        print("-" * 60)

        for index, item in enumerate(
            candidates[:20],
            start=1,
        ):

            print(
                f"{index:>3} "
                f"0x{item['address']:08X} "
                f"{item['score']:>6} "
                f"{item['live_ca']:>5} "
                f"{item['ca_delta']:>5} "
                f"{item['live_pa']:>5} "
                f"{item['pa_delta']:>5}"
            )

        if not candidates:
            return

        best = candidates[0]

        print()
        print("=" * 100)
        print(
            " MELHOR CANDIDATO"
        )
        print("=" * 100)

        print(
            f"UID address : "
            f"0x{best['address']:08X}"
        )

        print(
            f"CA address  : "
            f"0x"
            f"{best['address'] + CA_REL:08X}"
            f"  rel={CA_REL:+d}"
        )

        print(
            f"PA address  : "
            f"0x"
            f"{best['address'] + PA_REL:08X}"
            f"  rel={PA_REL:+d}"
        )

        print(
            f"Live CA     : "
            f"{best['live_ca']}"
        )

        print(
            f"Live PA     : "
            f"{best['live_pa']}"
        )

        print()
        print(
            "U16 AO REDOR DO REGISTRO"
        )

        print(
            "relativo   endereço     "
            "u16   hex"
        )

        print("-" * 50)

        block = best[
            "block"
        ]

        uid_local = best[
            "uid_local"
        ]

        for relative in range(
            DUMP_START,
            DUMP_END + 1,
            2,
        ):

            local = (
                uid_local
                + relative
            )

            if (
                local < 0
                or local + 2
                > len(block)
            ):
                continue

            value = u16(
                block,
                local,
            )

            absolute = (
                best["address"]
                + relative
            )

            marker = ""

            if relative == CA_REL:
                marker = "<-- CA"

            elif relative == PA_REL:
                marker = "<-- PA"

            print(
                f"{relative:+8d} "
                f"0x{absolute:08X} "
                f"{value:5d} "
                f"{value:04X} "
                f"{marker}"
            )

    finally:

        kernel32.CloseHandle(
            handle
        )


if __name__ == "__main__":
    main()