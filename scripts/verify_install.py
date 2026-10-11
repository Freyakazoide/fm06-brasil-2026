from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

LOCAL_CONFIG = PROJECT_ROOT / "config" / "local.json"
SUPPORTED_BUILDS = PROJECT_ROOT / "config" / "supported_builds.json"

BASELINE_DIR = PROJECT_ROOT / "workspace" / "baseline"
FINGERPRINT_FILE = BASELINE_DIR / "install_fingerprint.json"


REQUIRED_DATABASE_FILES = [
    Path("data/db/server_db.dat"),
    Path("data/db/people_db.dat"),
    Path("data/db/client_db.dat"),
    Path("data/db/lang_db.dat"),
    Path("data/db/pl_hist_dt.dat"),
    Path("data/db/pl_hist_id.dat"),
    Path("data/db/pl_hist_index.dat"),
]


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    sha256 = hashlib.sha256()

    with path.open("rb") as file:
        while chunk := file.read(chunk_size):
            sha256.update(chunk)

    return sha256.hexdigest().upper()


def format_size(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size)

    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.2f} {unit}"

        value /= 1024

    return f"{size} B"


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def find_supported_build(exe_hash: str, supported_builds: dict):
    for build_id, build_data in supported_builds.items():
        expected_hash = build_data.get("sha256", "").upper()

        if exe_hash.upper() == expected_hash:
            return build_id, build_data

    return None, None


def main() -> int:
    print("=" * 70)
    print(" FM06 BRASIL 2026 - VERIFICACAO DA INSTALACAO")
    print("=" * 70)
    print()

    try:
        local_config = load_json(LOCAL_CONFIG)
        supported_builds = load_json(SUPPORTED_BUILDS)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        print(f"[ERRO] Falha ao carregar configuracao:")
        print(f"       {error}")
        return 1

    game_dir = Path(local_config["game_dir"])
    exe_name = local_config.get("exe", "fm.exe")
    exe_path = game_dir / exe_name

    print(f"Pasta configurada:")
    print(f"  {game_dir}")
    print()

    if not game_dir.exists():
        print("[ERRO] Pasta do Football Manager 2006 nao encontrada.")
        return 1

    print("[OK] Pasta do jogo encontrada.")

    if not exe_path.exists():
        print(f"[ERRO] Executavel nao encontrado: {exe_path}")
        return 1

    print(f"[OK] Executavel encontrado: {exe_name}")

    print()
    print("Calculando SHA-256 do executavel...")

    exe_hash = sha256_file(exe_path)
    exe_size = exe_path.stat().st_size

    print(f"[OK] SHA-256:")
    print(f"     {exe_hash}")
    print(f"[OK] Tamanho:")
    print(f"     {format_size(exe_size)} ({exe_size:,} bytes)")

    build_id, build_data = find_supported_build(
        exe_hash,
        supported_builds,
    )

    print()

    if build_data is None:
        print("[ERRO] Esta versao do fm.exe nao esta cadastrada.")
        print()
        print("Hash encontrado:")
        print(exe_hash)
        return 1

    print("[OK] Build reconhecida:")
    print(f"     ID: {build_id}")
    print(f"     Nome: {build_data.get('name')}")
    print(f"     File Version: {build_data.get('file_version')}")
    print(f"     Product Version: {build_data.get('product_version')}")

    print()
    print("-" * 70)
    print(" BANCO DE DADOS")
    print("-" * 70)

    database_fingerprints = {}
    missing_files = []

    for relative_path in REQUIRED_DATABASE_FILES:
        absolute_path = game_dir / relative_path

        if not absolute_path.exists():
            missing_files.append(str(relative_path))
            print(f"[FALTA] {relative_path}")
            continue

        size = absolute_path.stat().st_size
        file_hash = sha256_file(absolute_path)

        database_fingerprints[str(relative_path).replace("\\", "/")] = {
            "size": size,
            "sha256": file_hash,
        }

        print(
            f"[OK] {relative_path} "
            f"- {format_size(size)}"
        )

    print()

    if missing_files:
        print("[ERRO] Existem arquivos obrigatorios ausentes.")
        print()

        for item in missing_files:
            print(f"       {item}")

        return 1

    BASELINE_DIR.mkdir(parents=True, exist_ok=True)

    fingerprint = {
        "created_at": datetime.now().astimezone().isoformat(),
        "game_dir": str(game_dir),
        "build": {
            "id": build_id,
            "name": build_data.get("name"),
            "file_version": build_data.get("file_version"),
            "product_version": build_data.get("product_version"),
        },
        "executable": {
            "path": exe_name,
            "size": exe_size,
            "sha256": exe_hash,
        },
        "database": database_fingerprints,
    }

    with FINGERPRINT_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            fingerprint,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print("-" * 70)
    print("[OK] Todos os arquivos essenciais foram encontrados.")
    print()
    print("[OK] Fingerprint original salvo em:")
    print(f"     {FINGERPRINT_FILE}")
    print()
    print("=" * 70)
    print(" AMBIENTE PRONTO PARA ENGENHARIA REVERSA")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())