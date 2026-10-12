from __future__ import annotations

import argparse
import json
import struct
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(
    0,
    str(ROOT / "src"),
)

from fm06patch.server_db import (
    parse_serialized_string,
)


CONFIG = (
    ROOT
    / "config"
    / "local.json"
)


# ============================================================
# HELPERS
# ============================================================

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

        result.append(
            pos
        )

        cursor = pos + 1

    return result


def valid_text(
    text: str,
) -> bool:

    if not text:
        return False

    if not any(
        char.isalpha()
        for char in text
    ):
        return False

    return all(
        char.isprintable()
        for char in text
    )


def serialized_token(
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


# ============================================================
# LANG RECORD
# ============================================================

@dataclass(frozen=True)
class LangClubCandidate:
    offset: int
    uid: int

    flag: int

    full_name: str
    short_name: str


def parse_lang_candidate(
    data: bytes,
    offset: int,
    expected_uid: int,
) -> LangClubCandidate | None:

    if (
        offset < 0
        or offset + 16
        > len(data)
    ):
        return None

    if u32(
        data,
        offset,
    ) != expected_uid:
        return None

    full_length = u32(
        data,
        offset + 4,
    )

    if not (
        1 <= full_length <= 100
    ):
        return None

    full_start = (
        offset + 8
    )

    full_end = (
        full_start
        + full_length * 2
    )

    if (
        full_end + 2
        >= len(data)
    ):
        return None

    if data[
        full_end:
        full_end + 2
    ] != b"\x00\x00":
        return None

    try:
        full_name = (
            data[
                full_start:
                full_end
            ].decode(
                "utf-16le"
            )
        )
    except UnicodeDecodeError:
        return None

    if not valid_text(
        full_name
    ):
        return None

    flag_offset = (
        full_end + 2
    )

    flag = data[
        flag_offset
    ]

    short_length_offset = (
        flag_offset + 1
    )

    if (
        short_length_offset + 4
        > len(data)
    ):
        return None

    short_length = u32(
        data,
        short_length_offset,
    )

    if not (
        1 <= short_length <= 100
    ):
        return None

    short_start = (
        short_length_offset + 4
    )

    short_end = (
        short_start
        + short_length * 2
    )

    if (
        short_end + 2
        > len(data)
    ):
        return None

    if data[
        short_end:
        short_end + 2
    ] != b"\x00\x00":
        return None

    try:
        short_name = (
            data[
                short_start:
                short_end
            ].decode(
                "utf-16le"
            )
        )
    except UnicodeDecodeError:
        return None

    if not valid_text(
        short_name
    ):
        return None

    return LangClubCandidate(
        offset=offset,
        uid=expected_uid,
        flag=flag,
        full_name=full_name,
        short_name=short_name,
    )


def find_lang_candidates(
    data: bytes,
    uid: int,
):
    needle = struct.pack(
        "<I",
        uid,
    )

    result = []

    seen = set()

    for offset in find_all(
        data,
        needle,
    ):

        candidate = (
            parse_lang_candidate(
                data,
                offset,
                uid,
            )
        )

        if candidate is None:
            continue

        key = (
            candidate.offset,
            candidate.full_name,
            candidate.short_name,
        )

        if key in seen:
            continue

        seen.add(key)

        result.append(
            candidate
        )

    return result


# ============================================================
# CLIENT / SERVER CONTAINER
# ============================================================

@dataclass(frozen=True)
class ClubContainerCandidate:
    source: str

    header_offset: int

    field_a: int
    field_b: int

    group_marker: int

    first_string: str

    full_name_rel: int
    short_name_rel: int


def plausible_header(
    data: bytes,
    offset: int,
):
    if (
        offset < 0
        or offset + 20
        > len(data)
    ):
        return None

    field_a = u32(
        data,
        offset,
    )

    field_b = u32(
        data,
        offset + 4,
    )

    zero_flag = data[
        offset + 8
    ]

    group_marker = u32(
        data,
        offset + 9,
    )

    if zero_flag != 0:
        return None

    if not (
        1 <= field_a <= 100_000_000
    ):
        return None

    if not (
        1 <= field_b <= 100_000_000
    ):
        return None

    if not (
        1 <= group_marker <= 100_000
    ):
        return None

    # Em todos os clubes que já reconstruímos,
    # a primeira string serializada começa
    # exatamente em header + 0x0E.
    first_string = (
        parse_serialized_string(
            data,
            offset + 0x0E,
            limit=min(
                len(data),
                offset + 0x400,
            ),
            max_chars=100,
        )
    )

    if first_string is None:
        return None

    return (
        field_a,
        field_b,
        group_marker,
        first_string.text,
    )


def find_containers(
    source: str,
    data: bytes,
    full_name: str,
    short_name: str,
):
    full_token = (
        serialized_token(
            full_name
        )
    )

    short_token = (
        serialized_token(
            short_name
        )
    )

    full_hits = find_all(
        data,
        full_token,
    )

    results = []

    seen_headers = set()

    for full_offset in (
        full_hits
    ):

        search_end = min(
            len(data),
            full_offset + 0x400,
        )

        short_offset = data.find(
            short_token,
            full_offset,
            search_end,
        )

        if short_offset == -1:
            continue

        backwards_start = max(
            0,
            full_offset - 0x400,
        )

        candidates = []

        for header_offset in range(
            backwards_start,
            full_offset + 1,
        ):

            header = plausible_header(
                data,
                header_offset,
            )

            if header is None:
                continue

            (
                field_a,
                field_b,
                group_marker,
                first_string,
            ) = header

            # O nome completo e curto precisam
            # pertencer a esse mesmo bloco.
            if not (
                header_offset
                < full_offset
                < header_offset + 0x400
            ):
                continue

            if not (
                header_offset
                < short_offset
                < header_offset + 0x400
            ):
                continue

            distance = (
                full_offset
                - header_offset
            )

            candidates.append(
                (
                    distance,
                    header_offset,
                    field_a,
                    field_b,
                    group_marker,
                    first_string,
                )
            )

        if not candidates:
            continue

        # O header correto tende a ser o
        # candidato válido mais próximo
        # antes do nome completo.
        candidates.sort(
            key=lambda item:
                item[0]
        )

        (
            _,
            header_offset,
            field_a,
            field_b,
            group_marker,
            first_string,
        ) = candidates[0]

        if (
            header_offset
            in seen_headers
        ):
            continue

        seen_headers.add(
            header_offset
        )

        results.append(
            ClubContainerCandidate(
                source=source,

                header_offset=
                    header_offset,

                field_a=
                    field_a,

                field_b=
                    field_b,

                group_marker=
                    group_marker,

                first_string=
                    first_string,

                full_name_rel=
                    full_offset
                    - header_offset,

                short_name_rel=
                    short_offset
                    - header_offset,
            )
        )

    return results


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "club_uid",
        type=int,
    )

    parser.add_argument(
        "--name",
        default="",
        help=(
            "Texto esperado no nome "
            "completo ou curto."
        ),
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
            config[
                "game_dir"
            ]
        )
        / "data"
        / "db"
    )

    lang = (
        db_dir
        / "lang_db.dat"
    ).read_bytes()

    client = (
        db_dir
        / "client_db.dat"
    ).read_bytes()

    server = (
        db_dir
        / "server_db.dat"
    ).read_bytes()

    lang_candidates = (
        find_lang_candidates(
            lang,
            args.club_uid,
        )
    )

    if args.name:

        query = (
            args.name
            .casefold()
        )

        filtered = [
            item
            for item
            in lang_candidates
            if (
                query
                in item.full_name.casefold()
                or query
                in item.short_name.casefold()
            )
        ]

        if filtered:
            lang_candidates = (
                filtered
            )

    print("=" * 110)

    print(
        " FM06 BRASIL 2026 - "
        "CLUB UID RESOLVER"
    )

    print("=" * 110)

    print()
    print(
        f"Club UID : "
        f"{args.club_uid}"
    )

    print(
        f"Filtro   : "
        f"{args.name or '-'}"
    )

    print(
        f"LANG candidates: "
        f"{len(lang_candidates)}"
    )

    if not lang_candidates:

        return

    for index, lang_record in (
        enumerate(
            lang_candidates,
            start=1,
        )
    ):

        print()
        print("=" * 110)

        print(
            f"LANG #{index}"
        )

        print("=" * 110)

        print(
            f"offset : "
            f"0x"
            f"{lang_record.offset:08X}"
        )

        print(
            f"flag   : "
            f"{lang_record.flag}"
        )

        print(
            f"full   : "
            f"{lang_record.full_name}"
        )

        print(
            f"short  : "
            f"{lang_record.short_name}"
        )

        print()

        for source_name, data in (
            (
                "client_db",
                client,
            ),
            (
                "server_db",
                server,
            ),
        ):

            containers = (
                find_containers(
                    source_name,
                    data,
                    lang_record.full_name,
                    lang_record.short_name,
                )
            )

            print(
                f"{source_name}: "
                f"{len(containers)} "
                f"container(s)"
            )

            for container in (
                containers[:10]
            ):

                print(
                    f"  header="
                    f"0x"
                    f"{container.header_offset:08X} "
                    f"KEY=("
                    f"{container.field_a},"
                    f"{container.field_b},"
                    f"{container.group_marker}"
                    f") "
                    f"first="
                    f"{container.first_string!r} "
                    f"full=+0x"
                    f"{container.full_name_rel:X} "
                    f"short=+0x"
                    f"{container.short_name_rel:X}"
                )

            if len(
                containers
            ) > 10:

                print(
                    f"  ... "
                    f"{len(containers)-10} "
                    f"omitidos"
                )


if __name__ == "__main__":
    main()