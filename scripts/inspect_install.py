from __future__ import annotations

import json
import math
import mmap
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_CONFIG = PROJECT_ROOT / "config" / "local.json"

OUTPUT_DIR = PROJECT_ROOT / "workspace" / "dumps"
OUTPUT_FILE = OUTPUT_DIR / "db_probe.json"


DATABASE_FILES = [
    "data/db/server_db.dat",
    "data/db/people_db.dat",
    "data/db/client_db.dat",
    "data/db/lang_db.dat",
]


SEARCH_TERMS = [
    "Flamengo",
    "Palmeiras",
    "Corinthians",
    "Sao Paulo",
    "São Paulo",
    "Brazil",
    "Brasil",
    "Ronaldinho",
    "Ronaldo",
    "Adriano",
]


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def format_size(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size)

    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.2f} {unit}"
        value /= 1024

    return str(size)


def hex_dump(data: bytes) -> str:
    lines = []

    for offset in range(0, len(data), 16):
        block = data[offset:offset + 16]

        hex_part = " ".join(f"{byte:02X}" for byte in block)
        ascii_part = "".join(
            chr(byte) if 32 <= byte <= 126 else "."
            for byte in block
        )

        lines.append(
            f"{offset:08X}  "
            f"{hex_part:<47}  "
            f"{ascii_part}"
        )

    return "\n".join(lines)


def entropy(data: bytes) -> float:
    if not data:
        return 0.0

    counts = Counter(data)
    total = len(data)

    result = 0.0

    for count in counts.values():
        probability = count / total
        result -= probability * math.log2(probability)

    return result


def find_offsets(
    mm: mmap.mmap,
    needle: bytes,
    max_matches: int = 20,
) -> list[int]:

    offsets = []
    position = 0

    while len(offsets) < max_matches:
        position = mm.find(needle, position)

        if position == -1:
            break

        offsets.append(position)
        position += 1

    return offsets


def search_term(mm: mmap.mmap, term: str) -> dict:
    encodings = {
        "utf8": term.encode("utf-8"),
        "latin1": None,
        "utf16le": term.encode("utf-16le"),
    }

    try:
        encodings["latin1"] = term.encode("latin-1")
    except UnicodeEncodeError:
        encodings["latin1"] = None

    results = {}

    for encoding_name, encoded in encodings.items():
        if not encoded:
            continue

        offsets = find_offsets(mm, encoded)

        if offsets:
            results[encoding_name] = offsets

    return results


def analyze_file(path: Path) -> dict:
    file_size = path.stat().st_size

    with path.open("rb") as file:
        header = file.read(128)

        file.seek(0)
        sample = file.read(min(file_size, 1024 * 1024))

    result = {
        "size": file_size,
        "size_human": format_size(file_size),
        "header_hex": header.hex(" ").upper(),
        "sample_entropy": round(entropy(sample), 4),
        "searches": {},
    }

    with path.open("rb") as file:
        with mmap.mmap(
            file.fileno(),
            length=0,
            access=mmap.ACCESS_READ,
        ) as mm:

            for term in SEARCH_TERMS:
                matches = search_term(mm, term)

                if matches:
                    result["searches"][term] = matches

    return result


def main():
    config = load_json(LOCAL_CONFIG)

    game_dir = Path(config["game_dir"])

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    report = {
        "game_dir": str(game_dir),
        "files": {},
    }

    print("=" * 72)
    print(" FM06 BRASIL 2026 - PROBE DOS BANCOS")
    print("=" * 72)

    for relative_name in DATABASE_FILES:
        path = game_dir / relative_name

        print()
        print("-" * 72)
        print(relative_name)
        print("-" * 72)

        if not path.exists():
            print("[FALTA]")
            continue

        info = analyze_file(path)

        report["files"][relative_name] = info

        print(f"Tamanho: {info['size_human']}")
        print(
            f"Entropia da amostra: "
            f"{info['sample_entropy']:.4f} / 8.0000"
        )

        print()
        print("Primeiros 128 bytes:")
        print()

        with path.open("rb") as file:
            print(hex_dump(file.read(128)))

        print()
        print("Termos encontrados:")

        if not info["searches"]:
            print("  nenhum")
        else:
            for term, encodings in info["searches"].items():
                print(f"  {term}")

                for encoding, offsets in encodings.items():
                    formatted = ", ".join(
                        f"0x{offset:X}"
                        for offset in offsets
                    )

                    print(
                        f"    {encoding}: {formatted}"
                    )

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print()
    print("=" * 72)
    print("Relatorio salvo em:")
    print(OUTPUT_FILE)
    print("=" * 72)


if __name__ == "__main__":
    main()