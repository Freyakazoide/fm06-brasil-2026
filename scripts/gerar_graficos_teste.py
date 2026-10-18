"""Gera o pacote de teste de escudos e uniformes (data/brasil/graficos_teste).

Uso: python scripts/gerar_graficos_teste.py --escudos <pasta com os .svg/.png>
Os escudos têm o nome da coluna escudo_arquivo de clubes_master.xlsx.

Teste de estilo: uniforme de casa em 3D (com escudo, fornecedor e patrocínio),
de fora em pixel art. Teste do tamanho do escudo no cabeçalho da skin:
Palmeiras 60x60 e Fluminense 90x90; os demais 120x120.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import unicodedata
from pathlib import Path

import openpyxl
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import graficos  # noqa: E402

CLUBES = ROOT / "data" / "brasil" / "clubes"
OUT = ROOT / "data" / "brasil" / "graficos_teste"

# clube (como em uniformes_2026.xlsx) -> UID do jogo (CLUB+0x14)
TESTE = {
    "Flamengo": 322, "Palmeiras": 329, "Cruzeiro": 321, "Fluminense": 323, "Botafogo": 316,
    "Vasco da Gama": 339, "São Paulo": 337, "Corinthians": 319, "Santos": 335, "Grêmio": 324,
    "Internacional": 326, "Atlético-MG": 314, "Bahia": 315, "Sport": 338,
}
LOGO_SIZE = {"Palmeiras": (60, 60), "Fluminense": (90, 90)}


def _sheet(path: Path) -> dict[str, dict]:
    sheet = openpyxl.load_workbook(path, read_only=True).worksheets[0]
    rows = sheet.iter_rows(values_only=True)
    header = next(rows)
    return {row[header.index("clube")]: dict(zip(header, row)) for row in rows if row[header.index("clube")]}


def _slug(name: str) -> str:
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", plain.lower()).strip("_")


def _kit(row: dict, n: int) -> dict:
    model = row[f"uni{n}_modelo"] or "lisa"
    return {"modelo": "lisa" if model.startswith("outro") else model, "camisa": row[f"uni{n}_camisa"],
            "secundaria": row[f"uni{n}_secundaria"], "detalhes": row[f"uni{n}_detalhes"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--escudos", type=Path, required=True)
    args = parser.parse_args()
    kits = _sheet(CLUBES / "uniformes_2026.xlsx")
    master = _sheet(CLUBES / "clubes_master.xlsx")
    clubs = []
    for name, uid in TESTE.items():
        row = kits[name]
        crest_file = (master.get(name) or {}).get("escudo_arquivo")
        crest = args.escudos / crest_file if crest_file else None
        home = dict(_kit(row, 1), estilo="3d", patrocinador=row["patrocinador_master"],
                    fornecedor=row["fornecedor_2026"])
        away = dict(_kit(row, 2), estilo="pixel", fornecedor=row["fornecedor_2026"])
        clubs.append({"uid": uid, "slug": _slug(name),
                      "escudo": crest.read_bytes() if crest and crest.exists() else None,
                      "logo_size": LOGO_SIZE.get(name, graficos.SIZES["logo"]),
                      "kits": {"home": home, "away": away}, "nome": name})
        if not clubs[-1]["escudo"]:
            print(f"[AVISO] sem escudo: {name}")
    shutil.rmtree(OUT / "data", ignore_errors=True)
    count = graficos.pacote(OUT, clubs)
    print(f"[OK] {count} imagens em {OUT / 'data'}")
    _preview(clubs)


def _preview(clubs: list[dict]) -> None:
    """previa.png: casa e fora de cada clube no tamanho real e em 2x."""
    kits = OUT / "data" / "graphics" / "pictures" / "kits" / "clubs" / "bra2026"
    cell = 2 * graficos.KIT_SIZE + 12
    sheet = Image.new("RGB", (cell * 7, (2 * cell + 20) * 2), (58, 68, 58))
    d = ImageDraw.Draw(sheet)
    for i, club in enumerate(clubs):
        x, y = (i % 7) * cell, (i // 7) * (2 * cell + 20)
        d.text((x + 6, y + 4), club["nome"], fill="white")
        for j, kind in enumerate(("home", "away")):
            path = kits / f"{club['slug']}_{kind}.png"
            if path.exists():
                kit = Image.open(path).resize((2 * graficos.KIT_SIZE,) * 2, Image.NEAREST)
                sheet.paste(kit, (x + 6, y + 18 + j * cell), kit)
    sheet.save(OUT / "previa.png")


if __name__ == "__main__":
    main()
