from __future__ import annotations

import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

CONFIG_FILE = ROOT / "config" / "local.json"

OUTPUT_FILE = (
    ROOT
    / "workspace"
    / "dumps"
    / "active_lang_clubs.json"
)

SCAN_START = 0x01539000
SCAN_END = 0x0153B000


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def read_utf16(
    data: bytes,
    offset: int,
    length: int,
) -> str | None:

    byte_length = length * 2
    end = offset + byte_length

    if end > len(data):
        return None

    raw = data[offset:end]

    try:
        text = raw.decode("utf-16le")
    except UnicodeDecodeError:
        return None

    if not text:
        return None

    if not any(ch.isalpha() for ch in text):
        return None

    return text


def parse_candidate(
    data: bytes,
    offset: int,
) -> dict | None:

    if offset + 16 >= len(data):
        return None

    record_id = u32(data, offset)
    full_length = u32(data, offset + 4)

    if not (1 <= full_length <= 80):
        return None

    full_start = offset + 8

    full_name = read_utf16(
        data,
        full_start,
        full_length,
    )

    if full_name is None:
        return None

    full_end = full_start + full_length * 2

    # String deve terminar em UTF-16 NUL.
    if data[full_end:full_end + 2] != b"\x00\x00":
        return None

    flag_offset = full_end + 2

    if flag_offset + 5 > len(data):
        return None

    flag = data[flag_offset]

    short_length_offset = flag_offset + 1

    short_length = u32(
        data,
        short_length_offset,
    )

    if not (1 <= short_length <= 80):
        return None

    short_start = short_length_offset + 4

    short_name = read_utf16(
        data,
        short_start,
        short_length,
    )

    if short_name is None:
        return None

    short_end = short_start + short_length * 2

    if data[short_end:short_end + 2] != b"\x00\x00":
        return None

    return {
        "record_offset": offset,
        "record_offset_hex": f"0x{offset:08X}",
        "record_id": record_id,
        "record_id_hex": f"0x{record_id:X}",
        "full_name_length": full_length,
        "full_name_offset": full_start,
        "full_name_offset_hex": f"0x{full_start:08X}",
        "full_name": full_name,
        "flag": flag,
        "short_name_length": short_length,
        "short_name_offset": short_start,
        "short_name_offset_hex": f"0x{short_start:08X}",
        "short_name": short_name,
        "record_known_end": short_end + 2,
    }


def main():
    with CONFIG_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        config = json.load(file)

    lang_db = (
        Path(config["game_dir"])
        / "data"
        / "db"
        / "lang_db.dat"
    )

    data = lang_db.read_bytes()

    records = []

    start = max(0, SCAN_START)
    end = min(len(data), SCAN_END)

    for offset in range(start, end):
        record = parse_candidate(
            data,
            offset,
        )

        if record is not None:
            records.append(record)

    print("=" * 92)
    print(" FM06 BRASIL 2026 - TABELA ATIVA DE NOMES")
    print("=" * 92)
    print()

    for record in records:
        print(
            f"{record['record_offset_hex']}  "
            f"ID={record['record_id']:5d} "
            f"({record['record_id_hex']})  "
            f"flag={record['flag']}  "
            f"{record['full_name']!r} -> "
            f"{record['short_name']!r}"
        )

    print()
    print(f"Registros encontrados: {len(records)}")

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            {
                "source": str(lang_db),
                "scan_start": SCAN_START,
                "scan_end": SCAN_END,
                "records": records,
            },
            file,
            indent=4,
            ensure_ascii=False,
        )

    print()
    print("JSON salvo em:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()