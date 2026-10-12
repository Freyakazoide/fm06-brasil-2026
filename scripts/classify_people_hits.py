from __future__ import annotations

import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "local.json"


ANCHORS = [
    {
        "name": "Sávio",
        "uid": 104318,
        "dob": (1974, 1, 9),
        "clubs": {
            1749: "Zaragoza/current",
            322: "Flamengo/preferred",
            1736: "Real Madrid/preferred",
        },
    },
    {
        "name": "Fred",
        "uid": 321081,
        "clubs": {
            865: "Lyon/current",
            321: "Cruzeiro/server-link",
        },
    },
    {
        "name": "Rogério Ceni",
        "uid": 3300977,
        "clubs": {
            337: "São Paulo/current+server-link",
        },
    },
]


def find_all(
    data: bytes,
    needle: bytes,
):
    hits = []
    pos = 0

    while True:
        pos = data.find(
            needle,
            pos,
        )

        if pos == -1:
            break

        hits.append(pos)
        pos += 1

    return hits


def search_value(
    data: bytes,
    center: int,
    value: int,
    radius: int = 512,
):
    start = max(
        0,
        center - radius,
    )

    end = min(
        len(data),
        center + radius,
    )

    block = data[start:end]

    results = []

    if 0 <= value <= 0xFFFF:
        needle = struct.pack(
            "<H",
            value,
        )

        for pos in find_all(
            block,
            needle,
        ):
            results.append(
                (
                    "u16",
                    start + pos - center,
                )
            )

    needle = struct.pack(
        "<I",
        value,
    )

    for pos in find_all(
        block,
        needle,
    ):
        results.append(
            (
                "u32",
                start + pos - center,
            )
        )

    return results


def search_dob(
    data: bytes,
    center: int,
    dob,
    radius: int = 512,
):
    year, month, day = dob

    patterns = {
        "year-month-day":
            struct.pack(
                "<HBB",
                year,
                month,
                day,
            ),

        "year-day-month":
            struct.pack(
                "<HBB",
                year,
                day,
                month,
            ),

        "day-month-year":
            struct.pack(
                "<BBH",
                day,
                month,
                year,
            ),

        "month-day-year":
            struct.pack(
                "<BBH",
                month,
                day,
                year,
            ),
    }

    start = max(
        0,
        center - radius,
    )

    end = min(
        len(data),
        center + radius,
    )

    block = data[start:end]

    result = []

    for name, pattern in (
        patterns.items()
    ):
        for pos in find_all(
            block,
            pattern,
        ):
            result.append(
                (
                    name,
                    start + pos - center,
                )
            )

    return result


def metrics(
    data: bytes,
    center: int,
    radius: int = 96,
):
    block = data[
        max(0, center-radius):
        min(len(data), center+radius)
    ]

    length = len(block)

    return (
        sum(
            1
            for value in block
            if 1 <= value <= 20
        ) / length,

        block.count(0) / length,

        block.count(255) / length,
    )


def main():

    with CONFIG.open(
        "r",
        encoding="utf-8",
    ) as f:
        config = json.load(f)

    people = (
        Path(config["game_dir"])
        / "data"
        / "db"
        / "people_db.dat"
    ).read_bytes()

    print("=" * 115)
    print(
        " FM06 BRASIL 2026 - "
        "PEOPLE HIT CLASSIFIER"
    )
    print("=" * 115)

    for anchor in ANCHORS:

        uid = anchor["uid"]

        hits = find_all(
            people,
            struct.pack(
                "<I",
                uid,
            ),
        )

        print()
        print(
            f"{anchor['name']} "
            f"(UID {uid})"
        )
        print("-" * 100)

        ranked = []

        for hit in hits:

            references = []

            for club_uid, label in (
                anchor["clubs"].items()
            ):

                matches = search_value(
                    people,
                    hit,
                    club_uid,
                )

                for encoding, relative in (
                    matches
                ):
                    references.append(
                        (
                            club_uid,
                            label,
                            encoding,
                            relative,
                        )
                    )

            dates = []

            if "dob" in anchor:
                dates = search_dob(
                    people,
                    hit,
                    anchor["dob"],
                )

            small, zero, ff = metrics(
                people,
                hit,
            )

            score = (
                len(references) * 100
                + len(dates) * 50
                + small
            )

            ranked.append(
                (
                    score,
                    hit,
                    references,
                    dates,
                    small,
                    zero,
                    ff,
                )
            )

        ranked.sort(
            reverse=True,
            key=lambda item:
                item[0],
        )

        for (
            score,
            hit,
            references,
            dates,
            small,
            zero,
            ff,
        ) in ranked:

            print()
            print(
                f"0x{hit:08X} "
                f"mod4={hit % 4} "
                f"small={small:.3f} "
                f"zero={zero:.3f} "
                f"ff={ff:.3f}"
            )

            if references:

                print(
                    "  CLUB REFERENCES:"
                )

                for (
                    club_uid,
                    label,
                    encoding,
                    relative,
                ) in references:

                    print(
                        f"    "
                        f"{relative:+5} "
                        f"{encoding:<3} "
                        f"{club_uid:<5} "
                        f"{label}"
                    )

            if dates:

                print(
                    "  DOB:"
                )

                for (
                    pattern,
                    relative,
                ) in dates:

                    print(
                        f"    "
                        f"{relative:+5} "
                        f"{pattern}"
                    )


if __name__ == "__main__":
    main()