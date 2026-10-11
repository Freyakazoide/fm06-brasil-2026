from __future__ import annotations

import argparse
from pathlib import Path


def hex_dump(data: bytes, base_offset: int) -> str:
    lines = []

    for relative in range(0, len(data), 16):
        block = data[relative:relative + 16]
        absolute = base_offset + relative

        hex_part = " ".join(f"{b:02X}" for b in block)
        ascii_part = "".join(
            chr(b) if 32 <= b <= 126 else "."
            for b in block
        )

        lines.append(
            f"{absolute:08X}  {hex_part:<47}  {ascii_part}"
        )

    return "\n".join(lines)


def extract_utf16le_strings(
    data: bytes,
    base_offset: int,
    min_chars: int = 3,
) -> list[tuple[int, str]]:

    results = []

    # Testamos os dois alinhamentos porque o formato pode ser packed.
    for alignment in (0, 1):
        start = None
        chars = []

        i = alignment

        while i + 1 < len(data):
            lo = data[i]
            hi = data[i + 1]

            # Caracteres UTF-16LE simples que nos interessam agora.
            codepoint = lo | (hi << 8)

            printable = (
                codepoint == 0x20
                or 0x21 <= codepoint <= 0x7E
                or 0x00C0 <= codepoint <= 0x017F
            )

            if printable:
                if start is None:
                    start = i

                chars.append(chr(codepoint))
            else:
                if start is not None and len(chars) >= min_chars:
                    results.append(
                        (
                            base_offset + start,
                            "".join(chars),
                        )
                    )

                start = None
                chars = []

            i += 2

        if start is not None and len(chars) >= min_chars:
            results.append(
                (
                    base_offset + start,
                    "".join(chars),
                )
            )

    # Remove duplicatas resultantes dos dois alinhamentos.
    unique = {}

    for offset, text in results:
        unique[(offset, text)] = None

    return sorted(
        unique.keys(),
        key=lambda item: item[0],
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "file",
        type=Path,
        help="Arquivo .dat a analisar",
    )

    parser.add_argument(
        "offset",
        help="Offset central, decimal ou hexadecimal (ex: 0xCA57A)",
    )

    parser.add_argument(
        "--before",
        type=int,
        default=512,
    )

    parser.add_argument(
        "--after",
        type=int,
        default=512,
    )

    args = parser.parse_args()

    offset = int(args.offset, 0)

    file_size = args.file.stat().st_size

    start = max(0, offset - args.before)
    end = min(file_size, offset + args.after)

    with args.file.open("rb") as f:
        f.seek(start)
        data = f.read(end - start)

    print("=" * 80)
    print(f"Arquivo : {args.file}")
    print(f"Offset  : 0x{offset:X}")
    print(f"Janela  : 0x{start:X} - 0x{end:X}")
    print("=" * 80)

    print()
    print("HEX DUMP")
    print("-" * 80)
    print(hex_dump(data, start))

    print()
    print("STRINGS UTF-16LE")
    print("-" * 80)

    strings = extract_utf16le_strings(
        data,
        start,
    )

    if not strings:
        print("Nenhuma string encontrada.")
    else:
        for string_offset, text in strings:
            print(
                f"0x{string_offset:08X}  {text}"
            )


if __name__ == "__main__":
    main()