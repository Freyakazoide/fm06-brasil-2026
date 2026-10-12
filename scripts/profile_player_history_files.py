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


FILES = [
    "pl_hist_id.dat",
    "pl_hist_index.dat",
    "pl_hist_dt.dat",
]


def u32_values(
    data: bytes,
    start: int,
    count: int,
):
    result = []

    pos = start

    while (
        pos + 4 <= len(data)
        and len(result) < count
    ):

        result.append(
            struct.unpack_from(
                "<I",
                data,
                pos,
            )[0]
        )

        pos += 4

    return result


def score_alignment(
    data: bytes,
    start: int,
    sample_count: int = 50000,
):

    values = u32_values(
        data,
        start,
        sample_count,
    )

    if not values:
        return None

    small = sum(
        1
        for value in values
        if (
            0
            <= value
            <= 10_000_000
        )
    )

    zeros = values.count(
        0
    )

    monotonic = sum(
        1
        for a, b in zip(
            values,
            values[1:],
        )
        if b >= a
    )

    return {
        "start":
            start,

        "count":
            len(values),

        "small_ratio":
            small
            / len(values),

        "zero_ratio":
            zeros
            / len(values),

        "monotonic_ratio":
            monotonic
            / max(
                1,
                len(values) - 1,
            ),

        "unique":
            len(
                set(values)
            ),

        "minimum":
            min(values),

        "maximum":
            max(values),

        "first_values":
            values[:20],
    }


def main():

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

    print("=" * 100)
    print(
        " FM06 BRASIL 2026 - "
        "PLAYER HISTORY FILE PROFILER"
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

        print()
        print(filename)
        print("-" * len(filename))

        print(
            f"size: "
            f"{len(data):,}"
        )

        print(
            "first 32 bytes:"
        )

        print(
            " ".join(
                f"{byte:02X}"
                for byte
                in data[:32]
            )
        )

        candidates = []

        for start in range(
            0,
            17,
        ):

            score = score_alignment(
                data,
                start,
            )

            if score is not None:
                candidates.append(
                    score
                )

        candidates.sort(
            key=lambda item: (
                -item[
                    "small_ratio"
                ],
                -item[
                    "monotonic_ratio"
                ],
                item[
                    "zero_ratio"
                ],
            )
        )

        print()
        print(
            "melhores alinhamentos u32:"
        )

        for item in candidates[:5]:

            print(
                f"  start={item['start']:>2}  "
                f"small={item['small_ratio']:.3f}  "
                f"zero={item['zero_ratio']:.3f}  "
                f"mono={item['monotonic_ratio']:.3f}  "
                f"unique={item['unique']}  "
                f"min={item['minimum']}  "
                f"max={item['maximum']}"
            )

            print(
                "     ",
                item[
                    "first_values"
                ],
            )


if __name__ == "__main__":
    main()