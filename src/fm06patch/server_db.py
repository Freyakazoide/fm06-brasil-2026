from __future__ import annotations

import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class SerializedString:
    prefix_offset: int
    text_offset: int
    end_offset: int
    length: int
    text: str

    @property
    def size(self) -> int:
        return self.end_offset - self.prefix_offset


@dataclass(frozen=True)
class ServerClubHeader:
    offset: int
    field_a: int
    field_b: int
    zero_flag: int
    group_marker: int


def read_u32(
    data: bytes | bytearray,
    offset: int,
) -> int:
    return struct.unpack_from(
        "<I",
        data,
        offset,
    )[0]


def parse_header(
    data: bytes,
    offset: int,
) -> ServerClubHeader:

    return ServerClubHeader(
        offset=offset,
        field_a=read_u32(
            data,
            offset,
        ),
        field_b=read_u32(
            data,
            offset + 4,
        ),
        zero_flag=data[
            offset + 8
        ],
        group_marker=read_u32(
            data,
            offset + 9,
        ),
    )


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

    for char in text:

        if char in "\r\n\t":
            continue

        if not char.isprintable():
            return False

    return True


def parse_serialized_string(
    data: bytes,
    prefix_offset: int,
    limit: int | None = None,
    max_chars: int = 150,
) -> SerializedString | None:

    if limit is None:
        limit = len(data)

    if (
        prefix_offset < 0
        or prefix_offset + 6 > limit
    ):
        return None

    try:
        length = read_u32(
            data,
            prefix_offset,
        )
    except struct.error:
        return None

    if not (
        1 <= length <= max_chars
    ):
        return None

    text_offset = (
        prefix_offset + 4
    )

    text_end = (
        text_offset
        + length * 2
    )

    terminator_end = (
        text_end + 2
    )

    if terminator_end > limit:
        return None

    if data[
        text_end:terminator_end
    ] != b"\x00\x00":
        return None

    raw = data[
        text_offset:text_end
    ]

    try:
        text = raw.decode(
            "utf-16le"
        )
    except UnicodeDecodeError:
        return None

    if not valid_text(text):
        return None

    return SerializedString(
        prefix_offset=prefix_offset,
        text_offset=text_offset,
        end_offset=terminator_end,
        length=length,
        text=text,
    )


def scan_serialized_strings(
    data: bytes,
    start: int,
    end: int,
    max_chars: int = 150,
) -> list[SerializedString]:

    start = max(
        0,
        start,
    )

    end = min(
        len(data),
        end,
    )

    result = []

    cursor = start

    while cursor + 6 <= end:

        token = (
            parse_serialized_string(
                data,
                cursor,
                limit=end,
                max_chars=max_chars,
            )
        )

        if token is None:
            cursor += 1
            continue

        result.append(
            token
        )

        # Evita detectar lixo dentro de uma
        # string que já foi validada.
        cursor = token.end_offset

    return result


def find_exact_string(
    tokens: list[
        SerializedString
    ],
    text: str,
) -> SerializedString | None:

    matches = [
        token
        for token in tokens
        if token.text == text
    ]

    if not matches:
        return None

    return matches[-1]