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

BACKUP_FILE = BASELINE_DIR / "server_db.original.dat"
PATCHED_FILE = WORKING_DIR / "server_db_test.dat"


EXPECTED_ORIGINAL_HASH = (
    "9FB7A4A2B87798120BF4D9DA9E86E7D"
    "ABB99C668802B2FB9ECB035230F66BE62"
)


PATCHES = [
    {
        "offset": 0xCA574,
        "original": "CR Flamengo",
        "replacement": "CR FLAMENGO",
    },
    {
        "offset": 0xCA590,
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


def get_server_db() -> Path:
    with CONFIG_FILE.open("r", encoding="utf-8") as file:
        config = json.load(file)

    return (
        Path(config["game_dir"])
        / "data"
        / "db"
        / "server_db.dat"
    )


def verify_offsets(path: Path, patched: bool = False) -> bool:
    with path.open("rb") as file:

        for patch in PATCHES:
            expected_text = (
                patch["replacement"]
                if patched
                else patch["original"]
            )

            expected = expected_text.encode("utf-16le")

            file.seek(patch["offset"])
            found = file.read(len(expected))

            if found != expected:
                print()
                print(
                    f"[ERRO] Offset 0x{patch['offset']:X}"
                )
                print(f"Esperado: {expected_text!r}")
                print(
                    "Bytes esperados:",
                    expected.hex(" ").upper(),
                )
                print(
                    "Bytes encontrados:",
                    found.hex(" ").upper(),
                )

                return False

    return True


def build_test_file() -> str:
    target = get_server_db()

    WORKING_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    original_hash = sha256_file(target)

    if original_hash != EXPECTED_ORIGINAL_HASH:
        raise RuntimeError(
            "server_db.dat não corresponde ao baseline original."
        )

    if not verify_offsets(target, patched=False):
        raise RuntimeError(
            "Os offsets esperados não correspondem aos textos."
        )

    shutil.copy2(
        target,
        PATCHED_FILE,
    )

    with PATCHED_FILE.open("r+b") as file:

        for patch in PATCHES:
            original = patch["original"].encode("utf-16le")
            replacement = patch["replacement"].encode("utf-16le")

            if len(original) != len(replacement):
                raise RuntimeError(
                    "Patch altera o tamanho da string."
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

    if PATCHED_FILE.stat().st_size != target.stat().st_size:
        raise RuntimeError(
            "O tamanho do arquivo modificado mudou."
        )

    if not verify_offsets(
        PATCHED_FILE,
        patched=True,
    ):
        raise RuntimeError(
            "Falha ao validar a cópia modificada."
        )

    return sha256_file(PATCHED_FILE)


def status() -> int:
    target = get_server_db()

    print("=" * 72)
    print(" FM06 BRASIL 2026 - STATUS DO SERVER_DB")
    print("=" * 72)
    print()

    if not target.exists():
        print("[ERRO] server_db.dat não encontrado.")
        return 1

    current_hash = sha256_file(target)

    print("Arquivo:")
    print(f"  {target}")
    print()

    print("SHA-256 atual:")
    print(f"  {current_hash}")
    print()

    if current_hash == EXPECTED_ORIGINAL_HASH:
        print("[ORIGINAL] server_db.dat original detectado.")

    elif verify_offsets(target, patched=True):
        print("[TESTE] Patch FLAMENGO detectado.")

    else:
        print("[DESCONHECIDO] server_db.dat possui")
        print("um estado que não reconhecemos.")

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
    target = get_server_db()

    print("=" * 72)
    print(" FM06 BRASIL 2026 - TESTE NO SERVER_DB")
    print("=" * 72)
    print()

    if not target.exists():
        print("[ERRO] server_db.dat não encontrado.")
        return 1

    current_hash = sha256_file(target)

    if current_hash != EXPECTED_ORIGINAL_HASH:

        if verify_offsets(target, patched=True):
            print("[INFO] Patch de teste já está aplicado.")
            return 0

        print("[ERRO] server_db.dat não corresponde")
        print("ao arquivo original conhecido.")
        print()
        print("Patch cancelado.")
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

        if (
            sha256_file(BACKUP_FILE)
            != EXPECTED_ORIGINAL_HASH
        ):
            print("[ERRO] Falha ao validar backup.")
            return 1

        print("[OK] Backup original criado:")
        print(BACKUP_FILE)

    else:

        if (
            sha256_file(BACKUP_FILE)
            != EXPECTED_ORIGINAL_HASH
        ):
            print("[ERRO] Backup existente inválido.")
            return 1

        print("[OK] Backup original já existente.")

    print()
    print("Criando cópia experimental...")

    patched_hash = build_test_file()

    print()
    print("[OK] Cópia experimental criada:")
    print(PATCHED_FILE)

    print()
    print("SHA-256 experimental:")
    print(patched_hash)

    print()
    print("Aplicando no jogo...")

    shutil.copy2(
        PATCHED_FILE,
        target,
    )

    if not verify_offsets(target, patched=True):
        print("[ERRO] Validação do arquivo instalado falhou.")
        print("Restaurando original...")

        shutil.copy2(
            BACKUP_FILE,
            target,
        )

        return 1

    installed_hash = sha256_file(target)

    print()
    print("[OK] Patch experimental aplicado.")
    print()
    print("SHA-256 instalado:")
    print(installed_hash)

    print()
    print("Os textos de teste são:")
    print()
    print("    CR FLAMENGO")
    print("    FLAMENGO")
    print()
    print("Para restaurar:")
    print(
        "python .\\scripts\\test_server_patch.py restore"
    )

    return 0


def restore() -> int:
    target = get_server_db()

    print("=" * 72)
    print(" FM06 BRASIL 2026 - RESTAURAR SERVER_DB")
    print("=" * 72)
    print()

    if not BACKUP_FILE.exists():
        print("[ERRO] Backup não encontrado.")
        return 1

    backup_hash = sha256_file(BACKUP_FILE)

    if backup_hash != EXPECTED_ORIGINAL_HASH:
        print("[ERRO] Backup possui hash inesperado.")
        print("Restauração cancelada.")
        return 1

    shutil.copy2(
        BACKUP_FILE,
        target,
    )

    restored_hash = sha256_file(target)

    if restored_hash != EXPECTED_ORIGINAL_HASH:
        print("[ERRO] Falha na validação da restauração.")
        return 1

    print("[OK] server_db.dat original restaurado.")
    print()
    print("SHA-256:")
    print(restored_hash)

    return 0


def main() -> int:

    if len(sys.argv) != 2:
        print("Uso:")
        print()
        print(
            "python scripts/test_server_patch.py status"
        )
        print(
            "python scripts/test_server_patch.py apply"
        )
        print(
            "python scripts/test_server_patch.py restore"
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