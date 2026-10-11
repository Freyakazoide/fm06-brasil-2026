from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONFIG_FILE = PROJECT_ROOT / "config" / "local.json"

WORKING_DIR = PROJECT_ROOT / "workspace" / "working"

OUTPUT_FILE = WORKING_DIR / "client_db_test.dat"
REPORT_FILE = WORKING_DIR / "client_db_test_report.json"


# Descoberto pela análise binária.
FLAMENGO_SHORT_NAME_OFFSET = 0xBD62C

ORIGINAL_TEXT = "Flamengo"
PATCHED_TEXT = "FLAMENGO"


def sha256_file(path: Path) -> str:
    sha = hashlib.sha256()

    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            sha.update(chunk)

    return sha.hexdigest().upper()


def main():
    print("=" * 72)
    print(" FM06 BRASIL 2026 - PRIMEIRO PATCH EXPERIMENTAL")
    print("=" * 72)

    with CONFIG_FILE.open("r", encoding="utf-8") as file:
        config = json.load(file)

    game_dir = Path(config["game_dir"])

    original_file = (
        game_dir
        / "data"
        / "db"
        / "client_db.dat"
    )

    if not original_file.exists():
        raise FileNotFoundError(original_file)

    WORKING_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("Original:")
    print(original_file)

    original_hash = sha256_file(original_file)

    print()
    print("SHA-256 original:")
    print(original_hash)

    # Nunca altera o arquivo original.
    shutil.copy2(
        original_file,
        OUTPUT_FILE,
    )

    original_bytes = ORIGINAL_TEXT.encode("utf-16le")
    patched_bytes = PATCHED_TEXT.encode("utf-16le")

    if len(original_bytes) != len(patched_bytes):
        raise RuntimeError(
            "O teste exige strings de exatamente o mesmo tamanho."
        )

    with OUTPUT_FILE.open("r+b") as file:
        file.seek(FLAMENGO_SHORT_NAME_OFFSET)

        found = file.read(len(original_bytes))

        if found != original_bytes:
            print()
            print("[ERRO] Conteudo inesperado no offset.")

            print("Esperado:")
            print(original_bytes.hex(" ").upper())

            print("Encontrado:")
            print(found.hex(" ").upper())

            raise RuntimeError(
                "O offset nao corresponde a 'Flamengo'."
            )

        print()
        print(
            f"[OK] Encontrado '{ORIGINAL_TEXT}' "
            f"em 0x{FLAMENGO_SHORT_NAME_OFFSET:X}"
        )

        file.seek(FLAMENGO_SHORT_NAME_OFFSET)

        file.write(patched_bytes)

    patched_hash = sha256_file(OUTPUT_FILE)

    original_data = original_file.read_bytes()
    patched_data = OUTPUT_FILE.read_bytes()

    changes = []

    for offset, (before, after) in enumerate(
        zip(original_data, patched_data)
    ):
        if before != after:
            changes.append(
                {
                    "offset": offset,
                    "offset_hex": f"0x{offset:X}",
                    "before": before,
                    "after": after,
                }
            )

    print()
    print("[OK] Copia modificada criada:")
    print(OUTPUT_FILE)

    print()
    print("SHA-256 modificado:")
    print(patched_hash)

    print()
    print(f"Bytes alterados: {len(changes)}")

    for change in changes:
        print(
            f"  {change['offset_hex']}: "
            f"{change['before']:02X} -> "
            f"{change['after']:02X}"
        )

    report = {
        "source": str(original_file),
        "output": str(OUTPUT_FILE),
        "original_sha256": original_hash,
        "patched_sha256": patched_hash,
        "patch": {
            "offset": FLAMENGO_SHORT_NAME_OFFSET,
            "offset_hex": (
                f"0x{FLAMENGO_SHORT_NAME_OFFSET:X}"
            ),
            "original": ORIGINAL_TEXT,
            "replacement": PATCHED_TEXT,
        },
        "changed_bytes": changes,
    }

    with REPORT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print()
    print("[OK] Relatorio:")
    print(REPORT_FILE)

    print()
    print("=" * 72)
    print(" O ARQUIVO ORIGINAL DO FM06 NAO FOI ALTERADO")
    print("=" * 72)


if __name__ == "__main__":
    main()