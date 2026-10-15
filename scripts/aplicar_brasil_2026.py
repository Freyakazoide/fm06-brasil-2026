"""Aplica a estrutura do futebol brasileiro de 2026 (Séries A, B, C e D).

    python scripts\\aplicar_brasil_2026.py            (simulação: mostra o que faria)
    python scripts\\aplicar_brasil_2026.py --apply    (grava tudo)
    python scripts\\aplicar_brasil_2026.py --restore  (volta o banco original e tira o .lnc)

Com --apply:
1. cria fm_brasil.exe na pasta do jogo (cópia do fm.exe com os patches das séries);
2. grava o server_db.dat do jogo com os clubes de cada série, partindo sempre
   do original (cópia em workspace\\baseline\\server_db.original.dat);
3. grava data\\db\\lnc\\all\\brasil_2026.lnc com os nomes Série A, B, C e D;
4. atualiza data\\brasil\\mapa_2026.csv (quem entrou no lugar de quem).

Depois é só abrir o fm_brasil.exe e começar um New Game.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch.brasil_2026 import SERIES, apply as apply_db, lnc_text, plan, write_report  # noqa: E402
from fm06patch.exe_patches import EXE_SHA256, PATCHES, apply as apply_exe  # noqa: E402

EXE_PATCHES = [
    "serie_a_calendario_copa",
    "serie_a_rebaixa_4",
    "serie_b_datas_2026",
    "serie_b_playoffs",
    "serie_b_rebaixa_4",
    "serie_c_nova",
    "serie_d_96",
    "virada_1_janeiro",
    "estaduais_2026",
]
SERVER_SHA256 = "9FB7A4A2B87798120BF4D9DA9E86E7DABB99C668802B2FB9ECB035230F66BE62"
BACKUP = ROOT / "workspace" / "baseline" / "server_db.original.dat"
DATA_DIR = ROOT / "data" / "brasil"


def game_dir() -> Path:
    config = ROOT / "config" / "local.json"
    return Path(json.loads(config.read_text(encoding="utf-8"))["game_dir"])


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def original_server_db(path: Path) -> bytes:
    if BACKUP.exists():
        return BACKUP.read_bytes()
    data = path.read_bytes()
    if sha256(data) != SERVER_SHA256:
        sys.exit("[ERRO] o server_db.dat do jogo não é o original e não há cópia em workspace\\baseline.")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--restore", action="store_true")
    parser.add_argument("--teste-copa", type=int, choices=(1, 2),
                        help="troca as datas da Série A pelo teste de pausa da Copa (exp_a_copa_1 ou _2)")
    args = parser.parse_args()
    patches = list(EXE_PATCHES)
    if args.teste_copa:
        patches[patches.index("serie_a_calendario_copa")] = f"exp_a_copa_{args.teste_copa}"

    game = game_dir()
    server = game / "data" / "db" / "server_db.dat"
    lnc = game / "data" / "db" / "lnc" / "all" / "brasil_2026.lnc"

    if args.restore:
        if BACKUP.exists():
            shutil.copy2(BACKUP, server)
            print(f"[OK] banco original restaurado em {server}")
        if lnc.exists():
            lnc.unlink()
            print(f"[OK] removido {lnc}")
        return

    data = original_server_db(server)
    placements = plan(data, DATA_DIR)
    counts = Counter(p.serie for p in placements)
    kinds = Counter(p.kind for p in placements)
    print("Clubes por série:", {s: counts[s] for s in SERIES},
          f"({kinds['equivalente']} equivalentes, {kinds['substituto']} substitutos)")
    print("\nSubstitutos (clube de 2026 -> clube do FM06):")
    for p in placements:
        if p.kind == "substituto":
            print(f"  Série {p.serie}: {p.clube or '(vaga extra)':24} -> {p.team.short_name}")

    if not args.apply:
        print("\nSimulação. Para gravar, rode de novo com --apply no fim.")
        return

    exe = game / "fm.exe"
    exe_data = exe.read_bytes()
    if sha256(exe_data) != EXE_SHA256:
        sys.exit(f"[ERRO] {exe} não é o fm.exe 6.0.2 original.")
    target = game / "fm_brasil.exe"
    target.write_bytes(apply_exe(exe_data, patches))
    print(f"\n[OK] criado {target}")
    for name in patches:
        print(f"     + {name}")

    if not BACKUP.exists():
        BACKUP.parent.mkdir(parents=True, exist_ok=True)
        BACKUP.write_bytes(data)
        print(f"[OK] cópia do banco original em {BACKUP}")
    server.write_bytes(apply_db(data, placements))
    print(f"[OK] gravado {server}")

    lnc.parent.mkdir(parents=True, exist_ok=True)
    lnc.write_bytes(lnc_text().encode("utf-16"))
    print(f"[OK] gravado {lnc}")

    write_report(DATA_DIR / "mapa_2026.csv", placements)
    print(f"[OK] lista completa em {DATA_DIR / 'mapa_2026.csv'}")


if __name__ == "__main__":
    main()
