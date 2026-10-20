"""Telas do FM06 em português do Brasil (data/languages/portuguese.ltc).

    python scripts\\traduzir_telas.py            (simulação: quantos textos mudam)
    python scripts\\traduzir_telas.py --apply    (grava; o jogo tem de estar fechado)
    python scripts\\traduzir_telas.py --restore  (volta o original)

Usa o glossário e as frases de data/modelos/traducao_ptbr.xlsx com as regras das telas
(src/fm06patch/traducao.py: "equipa" vira "equipe", "médio" só nas posições...). Parte
sempre do original (cópia em workspace/baseline/portuguese.ltc.original), apaga o cache
do skin (data/cache/portuguese, o jogo refaz) e grava a lista do que mudou em
data/brasil/traducao_telas.csv. Vale também para um jogo salvo: o jogo lê o .ltc ao abrir.
O aplicar_brasil_2026.py --apply também roda esta tradução.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import traducao  # noqa: E402

LTC_SHA256 = "D7380636B252E48121D49057ADAC3A43B2ECFB3D0AC1A811E70EF572430F276F"   # 6.0.2
BACKUP = ROOT / "workspace" / "baseline" / "portuguese.ltc.original"
SHEET = ROOT / "data" / "modelos" / "traducao_ptbr.xlsx"
REPORT = ROOT / "data" / "brasil" / "traducao_telas.csv"


def game_dir() -> Path:
    return Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"])


def original(path: Path) -> bytes | None:
    if BACKUP.exists():
        return BACKUP.read_bytes()
    if not path.exists():
        print(f"[AVISO] {path} não existe: telas não traduzidas.")
        return None
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest().upper() != LTC_SHA256:
        print("[AVISO] o portuguese.ltc do jogo não é o original e não há cópia em workspace\\baseline: "
              "telas não traduzidas.")
        return None
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    BACKUP.write_bytes(data)
    print(f"[OK] cópia do portuguese.ltc original em {BACKUP}")
    return data


def clear_cache(game: Path) -> None:
    cache = game / "data" / "cache" / "portuguese"
    if cache.exists():
        shutil.rmtree(cache)
        print(f"[OK] cache do skin apagado ({cache}); o jogo refaz ao abrir")


def translate(game: Path, apply: bool) -> None:
    path = game / "data" / "languages" / "portuguese.ltc"
    data = original(path)
    if data is None or not SHEET.exists():
        return
    sheet = traducao.load_sheet(SHEET)
    changes, too_long = traducao.plan_screens(data, sheet.glossary(traducao.SCREENS), sheet.phrases,
                                              sheet.short_phrases)
    print(f"[OK] telas: {len(changes)} textos em pt-BR ({len(too_long)} ficam como estão porque a tradução "
          f"não cabe; lista em {REPORT.relative_to(ROOT)})")
    if not apply:
        return
    path.write_bytes(traducao.apply(data, changes))
    clear_cache(game)
    with REPORT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["antes", "depois"])
        writer.writerows(sorted({(c.old, c.new) for c in changes}))
        writer.writerows([(line, "NÃO COUBE") for line in too_long])
    print(f"[OK] gravado {path}")


def restore(game: Path) -> None:
    if BACKUP.exists():
        shutil.copy2(BACKUP, game / "data" / "languages" / "portuguese.ltc")
        clear_cache(game)
        print("[OK] portuguese.ltc original restaurado")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    game = game_dir()
    if args.restore:
        restore(game)
        return
    translate(game, args.apply)
    if not args.apply:
        print("\nSimulação. Para gravar, feche o jogo e rode de novo com --apply.")


if __name__ == "__main__":
    main()
