from __future__ import annotations

import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "local.json"

RADIUS = 4096


PLAYERS = [
    {
        "name": "Sávio",
        "uid": 104318,
        "start": (2003, 7, 1),
        "end": (2007, 6, 30),
        "club_uid": 1749,
    },
    {
        "name": "Zinedine Zidane",
        "uid": 8076,
        "start": (2004, 3, 1),
        "end": (2007, 6, 30),
        "club_uid": 1736,
    },
    {
        "name": "Rogério Ceni",
        "uid": 3300977,
        "start": (2004, 3, 1),
        "end": (2008, 7, 31),
        "club_uid": 337,
    },
]


FILES = [
    "people_db.dat",
    "server_db.dat",
    "client_db.dat",
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


def date_patterns(
    year: int,
    month: int,
    day: int,
):
    """
    Testamos representações comuns sem assumir
    ainda como o FM serializa Date.
    """

    return {
        # uint16 year + month + day
        "Y16-M-D":
            struct.pack(
                "<HBB",
                year,
                month,
                day,
            ),

        # uint16 year + day + month
        "Y16-D-M":
            struct.pack(
                "<HBB",
                year,
                day,
                month,
            ),

        # day + month + uint16 year
        "D-M-Y16":
            struct.pack(
                "<BBH",
                day,
                month,
                year,
            ),

        # month + day + uint16 year
        "M-D-Y16":
            struct.pack(
                "<BBH",
                month,
                day,
                year,
            ),

        # três uint32
        "Y32-M32-D32":
            struct.pack(
                "<III",
                year,
                month,
                day,
            ),

        "D32-M32-Y32":
            struct.pack(
                "<III",
                day,
                month,
                year,
            ),
    }


def search_patterns(
    data: bytes,
    start: int,
    end: int,
    center: int,
    patterns: dict[str, bytes],
):
    block = data[
        start:end
    ]

    result = []

    for name, pattern in (
        patterns.items()
    ):

        cursor = 0

        while True:

            pos = block.find(
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

                    "relative":
                        absolute
                        - center,
                }
            )

            cursor = pos + 1

    return result


def search_u32_near(
    data: bytes,
    start: int,
    end: int,
    center: int,
    value: int,
):
    needle = struct.pack(
        "<I",
        value,
    )

    block = data[
        start:end
    ]

    result = []

    cursor = 0

    while True:

        pos = block.find(
            needle,
            cursor,
        )

        if pos == -1:
            break

        absolute = (
            start + pos
        )

        result.append(
            absolute - center
        )

        cursor = pos + 1

    return result


def main():

    with CONFIG.open(
        "r",
        encoding="utf-8",
    ) as file:
        config = json.load(file)

    db_dir = (
        Path(config["game_dir"])
        / "data"
        / "db"
    )

    databases = {
        filename:
            (
                db_dir
                / filename
            ).read_bytes()
        for filename in FILES
    }

    print("=" * 120)
    print(
        " FM06 BRASIL 2026 - "
        "CONTRACT DATE TRACE"
    )
    print("=" * 120)

    for player in PLAYERS:

        uid = player["uid"]

        start_date = player[
            "start"
        ]

        end_date = player[
            "end"
        ]

        print()
        print("=" * 120)

        print(
            f"{player['name']} "
            f"(UID {uid})"
        )

        print(
            f"Início : "
            f"{start_date[2]:02d}/"
            f"{start_date[1]:02d}/"
            f"{start_date[0]}"
        )

        print(
            f"Expira : "
            f"{end_date[2]:02d}/"
            f"{end_date[1]:02d}/"
            f"{end_date[0]}"
        )

        print("=" * 120)

        uid_bytes = struct.pack(
            "<I",
            uid,
        )

        start_patterns = date_patterns(
            *start_date,
        )

        end_patterns = date_patterns(
            *end_date,
        )

        for db_name, data in (
            databases.items()
        ):

            uid_hits = find_all(
                data,
                uid_bytes,
            )

            interesting = []

            for uid_hit in uid_hits:

                region_start = max(
                    0,
                    uid_hit - RADIUS,
                )

                region_end = min(
                    len(data),
                    uid_hit + RADIUS,
                )

                starts = search_patterns(
                    data,
                    region_start,
                    region_end,
                    uid_hit,
                    start_patterns,
                )

                ends = search_patterns(
                    data,
                    region_start,
                    region_end,
                    uid_hit,
                    end_patterns,
                )

                clubs = search_u32_near(
                    data,
                    region_start,
                    region_end,
                    uid_hit,
                    player[
                        "club_uid"
                    ],
                )

                score = (
                    len(starts) * 100
                    + len(ends) * 100
                )

                # Clube sozinho vale pouco,
                # pois pode ser coincidência.
                if clubs:
                    score += 10

                if score:

                    interesting.append(
                        {
                            "uid_hit":
                                uid_hit,

                            "score":
                                score,

                            "starts":
                                starts,

                            "ends":
                                ends,

                            "clubs":
                                clubs,
                        }
                    )

            interesting.sort(
                key=lambda item: (
                    -item["score"],
                    item["uid_hit"],
                )
            )

            print()
            print(
                f"{db_name}: "
                f"{len(uid_hits)} UID hit(s), "
                f"{len(interesting)} candidato(s)"
            )

            for index, item in enumerate(
                interesting[:15],
                start=1,
            ):

                print()
                print(
                    f"  #{index} "
                    f"UID @ "
                    f"0x{item['uid_hit']:08X} "
                    f"score="
                    f"{item['score']}"
                )

                for date in item[
                    "starts"
                ]:

                    print(
                        f"       START "
                        f"{date['pattern']:<12} "
                        f"rel="
                        f"{date['relative']:+d}"
                    )

                for date in item[
                    "ends"
                ]:

                    print(
                        f"       END   "
                        f"{date['pattern']:<12} "
                        f"rel="
                        f"{date['relative']:+d}"
                    )

                if item[
                    "clubs"
                ]:

                    print(
                        "       CLUB UID rel="
                        + ", ".join(
                            f"{value:+d}"
                            for value
                            in item[
                                "clubs"
                            ][:10]
                        )
                    )


if __name__ == "__main__":
    main()