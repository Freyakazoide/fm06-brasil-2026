from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONFIG_FILE = PROJECT_ROOT / "config" / "local.json"

WORKSPACE = PROJECT_ROOT / "workspace"

TEST_FILE = (
    WORKSPACE
    / "working"
    / "client_db_test.dat"
)

BACKUP_FILE = (
    WORKSPACE
    / "baseline"
    / "client_db.original.dat"
)

EXPECTED_ORIGINAL_HASH = (
    "850D0ED841BF2D8DA4E67976F4421120"
    "BDB87ABC42B82D2F1D8B7388EAEFBCF4"
)

EXPECTED_PATCHED_HASH = (
    "5009A2DEAFCF3DF8E1DE162C22954F48"
    "CBE810C90CFA302C917CA56D499AB83E"
)


def sha256_file(path: Path) -> str:
    sha = hashlib.sha256()

    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            sha.update(chunk)

    return sha.hexdigest().upper()


def get_client_db() -> Path:
    with CONFIG_FILE.open("r", encoding="utf-8") as file:
        config = json.load(file)

    return (
        Path(config["game_dir"])
        / "data"
        / "db"
        / "client_db.dat"
    )


def status():
    target = get_client_db()

    print("=" * 72)
    print(" FM06 BRASIL 2026 - STATUS DO CLIENT_DB")
    print("=" * 72)
    print()

    if not target.exists():
        print("[ERRO] client_db.dat não encontrado.")
        return 1

    current_hash = sha256_file(target)

    print(f"Arquivo:")
    print(f"  {target}")
    print()

    print("SHA-256 atual:")
    print(f"  {current_hash}")
    print()

    if current_hash == EXPECTED_ORIGINAL_HASH:
        print("[ORIGINAL] Banco original 6.0.2 detectado.")

    elif current_hash == EXPECTED_PATCHED_HASH:
        print("[TESTE] Patch FLAMENGO detectado.")

    else:
        print("[DESCONHECIDO] O arquivo não corresponde")
        print("ao original nem ao nosso patch experimental.")

    print()

    if BACKUP_FILE.exists():
        print("[OK] Backup existente:")
        print(f"     {BACKUP_FILE}")

        backup_hash = sha256_file(BACKUP_FILE)

        if backup_hash == EXPECTED_ORIGINAL_HASH:
            print("[OK] Hash do backup original confirmado.")
        else:
            print("[ALERTA] Hash inesperado no backup.")
    else:
        print("[INFO] Backup ainda não criado.")

    return 0


def apply_patch():
    target = get_client_db()

    print("=" * 72)
    print(" FM06 BRASIL 2026 - APLICAR PATCH EXPERIMENTAL")
    print("=" * 72)
    print()

    if not target.exists():
        print("[ERRO] client_db.dat não encontrado.")
        return 1

    if not TEST_FILE.exists():
        print("[ERRO] Arquivo experimental não encontrado:")
        print(TEST_FILE)
        print()
        print("Execute primeiro:")
        print("python .\\scripts\\make_test_patch.py")
        return 1

    current_hash = sha256_file(target)

    if current_hash == EXPECTED_PATCHED_HASH:
        print("[INFO] O patch já está aplicado.")
        return 0

    if current_hash != EXPECTED_ORIGINAL_HASH:
        print("[ERRO] Recusando alteração.")
        print()
        print("O client_db.dat atual não possui o hash")
        print("original esperado.")
        print()
        print(f"Encontrado: {current_hash}")
        return 1

    test_hash = sha256_file(TEST_FILE)

    if test_hash != EXPECTED_PATCHED_HASH:
        print("[ERRO] O arquivo de teste possui hash inesperado.")
        print(test_hash)
        return 1

    BACKUP_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not BACKUP_FILE.exists():
        shutil.copy2(
            target,
            BACKUP_FILE,
        )

        backup_hash = sha256_file(BACKUP_FILE)

        if backup_hash != EXPECTED_ORIGINAL_HASH:
            print("[ERRO] Falha ao validar o backup.")
            return 1

        print("[OK] Backup original criado:")
        print(BACKUP_FILE)

    else:
        backup_hash = sha256_file(BACKUP_FILE)

        if backup_hash != EXPECTED_ORIGINAL_HASH:
            print("[ERRO] Backup existente possui hash incorreto.")
            print("Patch não será aplicado.")
            return 1

        print("[OK] Backup original já existente.")

    print()
    print("Aplicando arquivo experimental...")

    shutil.copy2(
        TEST_FILE,
        target,
    )

    installed_hash = sha256_file(target)

    if installed_hash != EXPECTED_PATCHED_HASH:
        print("[ERRO] Hash final inesperado.")
        print("Tentando restaurar o backup...")

        shutil.copy2(
            BACKUP_FILE,
            target,
        )

        return 1

    print()
    print("[OK] PATCH EXPERIMENTAL APLICADO.")
    print()
    print("Flamengo deverá aparecer como:")
    print()
    print("    FLAMENGO")
    print()
    print("Para restaurar depois:")
    print(
        "python .\\scripts\\test_client_patch.py restore"
    )

    return 0


def restore():
    target = get_client_db()

    print("=" * 72)
    print(" FM06 BRASIL 2026 - RESTAURAR CLIENT_DB")
    print("=" * 72)
    print()

    if not BACKUP_FILE.exists():
        print("[ERRO] Backup não encontrado:")
        print(BACKUP_FILE)
        return 1

    backup_hash = sha256_file(BACKUP_FILE)

    if backup_hash != EXPECTED_ORIGINAL_HASH:
        print("[ERRO] O backup não corresponde ao")
        print("client_db.dat original conhecido.")
        print()
        print("Restauração cancelada.")
        return 1

    shutil.copy2(
        BACKUP_FILE,
        target,
    )

    restored_hash = sha256_file(target)

    if restored_hash != EXPECTED_ORIGINAL_HASH:
        print("[ERRO] A restauração não foi validada.")
        return 1

    print("[OK] Banco original restaurado.")
    print()
    print("SHA-256:")
    print(restored_hash)

    return 0


def main():
    if len(sys.argv) < 2:
        print("Uso:")
        print()
        print(
            "  python scripts/test_client_patch.py status"
        )
        print(
            "  python scripts/test_client_patch.py apply"
        )
        print(
            "  python scripts/test_client_patch.py restore"
        )

        return 1

    command = sys.argv[1].lower()

    if command == "status":
        return status()

    if command == "apply":
        return apply_patch()

    if command == "restore":
        return restore()

    print(f"Comando desconhecido: {command}")
    return 1


if __name__ == "__main__":
    sys.exit(main())