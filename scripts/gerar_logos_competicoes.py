"""Logos das competições (Série A a D, Copa do Brasil, Libertadores, Sul-Americana, Copa do
Mundo e os estaduais) para data\\graphics do FM06.

Uso (na pasta do repositório):
    python scripts\\gerar_logos_competicoes.py               (gera com os logos já baixados)
    python scripts\\gerar_logos_competicoes.py --baixar      (baixa antes os que faltam)
    python scripts\\gerar_logos_competicoes.py --instalar    (e copia para a pasta do jogo)

Entrada: data/brasil/logos_competicoes.csv (chave, comp_uid, competição, arquivo e link da
Wikipédia; o link é a miniatura PNG de 256 px, que serve também para os SVG). Os arquivos baixados ficam em data/brasil/logos_competicoes/<chave>.<ext>; para
trocar um logo, ponha outro arquivo com o mesmo nome (PNG, JPG ou SVG) ou outro link na planilha.
Saída: data/brasil/graficos_2026/data/graphics/pictures/logos/comps/bra2026 (ficha C12).
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import graficos  # noqa: E402

SHEET = ROOT / "data" / "brasil" / "logos_competicoes.csv"
FILES = ROOT / "data" / "brasil" / "logos_competicoes"
OUT = ROOT / "data" / "brasil" / "graficos_2026"
PACK = Path("data") / "graphics" / "pictures" / "logos" / "comps" / "bra2026"
FORMATS = (".png", ".jpg", ".jpeg", ".svg")
USER_AGENT = "fm06-brasil-2026/1.0 (mod pessoal)"


def game_dir() -> Path:
    return Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"])


def local_file(key: str) -> Path | None:
    return next((FILES / f"{key}{ext}" for ext in FORMATS if (FILES / f"{key}{ext}").exists()), None)


def download(key: str, url: str) -> None:
    ext = Path(url.split("?")[0]).suffix.lower()
    ext = ".jpg" if ext == ".jpeg" else ext if ext in FORMATS else ".png"
    for attempt in range(4):                    # a Wikimedia barra rajadas (HTTP 429)
        time.sleep(4 + 15 * attempt)
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}),
                                          timeout=30).read()
            break
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 3:
                raise
    if ext != ".svg":
        Image.open(io.BytesIO(data)).verify()
    FILES.mkdir(parents=True, exist_ok=True)
    (FILES / f"{key}{ext}").write_bytes(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--baixar", action="store_true", help="baixa os logos que faltam")
    parser.add_argument("--instalar", action="store_true", help="copia o pacote para a pasta do jogo")
    args = parser.parse_args()

    comps = []
    for row in csv.DictReader(SHEET.open(encoding="utf-8-sig")):
        key, url = row["chave"], row["logo_url"].strip()
        if args.baixar and url and not local_file(key):
            try:
                download(key, url)
                print(f"[OK] baixado {key}")
            except Exception as error:                  # noqa: BLE001
                print(f"[FALHOU] {key}: {url} ({error})")
        path = local_file(key)
        if path is None:
            print(f"[SEM LOGO] {row['competicao']}")
            continue
        comps.append((int(row["comp_uid"]), key.lower(), path.read_bytes()))
    shutil.rmtree(OUT / PACK, ignore_errors=True)
    count = graficos.pacote_competicoes(OUT, comps)
    print(f"[OK] {count} imagens de {len(comps)} competições em {OUT / PACK}")
    if args.instalar:
        target = game_dir() / PACK
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(OUT / PACK, target)
        print(f"[OK] copiado para {target}")


if __name__ == "__main__":
    main()
