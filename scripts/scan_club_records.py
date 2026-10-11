from __future__ import annotations

import struct
from pathlib import Path


DB_FILE = Path(
    r"C:\Games\Football Manager 2006\data\db\client_db.dat"
)

# Região que já sabemos que contém os clubes brasileiros.
SCAN_START = 0xBD000
SCAN_END = 0xC5000

# Campo constante observado nos registros deste bloco.
OBSERVED_CONSTANT = 0xBD


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def extract_utf16_strings(
    data: bytes,
    start: int,
    end: int,
    min_chars: int = 3,
):
    results = []

    for alignment in (0, 1):
        current_start = None
        chars = []

        i = start + alignment

        while i + 1 < end:
            codepoint = data[i] | (data[i + 1] << 8)

            printable = (
                codepoint == 0x20
                or 0x21 <= codepoint <= 0x7E
                or 0x00C0 <= codepoint <= 0x017F
            )

            if printable:
                if current_start is None:
                    current_start = i

                chars.append(chr(codepoint))

            else:
                if (
                    current_start is not None
                    and len(chars) >= min_chars
                ):
                    results.append(
                        (
                            current_start,
                            "".join(chars),
                        )
                    )

                current_start = None
                chars = []

            i += 2

    unique = {}

    for offset, text in results:
        unique[(offset, text)] = None

    return sorted(
        unique.keys(),
        key=lambda item: item[0],
    )


def find_record_headers(data: bytes):
    headers = []

    start = max(SCAN_START, 8)
    end = min(SCAN_END, len(data) - 16)

    for offset in range(start, end):

        # Estrutura observada:
        #
        # uint32 field_a
        # uint32 field_b
        # byte   zero
        # uint32 0xBD
        #
        if data[offset + 8] != 0:
            continue

        constant = u32(data, offset + 9)

        if constant != OBSERVED_CONSTANT:
            continue

        field_a = u32(data, offset)
        field_b = u32(data, offset + 4)

        # Filtros para evitar falsos positivos.
        if not (100 <= field_a <= 1000):
            continue

        if not (100 <= field_b <= 5000):
            continue

        headers.append(
            {
                "offset": offset,
                "field_a": field_a,
                "field_b": field_b,
                "constant": constant,
            }
        )

    return headers


def main():
    data = DB_FILE.read_bytes()

    headers = find_record_headers(data)

    print("=" * 90)
    print(" FM06 BRASIL 2026 - POSSIVEIS REGISTROS DE CLUBES")
    print("=" * 90)
    print()

    print(f"Arquivo: {DB_FILE}")
    print(
        f"Faixa:   0x{SCAN_START:X} - 0x{SCAN_END:X}"
    )
    print(f"Headers encontrados: {len(headers)}")
    print()

    for index, header in enumerate(headers):

        start = header["offset"]

        if index + 1 < len(headers):
            end = headers[index + 1]["offset"]
        else:
            end = min(start + 2048, len(data))

        # Evita interpretar regiões gigantes em caso
        # de falso positivo.
        if end - start > 4096:
            end = start + 4096

        strings = extract_utf16_strings(
            data,
            start,
            end,
        )

        print("-" * 90)

        print(
            f"Offset: 0x{start:08X} | "
            f"field_a={header['field_a']} "
            f"(0x{header['field_a']:X}) | "
            f"field_b={header['field_b']} "
            f"(0x{header['field_b']:X}) | "
            f"constant={header['constant']}"
        )

        if not strings:
            print("  [sem strings]")
            continue

        for string_offset, text in strings:
            print(
                f"  0x{string_offset:08X}  {text}"
            )

        if len(strings) >= 2:
            print()
            print(
                f"  POSSIVEL NOME COMPLETO: "
                f"{strings[-2][1]}"
            )
            print(
                f"  POSSIVEL NOME CURTO:    "
                f"{strings[-1][1]}"
            )

    print()
    print("=" * 90)


if __name__ == "__main__":
    main()