"""Cria uma cópia do fm.exe com patches de regras. O original nunca é alterado.

    python scripts/patch_exe.py --list
    python scripts/patch_exe.py serie_a_rebaixa_4
    python scripts/patch_exe.py serie_a_rebaixa_4 serie_b_sobe_4 --out fm_teste.exe

A cópia é salva na pasta do jogo (precisa ficar lá para achar os dados).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch.exe_patches import EXE_SHA256, PATCHES, apply  # noqa: E402


def game_dir() -> Path:
    config = ROOT / "config" / "local.json"
    if not config.exists():
        config = ROOT / "config" / "local.example.json"
    return Path(json.loads(config.read_text(encoding="utf-8"))["game_dir"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("patches", nargs="*")
    parser.add_argument("--list", action="store_true", help="lista os patches disponíveis")
    parser.add_argument("--exe", type=Path, help="fm.exe original (padrão: pasta do jogo)")
    parser.add_argument("--out", default="fm_teste.exe", help="nome da cópia, na mesma pasta do original")
    args = parser.parse_args()

    if args.list or not args.patches:
        for patch in PATCHES.values():
            print(f"{patch.name:22} {patch.description}")
        return

    source = args.exe or game_dir() / "fm.exe"
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest().upper()
    if digest != EXE_SHA256:
        raise SystemExit(f"{source} não é o fm.exe 6.0.2 original (sha256 {digest}).")

    target = source.with_name(args.out)
    if target.resolve() == source.resolve():
        raise SystemExit("A saída não pode ser o próprio fm.exe.")
    target.write_bytes(apply(data, args.patches))
    print(f"Criado {target}")
    for name in args.patches:
        print(f"  + {name}: {PATCHES[name].description}")


if __name__ == "__main__":
    main()
