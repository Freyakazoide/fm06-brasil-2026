from __future__ import annotations

import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

CONFIG = (
    ROOT
    / "config"
    / "local.json"
)


FIRST = "Sávio"
LAST = "Bortolini Pimentel"


def token(
    text: str,
) -> bytes:

    raw = text.encode(
        "utf-16le"
    )

    length = (
        len(raw) // 2
    )

    return (
        struct.pack(
            "<I",
            length,
        )
        + raw
        + b"\x00\x00"
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

        cursor = (
            pos + 1
        )

    return positions


def scan_strings(
    data: bytes,
    start: int,
    end: int,
):

    strings = []

    pos = max(
        0,
        start,
    )

    end = min(
        len(data),
        end,
    )

    while pos + 8 <= end:

        length = struct.unpack_from(
            "<I",
            data,
            pos,
        )[0]

        if not (
            1 <= length <= 100
        ):
            pos += 1
            continue

        text_start = (
            pos + 4
        )

        text_end = (
            text_start
            + length * 2
        )

        if (
            text_end + 2
            > end
        ):
            pos += 1
            continue

        if data[
            text_end:text_end + 2
        ] != b"\x00\x00":
            pos += 1
            continue

        try:
            text = data[
                text_start:text_end
            ].decode(
                "utf-16le"
            )
        except UnicodeDecodeError:
            pos += 1
            continue

        if (
            text
            and any(
                char.isalpha()
                for char in text
            )
            and all(
                char.isprintable()
                for char in text
            )
        ):
            strings.append(
                (
                    pos,
                    text,
                )
            )

            pos = (
                text_end + 2
            )
        else:
            pos += 1

    return strings


def main():

    with CONFIG.open(
        "r",
        encoding="utf-8",
    ) as file:
        config = json.load(file)

    game_dir = Path(
        config["game_dir"]
    )

    people_path = (
        game_dir
        / "data"
        / "db"
        / "people_db.dat"
    )

    data = (
        people_path.read_bytes()
    )

    first_token = token(
        FIRST
    )

    last_token = token(
        LAST
    )

    first_positions = find_all(
        data,
        first_token,
    )

    last_positions = find_all(
        data,
        last_token,
    )

    print("=" * 90)
    print(
        " FM06 BRASIL 2026 - "
        "PEOPLE LINK PROBE"
    )
    print("=" * 90)

    print()
    print(
        f"{FIRST!r}: "
        f"{len(first_positions)} "
        "ocorrência(s)"
    )

    print(
        f"{LAST!r}: "
        f"{len(last_positions)} "
        "ocorrência(s)"
    )

    print()
    print(
        "Pares próximos:"
    )

    candidates = []

    for first_pos in (
        first_positions
    ):

        for last_pos in (
            last_positions
        ):

            distance = (
                last_pos
                - first_pos
            )

            if (
                0 < distance < 256
            ):
                candidates.append(
                    (
                        first_pos,
                        last_pos,
                        distance,
                    )
                )

    if not candidates:
        print(
            "  nenhum"
        )
        return

    for index, (
        first_pos,
        last_pos,
        distance,
    ) in enumerate(
        candidates,
        start=1,
    ):

        print()
        print(
            f"[{index}]"
        )

        print(
            f"first prefix : "
            f"0x{first_pos:08X}"
        )

        print(
            f"last prefix  : "
            f"0x{last_pos:08X}"
        )

        print(
            f"distância    : "
            f"0x{distance:X}"
        )

        start = max(
            0,
            first_pos - 128,
        )

        end = min(
            len(data),
            last_pos + 256,
        )

        strings = scan_strings(
            data,
            start,
            end,
        )

        print(
            "strings próximas:"
        )

        for (
            offset,
            text,
        ) in strings:

            print(
                f"  "
                f"0x{offset:08X} "
                f"{text!r}"
            )

        print()
        print(
            "u32 anteriores ao "
            "primeiro nome:"
        )

        for relative in range(
            -32,
            0,
            4,
        ):

            pos = (
                first_pos
                + relative
            )

            if pos < 0:
                continue

            value = struct.unpack_from(
                "<I",
                data,
                pos,
            )[0]

            print(
                f"  "
                f"{relative:+04d} "
                f"0x{pos:08X} "
                f"{value}"
            )


if __name__ == "__main__":
    main()