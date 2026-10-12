from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "local.json"

BACKUP = ROOT / "workspace" / "baseline" / "lang_db.original.dat"
WORKING = ROOT / "workspace" / "working" / "lang_db_probe.dat"

ORIGINAL_HASH = (
    "313B5D388208389E1C97FCE8270B880B"
    "B9B95BA444FCC392AFF90474DD24EEF4"
)

NEEDLE = "Flamengo".encode("utf-16le")


def sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)

    return h.hexdigest().upper()


def lang_db() -> Path:
    with CONFIG.open("r", encoding="utf-8") as f:
        cfg = json.load(f)

    return Path(cfg["game_dir"]) / "data" / "db" / "lang_db.dat"


def find_all(data: bytes, needle: bytes) -> list[int]:
    result = []
    pos = 0

    while True:
        pos = data.find(needle, pos)

        if pos == -1:
            break

        result.append(pos)
        pos += len(needle)

    return result


def apply() -> int:
    target = lang_db()

    if sha256(target) != ORIGINAL_HASH:
        print("[ERRO] lang_db.dat não está original.")
        print("Restaure antes de executar este probe.")
        return 1

    data = target.read_bytes()
    offsets = find_all(data, NEEDLE)

    print(f"Ocorrências encontradas: {len(offsets)}")
    print()

    if not offsets:
        return 1

    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    WORKING.parent.mkdir(parents=True, exist_ok=True)

    if not BACKUP.exists():
        shutil.copy2(target, BACKUP)

    if sha256(BACKUP) != ORIGINAL_HASH:
        print("[ERRO] Backup inválido.")
        return 1

    patched = bytearray(data)

    for index, offset in enumerate(offsets, start=1):
        # Exatamente 8 caracteres, igual a "Flamengo".
        marker = f"FM{index:06d}"

        encoded = marker.encode("utf-16le")

        if len(encoded) != len(NEEDLE):
            raise RuntimeError(marker)

        patched[
            offset:offset + len(NEEDLE)
        ] = encoded

        print(
            f"{index:02d}  "
            f"0x{offset:08X}  "
            f"Flamengo -> {marker}"
        )

    WORKING.write_bytes(patched)

    if WORKING.stat().st_size != target.stat().st_size:
        raise RuntimeError("Tamanho do arquivo mudou.")

    shutil.copy2(WORKING, target)

    print()
    print("[OK] Probe instalado.")
    print()
    print("Abra o FM06 e procure o Flamengo.")
    print("Anote exatamente o código exibido, por exemplo:")
    print()
    print("    FM000007")
    print()
    print("Depois restaure com:")
    print(
        "python .\\scripts\\probe_lang_flamego.py restore"
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

    shutil.copy2(BACKUP, target)

    if sha256(target) != ORIGINAL_HASH:
        print("[ERRO] Falha ao restaurar.")
        return 1

    print("[OK] lang_db.dat original restaurado.")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso:")
        print("  python scripts/probe_lang_flamego.py apply")
        print("  python scripts/probe_lang_flamego.py restore")
        return 1

    if sys.argv[1].lower() == "apply":
        return apply()

    if sys.argv[1].lower() == "restore":
        return restore()

    return 1


if __name__ == "__main__":
    sys.exit(main())