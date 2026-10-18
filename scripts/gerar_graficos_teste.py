"""Gera o pacote de teste de escudos e uniformes (data/brasil/graficos_teste).

Uso: python scripts/gerar_graficos_teste.py --escudos <pasta com os .svg/.png>
Os escudos têm o nome da coluna escudo_arquivo de clubes_master.xlsx.

Estilo 3D (escolhido no teste), escudo 60x60 (cabe no cabeçalho da skin).
Teste do tamanho do uniforme: Flamengo 120, Palmeiras 100, Corinthians 80, demais 100.
Teste do 3º uniforme (cores provisórias): Flamengo, Palmeiras, Fluminense.
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
KIT_SIZE = {"Flamengo": 120, "Palmeiras": 100, "Corinthians": 80}
THIRD = {   # provisório, só para ver se o jogo mostra o 3º uniforme
    "Flamengo": {"modelo": "lisa", "camisa": "#FFFFFF", "secundaria": "#D2232A", "detalhes": "#000000"},
    "Palmeiras": {"modelo": "lisa", "camisa": "#035F30", "secundaria": "#FFFFFF", "detalhes": "#D4AF37"},
    "Fluminense": {"modelo": "lisa", "camisa": "#FFFFFF", "secundaria": "#7A263A", "detalhes": "#00843D"},
}


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
        brand = {"patrocinador": row["patrocinador_master"], "fornecedor": row["fornecedor_2026"]}
        kit = {"home": dict(_kit(row, 1), **brand), "away": dict(_kit(row, 2), **brand)}
        if row["uni3_camisa"] or name in THIRD:
            kit["third"] = dict(_kit(row, 3) if row["uni3_camisa"] else THIRD[name], **brand)
        clubs.append({"uid": uid, "slug": _slug(name),
                      "escudo": crest.read_bytes() if crest and crest.exists() else None,
                      "kit_size": KIT_SIZE.get(name, 100), "kits": kit, "nome": name})
        if not clubs[-1]["escudo"]:
            print(f"[AVISO] sem escudo: {name}")
    shutil.rmtree(OUT / "data", ignore_errors=True)
    count = graficos.pacote(OUT, clubs)
    print(f"[OK] {count} imagens em {OUT / 'data'}")
    _preview(clubs)


def _preview(clubs: list[dict]) -> None:
    """previa.png: casa, fora e 3º de cada clube no tamanho real."""
    kits = OUT / "data" / "graphics" / "pictures" / "kits" / "clubs" / "bra2026"
    cell = 130
    sheet = Image.new("RGB", (cell * 7, (3 * cell + 20) * 2), (58, 68, 58))
    d = ImageDraw.Draw(sheet)
    for i, club in enumerate(clubs):
        x, y = (i % 7) * cell, (i // 7) * (3 * cell + 20)
        d.text((x + 6, y + 4), club["nome"], fill="white")
        for j, kind in enumerate(("home", "away", "third")):
            path = kits / f"{club['slug']}_{kind}.png"
            if path.exists():
                kit = Image.open(path)
                sheet.paste(kit, (x + 6, y + 18 + j * cell), kit)
    sheet.save(OUT / "previa.png")


if __name__ == "__main__":
    main()
