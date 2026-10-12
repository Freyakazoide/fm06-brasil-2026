from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


# Primeira build suportada:
# FM06 6.0.2.7437
#
# Região confirmada empiricamente como pertencente à
# tabela de nomes utilizada pela interface atual.
ACTIVE_TABLE_START = 0x01539000
ACTIVE_TABLE_END = 0x0153B000


@dataclass(frozen=True)
class ClubNameRecord:
    offset: int
    record_id: int

    full_name: str
    short_name: str

    flag: int

    full_name_offset: int
    short_name_offset: int

    full_length: int
    short_length: int

    known_end: int

    @property
    def offset_hex(self) -> str:
        return f"0x{self.offset:08X}"

    @property
    def record_id_hex(self) -> str:
        return f"0x{self.record_id:X}"


@dataclass(frozen=True)
class ClubNameUpdate:
    record_id: int
    full_name: str | None = None
    short_name: str | None = None


def read_u32(
    data: bytes | bytearray,
    offset: int,
) -> int:
    return struct.unpack_from(
        "<I",
        data,
        offset,
    )[0]


def encode_utf16(text: str) -> bytes:
    return text.encode("utf-16le")


def utf16_length(text: str) -> int:
    """
    Quantidade de unidades UTF-16.

    Não usamos simplesmente len(text), porque caracteres
    fora do BMP podem ocupar duas unidades UTF-16.
    """
    return len(encode_utf16(text)) // 2


def decode_utf16(
    data: bytes | bytearray,
    offset: int,
    units: int,
) -> str | None:

    if units <= 0:
        return None

    end = offset + units * 2

    if end > len(data):
        return None

    raw = bytes(data[offset:end])

    try:
        return raw.decode("utf-16le")
    except UnicodeDecodeError:
        return None


def parse_club_record(
    data: bytes | bytearray,
    offset: int,
) -> ClubNameRecord | None:
    """
    Layout confirmado:

        uint32 record_id
        uint32 full_name_length
        wchar[] full_name
        uint16 0x0000
        uint8 flag
        uint32 short_name_length
        wchar[] short_name
        uint16 0x0000

    Existem bytes adicionais após esse trecho.
    Eles continuam preservados pelo writer.
    """

    try:
        if offset < 0 or offset + 16 > len(data):
            return None

        record_id = read_u32(
            data,
            offset,
        )

        if not (1 <= record_id <= 10_000_000):
            return None

        full_length = read_u32(
            data,
            offset + 4,
        )

        if not (1 <= full_length <= 150):
            return None

        full_start = offset + 8

        full_name = decode_utf16(
            data,
            full_start,
            full_length,
        )

        if not full_name:
            return None

        full_end = (
            full_start
            + full_length * 2
        )

        if data[
            full_end:full_end + 2
        ] != b"\x00\x00":
            return None

        flag_offset = full_end + 2

        if flag_offset >= len(data):
            return None

        flag = data[flag_offset]

        short_length_offset = (
            flag_offset + 1
        )

        short_length = read_u32(
            data,
            short_length_offset,
        )

        if not (1 <= short_length <= 150):
            return None

        short_start = (
            short_length_offset + 4
        )

        short_name = decode_utf16(
            data,
            short_start,
            short_length,
        )

        if not short_name:
            return None

        short_end = (
            short_start
            + short_length * 2
        )

        if data[
            short_end:short_end + 2
        ] != b"\x00\x00":
            return None

        # Evita falsos positivos binários muito óbvios.
        if not any(
            char.isalpha()
            for char in full_name
        ):
            return None

        if not any(
            char.isalpha()
            for char in short_name
        ):
            return None

        return ClubNameRecord(
            offset=offset,
            record_id=record_id,
            full_name=full_name,
            short_name=short_name,
            flag=flag,
            full_name_offset=full_start,
            short_name_offset=short_start,
            full_length=full_length,
            short_length=short_length,
            known_end=short_end + 2,
        )

    except (
        IndexError,
        struct.error,
    ):
        return None


def scan_club_records(
    data: bytes | bytearray,
    start: int = ACTIVE_TABLE_START,
    end: int = ACTIVE_TABLE_END,
) -> list[ClubNameRecord]:

    start = max(
        0,
        start,
    )

    end = min(
        len(data),
        end,
    )

    records: list[ClubNameRecord] = []

    for offset in range(start, end):
        record = parse_club_record(
            data,
            offset,
        )

        if record is not None:
            records.append(record)

    return records


def serialize_record(
    record: ClubNameRecord,
    full_name: str,
    short_name: str,
) -> bytes:

    full_encoded = encode_utf16(
        full_name,
    )

    short_encoded = encode_utf16(
        short_name,
    )

    result = bytearray()

    result += struct.pack(
        "<I",
        record.record_id,
    )

    result += struct.pack(
        "<I",
        utf16_length(full_name),
    )

    result += full_encoded
    result += b"\x00\x00"

    result += bytes([
        record.flag,
    ])

    result += struct.pack(
        "<I",
        utf16_length(short_name),
    )

    result += short_encoded
    result += b"\x00\x00"

    return bytes(result)


def apply_updates(
    data: bytes,
    updates: Iterable[ClubNameUpdate],
    start: int = ACTIVE_TABLE_START,
    end: int = ACTIVE_TABLE_END,
) -> bytes:

    records = scan_club_records(
        data,
        start=start,
        end=end,
    )

    by_id: dict[int, ClubNameRecord] = {}

    for record in records:
        if record.record_id in by_id:
            raise ValueError(
                "ID duplicado dentro da tabela ativa: "
                f"{record.record_id}"
            )

        by_id[
            record.record_id
        ] = record

    operations = []

    for update in updates:
        record = by_id.get(
            update.record_id
        )

        if record is None:
            raise KeyError(
                "Registro não encontrado: "
                f"{update.record_id}"
            )

        full_name = (
            update.full_name
            if update.full_name is not None
            else record.full_name
        )

        short_name = (
            update.short_name
            if update.short_name is not None
            else record.short_name
        )

        replacement = serialize_record(
            record,
            full_name,
            short_name,
        )

        operations.append(
            (
                record.offset,
                record.known_end,
                replacement,
            )
        )

    # Fundamental:
    #
    # editamos de trás para frente para mudanças de
    # tamanho não invalidarem offsets ainda pendentes.
    operations.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    result = bytearray(data)

    for offset, known_end, replacement in operations:
        result[
            offset:known_end
        ] = replacement

    return bytes(result)


class LangDatabase:
    def __init__(
        self,
        data: bytes,
    ):
        self.data = data

    @classmethod
    def load(
        cls,
        path: Path,
    ) -> "LangDatabase":
        return cls(
            path.read_bytes()
        )

    def clubs(
        self,
    ) -> list[ClubNameRecord]:
        return scan_club_records(
            self.data
        )

    def club_by_id(
        self,
        record_id: int,
    ) -> ClubNameRecord:

        matches = [
            record
            for record in self.clubs()
            if record.record_id == record_id
        ]

        if not matches:
            raise KeyError(
                f"Clube {record_id} não encontrado."
            )

        if len(matches) != 1:
            raise ValueError(
                f"Clube {record_id} apareceu "
                f"{len(matches)} vezes."
            )

        return matches[0]

    def updated(
        self,
        updates: Iterable[ClubNameUpdate],
    ) -> "LangDatabase":

        return LangDatabase(
            apply_updates(
                self.data,
                updates,
            )
        )

    def save(
        self,
        path: Path,
    ) -> None:

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_bytes(
            self.data
        )