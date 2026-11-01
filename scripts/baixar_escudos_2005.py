"""Escudos dos clubes de 2005 que voltaram com a Fase 6 (os que eram substitutos, ficha C13).

    python scripts\\baixar_escudos_2005.py

Os clubes vêm da identidade_fm06.csv de antes da Fase 6 (git 3d70bfb, tipo "substituto": o
clube do FM06 que estava ocupado). Para cada um, procura o artigo na Wikipédia em português
pelo nome longo do FM06 ("Paraná Clube") e baixa a imagem principal do artigo (miniatura PNG de
256 px) em data/brasil/clubes/escudos_2005/<UID do jogo>.png. Grava a lista em
data/brasil/clubes/escudos_2005.csv (confira o artigo; apague a linha e o arquivo do que vier
errado). Rodar de novo só baixa o que falta. Depois: gerar_graficos.py.
"""

from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import server_teams  # noqa: E402
from fm06patch.estaduais_clubes import normalize  # noqa: E402

BEFORE = "3d70bfb"
SERVER = ROOT / "workspace" / "baseline" / "server_db.original.dat"
FILES = ROOT / "data" / "brasil" / "clubes" / "escudos_2005"
SHEET = ROOT / "data" / "brasil" / "clubes" / "escudos_2005.csv"
UA = "fm06-brasil-2026/1.0 (mod pessoal)"
NOT_CREST = ("bandeira", "flag", "mapa", "map", "brasao", "brasão", "estadio", "estádio", "location")


def get(url: str) -> bytes:
    for attempt in range(5):
        time.sleep(3 + 20 * attempt)
        done = subprocess.run(["curl", "-s", "-m", "30", "-A", UA, "-w", "\n%{http_code}", url], capture_output=True)
        body, _, code = done.stdout.rpartition(b"\n")
        if code == b"200":
            return body
        if code == b"404":
            return b""
    raise RuntimeError(f"HTTP {code.decode()} em {url}")


def api(**params) -> dict:
    query = urllib.parse.urlencode({**params, "format": "json"})
    return json.loads(get(f"https://pt.wikipedia.org/w/api.php?{query}") or b"{}")


def find(long_name: str, short: str) -> tuple[str, str]:
    """(artigo, link da miniatura do escudo) ou ("", "")."""
    wanted = set(normalize(short.split("(")[0]).split())
    found = api(action="query", generator="search", gsrsearch=f"{long_name} futebol", gsrlimit=4,
                prop="pageimages", piprop="thumbnail|name", pithumbsize=256)
    pages = sorted(found.get("query", {}).get("pages", {}).values(), key=lambda p: p["index"])
    for page in pages:
        image = page.get("pageimage", "")
        thumb = page.get("thumbnail", {}).get("source", "")
        title = normalize(page["title"])
        if thumb and wanted <= set(title.split()) and not any(w in image.lower() for w in NOT_CREST):
            return page["title"], thumb
    return "", ""


def main() -> None:
    server = SERVER.read_bytes()
    before = subprocess.run(["git", "show", f"{BEFORE}:data/brasil/clubes/identidade_fm06.csv"], cwd=ROOT,
                            capture_output=True, text=True, encoding="utf-8").stdout
    clubs = [r for r in csv.DictReader(io.StringIO(before.lstrip("﻿"))) if r["tipo"] == "substituto"]
    rows = {}
    if SHEET.exists():
        rows = {r["uid_jogo"]: r for r in csv.DictReader(SHEET.open(encoding="utf-8-sig"))}
    FILES.mkdir(parents=True, exist_ok=True)
    for club in clubs:
        uid, short = club["uid_jogo"], club["fm06_nome"]
        if uid in rows and (FILES / f"{uid}.png").exists():
            continue
        long_name = server_teams.club_names(server, int(club["uid_repo"]))[0] or short
        article, thumb = find(long_name, short)
        if thumb:
            data = get(thumb)
            Image.open(io.BytesIO(data)).verify()
            (FILES / f"{uid}.png").write_bytes(data)
        rows[uid] = {"uid_jogo": uid, "clube_fm06": short, "nome_longo": long_name, "artigo": article, "escudo_url": thumb}
        print(f"{short:28} {long_name:40} {article or '(não achado)'}", flush=True)
        with SHEET.open("w", newline="", encoding="utf-8-sig") as handle:      # grava a cada clube
            writer = csv.DictWriter(handle, fieldnames=["uid_jogo", "clube_fm06", "nome_longo", "artigo", "escudo_url"])
            writer.writeheader()
            writer.writerows(rows.values())
    got = sum(1 for r in rows.values() if r["escudo_url"])
    print(f"[OK] {got} de {len(rows)} escudos em {FILES}")


if __name__ == "__main__":
    main()
