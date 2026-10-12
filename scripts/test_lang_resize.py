from __future__ import annotations

import hashlib
import json
import shutil
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "local.json"

BACKUP = ROOT / "workspace" / "baseline" / "lang_db.resize_original.dat"
WORKING = ROOT / "workspace" / "working" / "lang_db_resize_test.dat"

ORIGINAL_HASH = (
    "313B5D388208389E1C97FCE8270B880B"
    "B9B95BA444FCC392AFF90474DD24EEF4"
)

SCAN_START = 0x01539000
SCAN_END = 0x0153B000

TARGET_ID = 322

EXPECTED_FULL = "CR Flamengo"
EXPECTED_SHORT = "Flamengo"

NEW_SHORT = "FLAMENGO-RJ"


def sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)

    return h.hexdigest().upper()


def u32(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def lang_db() -> Path:
    with CONFIG.open("r", encoding="utf-8") as f:
        cfg = json.load(f)

    return (
        Path(cfg["game_dir"])
        / "data"
        / "db"
        / "lang_db.dat"
    )


def parse_record(data: bytes | bytearray, offset: int):
    try:
        record_id = u32(data, offset)

        full_len = u32(data, offset + 4)

        if not 1 <= full_len <= 100:
            return None

        full_start = offset + 8
        full_end = full_start + full_len * 2

        full = bytes(
            data[full_start:full_end]
        ).decode("utf-16le")

        if data[full_end:full_end + 2] != b"\x00\x00":
            return None

        flag_offset = full_end + 2
        flag = data[flag_offset]

        short_len_offset = flag_offset + 1
        short_len = u32(data, short_len_offset)

        if not 1 <= short_len <= 100:
            return None

        short_start = short_len_offset + 4
        short_end = short_start + short_len * 2

        short = bytes(
            data[short_start:short_end]
        ).decode("utf-16le")

        if data[short_end:short_end + 2] != b"\x00\x00":
            return None

        return {
            "offset": offset,
            "id": record_id,
            "full": full,
            "short": short,
            "short_len_offset": short_len_offset,
            "short_start": short_start,
            "short_end": short_end,
            "flag": flag,
        }

    except (
        UnicodeDecodeError,
        struct.error,
        IndexError,
    ):
        return None


def find_target(data):
    for offset in range(SCAN_START, SCAN_END):
        record = parse_record(data, offset)

        if record is None:
            continue

        if (
            record["id"] == TARGET_ID
            and record["full"] == EXPECTED_FULL
            and record["short"] == EXPECTED_SHORT
        ):
            return record

    return None


def apply() -> int:
    target = lang_db()

    print("=" * 72)
    print(" FM06 BRASIL 2026 - TESTE DE STRING VARIAVEL")
    print("=" * 72)
    print()

    current_hash = sha256(target)

    if current_hash != ORIGINAL_HASH:
        print("[ERRO] lang_db.dat não está original.")
        print(current_hash)
        return 1

    original = target.read_bytes()

    record = find_target(original)

    if record is None:
        print("[ERRO] Registro ativo do Flamengo não encontrado.")
        return 1

    print("[OK] Registro encontrado:")
    print(f"     Offset: 0x{record['offset']:08X}")
    print(f"     ID: {record['id']}")
    print(f"     Nome completo: {record['full']}")
    print(f"     Nome curto: {record['short']}")
    print()

    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    WORKING.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(target, BACKUP)

    if sha256(BACKUP) != ORIGINAL_HASH:
        print("[ERRO] Backup não passou na validação.")
        return 1

    patched = bytearray(original)

    new_encoded = NEW_SHORT.encode("utf-16le")
    new_length = len(NEW_SHORT)

    old_size = (
        record["short_end"]
        - record["short_start"]
    )

    print(f"Tamanho antigo: {len(original):,} bytes")
    print(
        f"Nome curto: {EXPECTED_SHORT!r} "
        f"({len(EXPECTED_SHORT)} caracteres)"
    )
    print(
        f"Novo nome : {NEW_SHORT!r} "
        f"({new_length} caracteres)"
    )
    print()

    struct.pack_into(
        "<I",
        patched,
        record["short_len_offset"],
        new_length,
    )

    patched[
        record["short_start"]:
        record["short_end"]
    ] = new_encoded

    expected_growth = len(new_encoded) - old_size

    WORKING.write_bytes(patched)

    actual_growth = (
        WORKING.stat().st_size
        - target.stat().st_size
    )

    print(f"Crescimento esperado: {expected_growth:+d} bytes")
    print(f"Crescimento real:     {actual_growth:+d} bytes")

    if actual_growth != expected_growth:
        print("[ERRO] Crescimento inesperado.")
        return 1

    # Confere se o próprio registro continua legível.
    check_data = WORKING.read_bytes()

    check = parse_record(
        check_data,
        record["offset"],
    )

    if check is None:
        print("[ERRO] Registro ficou ilegível após alteração.")
        return 1

    print()
    print("Registro reconstruído:")
    print(f"  ID:    {check['id']}")
    print(f"  Full:  {check['full']}")
    print(f"  Short: {check['short']}")

    if check["short"] != NEW_SHORT:
        print("[ERRO] Novo nome não foi validado.")
        return 1

    # Garante que o registro seguinte ainda existe,
    # mesmo deslocado pelo crescimento.
    search = "Fluminense FC".encode("utf-16le")

    pos = check_data.find(
        search,
        record["short_end"],
    )

    if pos == -1:
        print("[ERRO] Registro seguinte não encontrado.")
        return 1

    print()
    print(
        "[OK] Registro seguinte encontrado "
        f"em 0x{pos:08X}"
    )

    print()
    print("Instalando arquivo experimental...")

    shutil.copy2(
        WORKING,
        target,
    )

    print()
    print("[OK] TESTE INSTALADO.")
    print()
    print("Esperamos ver:")
    print()
    print(f"    {NEW_SHORT}")
    print()
    print("O arquivo cresceu:")
    print(f"    {expected_growth:+d} bytes")
    print()
    print("Para restaurar:")
    print(
        "python .\\scripts\\test_lang_resize.py restore"
    )

    return 0


def restore() -> int:
    target = lang_db()

    if not BACKUP.exists():
        print("[ERRO] Backup não encontrado.")
        return 1

    if sha256(BACKUP) != ORIGINAL_HASH:
        print("[ERRO] Backup inválido.")
        return 1

    shutil.copy2(
        BACKUP,
        target,
    )

    if sha256(target) != ORIGINAL_HASH:
        print("[ERRO] Falha na restauração.")
        return 1

    print("[OK] lang_db.dat original restaurado.")
    print()
    print(sha256(target))

    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso:")
        print(
            "  python scripts/test_lang_resize.py apply"
        )
        print(
            "  python scripts/test_lang_resize.py restore"
        )
        return 1

    command = sys.argv[1].lower()

    if command == "apply":
        return apply()

    if command == "restore":
        return restore()

    return 1


if __name__ == "__main__":
    sys.exit(main())