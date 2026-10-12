from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONFIG_FILE = PROJECT_ROOT / "config" / "local.json"

WORKSPACE = PROJECT_ROOT / "workspace"
WORKING_DIR = WORKSPACE / "working"
BASELINE_DIR = WORKSPACE / "baseline"

BACKUP_FILE = BASELINE_DIR / "lang_db.original.dat"
PATCHED_FILE = WORKING_DIR / "lang_db_test.dat"


EXPECTED_ORIGINAL_HASH = (
    "313B5D388208389E1C97FCE8270B880B"
    "B9B95BA444FCC392AFF90474DD24EEF4"
)


PATCHES = [
    {
        "offset": 0x8FEF6,
        "original": "CR Flamengo",
        "replacement": "CR FLAMENGO",
    },
    {
        "offset": 0x8FF13,
        "original": "Flamengo",
        "replacement": "FLAMENGO",
    },
]


def sha256_file(path: Path) -> str:
    sha = hashlib.sha256()

    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            sha.update(chunk)

    return sha.hexdigest().upper()


def get_lang_db() -> Path:
    with CONFIG_FILE.open("r", encoding="utf-8") as file:
        config = json.load(file)

    return (
        Path(config["game_dir"])
        / "data"
        / "db"
        / "lang_db.dat"
    )


def verify_patches(path: Path, patched: bool) -> bool:
    with path.open("rb") as file:

        for patch in PATCHES:
            text = (
                patch["replacement"]
                if patched
                else patch["original"]
            )

            expected = text.encode("utf-16le")

            file.seek(patch["offset"])
            found = file.read(len(expected))

            if found != expected:
                return False

    return True


def build_test_file() -> str:
    source = get_lang_db()

    if sha256_file(source) != EXPECTED_ORIGINAL_HASH:
        raise RuntimeError(
            "lang_db.dat não corresponde ao baseline original."
        )

    if not verify_patches(source, patched=False):
        raise RuntimeError(
            "Os offsets do Flamengo não correspondem "
            "ao conteúdo esperado."
        )

    WORKING_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        source,
        PATCHED_FILE,
    )

    with PATCHED_FILE.open("r+b") as file:

        for patch in PATCHES:
            original = patch["original"].encode("utf-16le")
            replacement = patch["replacement"].encode("utf-16le")

            if len(original) != len(replacement):
                raise RuntimeError(
                    "As strings precisam ter o mesmo tamanho."
                )

            file.seek(patch["offset"])

            found = file.read(len(original))

            if found != original:
                raise RuntimeError(
                    f"Conteúdo inesperado em "
                    f"0x{patch['offset']:X}"
                )

            file.seek(patch["offset"])
            file.write(replacement)

    if PATCHED_FILE.stat().st_size != source.stat().st_size:
        raise RuntimeError(
            "O tamanho do lang_db.dat foi alterado."
        )

    if not verify_patches(PATCHED_FILE, patched=True):
        raise RuntimeError(
            "A cópia modificada não passou na validação."
        )

    return sha256_file(PATCHED_FILE)


def status() -> int:
    target = get_lang_db()

    print("=" * 72)
    print(" FM06 BRASIL 2026 - STATUS DO LANG_DB")
    print("=" * 72)
    print()

    if not target.exists():
        print("[ERRO] lang_db.dat não encontrado.")
        return 1

    current_hash = sha256_file(target)

    print("Arquivo:")
    print(f"  {target}")
    print()

    print("SHA-256:")
    print(f"  {current_hash}")
    print()

    if current_hash == EXPECTED_ORIGINAL_HASH:
        print("[ORIGINAL] lang_db.dat original detectado.")

    elif verify_patches(target, patched=True):
        print("[TESTE] Patch de nomes do Flamengo detectado.")

    else:
        print("[DESCONHECIDO] Estado do arquivo não reconhecido.")

    print()

    if BACKUP_FILE.exists():
        backup_hash = sha256_file(BACKUP_FILE)

        print("Backup:")
        print(f"  {BACKUP_FILE}")

        if backup_hash == EXPECTED_ORIGINAL_HASH:
            print("[OK] Backup original validado.")
        else:
            print("[ALERTA] Backup possui hash inesperado.")
    else:
        print("[INFO] Backup ainda não criado.")

    return 0


def apply_patch() -> int:
    target = get_lang_db()

    print("=" * 72)
    print(" FM06 BRASIL 2026 - TESTE NO LANG_DB")
    print("=" * 72)
    print()

    if not target.exists():
        print("[ERRO] lang_db.dat não encontrado.")
        return 1

    current_hash = sha256_file(target)

    if current_hash != EXPECTED_ORIGINAL_HASH:

        if verify_patches(target, patched=True):
            print("[INFO] Patch já está aplicado.")
            return 0

        print("[ERRO] lang_db.dat não está no estado original.")
        print(f"Hash encontrado: {current_hash}")
        return 1

    BASELINE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not BACKUP_FILE.exists():
        shutil.copy2(
            target,
            BACKUP_FILE,
        )

        if sha256_file(BACKUP_FILE) != EXPECTED_ORIGINAL_HASH:
            print("[ERRO] Falha ao validar backup.")
            return 1

        print("[OK] Backup original criado:")
        print(BACKUP_FILE)

    else:
        if sha256_file(BACKUP_FILE) != EXPECTED_ORIGINAL_HASH:
            print("[ERRO] Backup existente inválido.")
            return 1

        print("[OK] Backup original já existente.")

    print()
    print("Criando lang_db.dat experimental...")

    patched_hash = build_test_file()

    print("[OK] Cópia criada.")
    print()
    print("SHA-256 experimental:")
    print(patched_hash)

    print()
    print("Instalando no jogo...")

    shutil.copy2(
        PATCHED_FILE,
        target,
    )

    if not verify_patches(target, patched=True):
        print("[ERRO] Validação falhou.")
        print("Restaurando original...")

        shutil.copy2(
            BACKUP_FILE,
            target,
        )

        return 1

    print()
    print("[OK] PATCH DE TESTE INSTALADO.")
    print()
    print("Esperamos encontrar:")
    print()
    print("    CR FLAMENGO")
    print("    FLAMENGO")
    print()
    print("Para restaurar:")
    print(
        "python .\\scripts\\test_lang_patch.py restore"
    )

    return 0


def restore() -> int:
    target = get_lang_db()

    print("=" * 72)
    print(" FM06 BRASIL 2026 - RESTAURAR LANG_DB")
    print("=" * 72)
    print()

    if not BACKUP_FILE.exists():
        print("[ERRO] Backup não encontrado.")
        return 1

    if sha256_file(BACKUP_FILE) != EXPECTED_ORIGINAL_HASH:
        print("[ERRO] Backup não corresponde ao original.")
        return 1

    shutil.copy2(
        BACKUP_FILE,
        target,
    )

    restored_hash = sha256_file(target)

    if restored_hash != EXPECTED_ORIGINAL_HASH:
        print("[ERRO] Falha na restauração.")
        return 1

    print("[OK] lang_db.dat original restaurado.")
    print()
    print("SHA-256:")
    print(restored_hash)

    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso:")
        print(
            "python scripts/test_lang_patch.py status"
        )
        print(
            "python scripts/test_lang_patch.py apply"
        )
        print(
            "python scripts/test_lang_patch.py restore"
        )
        return 1

    command = sys.argv[1].lower()

    if command == "status":
        return status()

    if command == "apply":
        return apply_patch()

    if command == "restore":
        return restore()

    print(f"Comando inválido: {command}")
    return 1


if __name__ == "__main__":
    sys.exit(main())