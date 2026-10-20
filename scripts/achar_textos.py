"""Procura na pasta do jogo o arquivo com as frases das telas.

    python scripts\\achar_textos.py

As frases das telas ("Utilizado num sistema de rotatividade do plantel", "Tácticas")
não ficam no lang_db.dat. Este script procura essas frases em todos os arquivos da
pasta do jogo (UTF-16, UTF-8 e Windows-1252) e lista os arquivos grandes de texto ou
idioma, para achar onde a tradução das telas tem de entrar. Mande a saída inteira.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHRASES = ["rotatividade do plantel", "Tácticas", "Selecção", "prémio de presença", "Remunerações",
           "Informação de Transferência", "Continuar"]
ENCODINGS = ("utf-16-le", "utf-8", "cp1252")
SKIP_DIRS = {"graphics", "pictures", "sound", "sounds", "movies"}


def main() -> None:
    game = Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"])
    print(f"Pasta do jogo: {game}\n")
    files = [p for p in game.rglob("*") if p.is_file() and not SKIP_DIRS & {x.lower() for x in p.parts}]
    print("Arquivos maiores que 200 KB (fora de graphics):")
    for path in sorted(files, key=lambda p: -p.stat().st_size):
        if path.stat().st_size > 200_000:
            print(f"  {path.stat().st_size // 1024:8} KB  {path.relative_to(game)}")
    print("\nFrases encontradas:")
    found = False
    for path in files:
        if path.stat().st_size > 300_000_000:
            continue
        data = path.read_bytes()
        for phrase in PHRASES:
            for encoding in ENCODINGS:
                count = data.count(phrase.encode(encoding))
                if count:
                    found = True
                    print(f"  {path.relative_to(game)}: '{phrase}' ({encoding}) x{count}")
    if not found:
        print("  nenhuma (o arquivo das telas deve estar comprimido; a lista acima ajuda a achar)")


if __name__ == "__main__":
    main()
