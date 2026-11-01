"""Comissão técnica de 2026 (além do técnico) dos clubes da CONMEBOL de data/estrangeiros.

    python scripts/coletar_comissao_estrangeiros.py [--wiki workspace/wiki]

- Artigo do clube na Wikipédia em inglês: o da data/estrangeiros/artigos_wiki_estrangeiros.csv;
  o clube que não está lá é procurado pela busca da Wikipédia ("<clube> football club <país>")
  e entra na planilha (confira e corrija à mão o que vier errado; vazio = sem artigo).
- Comissão: a tabela "Current coaching staff" / "Technical staff" do artigo, como no
  coletar_comissao.py (tabela comum ou o modelo {{Fb cs header}}). O técnico fica o da
  tecnicos_estrangeiros_2026.csv; daqui saem auxiliares, preparadores, analistas, médicos e
  olheiros.
- Muitas tabelas são de temporadas passadas. A do clube só entra se o técnico dela é o de
  2026 da tecnicos_estrangeiros_2026.csv, ou, sem técnico na tabela, se ela diz que foi
  atualizada em 2026. Quem aparece em mais de um clube fica de fora.

Grava data/estrangeiros/comissao_estrangeiros_2026.csv. Depois: scripts/aplicar_comissao.py.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from coletar_comissao import staff_rows  # noqa: E402
from coletar_historico import UA, Wiki  # noqa: E402
from fm06patch import comissao, estrangeiros  # noqa: E402
from fm06patch.estaduais_clubes import normalize  # noqa: E402

ARTICLES = estrangeiros.DATA / "artigos_wiki_estrangeiros.csv"
OUT = estrangeiros.DATA / "comissao_estrangeiros_2026.csv"
FIELDS = ["clube_2026", "pais", "cargo", "funcao", "nome", "nacionalidade", "nascimento", "fonte", "atualizado"]
COUNTRY = {"AR": "Argentina", "UY": "Uruguay", "CO": "Colombia", "PY": "Paraguay", "EC": "Ecuador",
           "CL": "Chile", "PE": "Peru", "BO": "Bolivia", "VE": "Venezuela"}
FLAG = {"SPA": "ESP", "CHL": "CHI", "URY": "URU", "PRY": "PAR"}
EMPTY = re.compile(r"(?i)^(tba|tbd|vacant|n/?a|-|—)$")


def search(term: str) -> list[str]:
    url = ("https://en.wikipedia.org/w/api.php?action=query&list=search&format=json&srlimit=3&srsearch="
           + urllib.parse.quote(term))
    for attempt in range(5):
        time.sleep(3)
        done = subprocess.run(["curl", "-s", "-m", "30", "-A", UA, url], capture_output=True)
        try:
            return [hit["title"] for hit in json.loads(done.stdout)["query"]["search"]]
        except (ValueError, KeyError):
            time.sleep(30 * (attempt + 1))                  # 429: a Wikipédia pede calma
    return []


def find_article(wiki: Wiki, club: str, alpha2: str) -> str:
    name = re.sub(r"\s*\([A-Z]{3}\)$", "", club)
    for title in search(f"{name} football club {COUNTRY[alpha2]}"):
        text = wiki.raw(title)
        if re.search(r"(?i)\{\{\s*Infobox football club", text) and COUNTRY[alpha2] in text:
            return title
    return ""


def same_person(a: str, b: str) -> bool:
    """Mesmo nome, ou um contido no outro ("Gustavo Costas" e "Gustavo Adolfo Costas")."""
    wa, wb = set(normalize(a).split()), set(normalize(b).split())
    return bool(wa and wb) and (wa <= wb or wb <= wa)


def nation(flag: str, alpha2: str) -> str:
    flag = FLAG.get(flag.upper(), flag.upper())
    return flag if comissao.nation_code(flag) else estrangeiros.NATIONS[alpha2][1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wiki", type=Path, default=ROOT / "workspace" / "wiki")
    args = parser.parse_args()
    wiki = Wiki(args.wiki)
    clubs = [(r["clube_2026"], r["pais"]) for r in csv.DictReader(estrangeiros.IDENTITIES.open(encoding="utf-8-sig"))
             if r["pais"] in COUNTRY]
    articles = {}
    if ARTICLES.exists():
        articles = {r["clube_2026"]: r["artigo"] for r in csv.DictReader(ARTICLES.open(encoding="utf-8-sig"))}
    for club, alpha2 in clubs:
        if club not in articles:
            articles[club] = find_article(wiki, club, alpha2)
            print(f"{club}: {articles[club] or '(sem artigo)'}", flush=True)
            with ARTICLES.open("w", newline="", encoding="utf-8-sig") as handle:   # grava a cada clube
                writer = csv.writer(handle)
                writer.writerow(["clube_2026", "artigo"])
                writer.writerows((c, articles.get(c, "")) for c, _ in clubs if c in articles)

    coach = {r["clube_2026"]: r["nome"] for r in csv.DictReader(estrangeiros.COACHES.open(encoding="utf-8-sig"))
             if r["cargo"] in ("", "tecnico")}
    rows, without, stale = [], [], []
    for club, alpha2 in clubs:
        staff, updated = staff_rows(wiki.raw(articles[club])) if articles[club] else ([], "")
        bosses = [s[2] for s in staff if s[0] == "tecnico"]
        current = (any(same_person(b, coach.get(club, "")) for b in bosses) if bosses
                   else bool(re.search(r"2026", updated)))
        if staff and not current:
            stale.append(f"{club} (tabela: {', '.join(bosses) or 'sem técnico'}, {updated or 'sem data'}; "
                         f"2026: {coach.get(club, '?')})")
            staff = []
        staff = [s for s in staff if s[0] != "tecnico" and not EMPTY.match(s[2])]
        for cargo, funcao, nome, flag in staff:
            rows.append({"clube_2026": club, "pais": alpha2, "cargo": cargo, "funcao": funcao, "nome": nome,
                         "nacionalidade": nation(flag, alpha2), "nascimento": "",
                         "fonte": f"Wikipédia: {articles[club]}", "atualizado": updated})
        if not staff:
            without.append(club)
    clubs_of: dict[str, set[str]] = {}
    for row in rows:
        clubs_of.setdefault(normalize(row["nome"]), set()).add(row["clube_2026"])
    twice = sorted({row["nome"] for row in rows if len(clubs_of[normalize(row["nome"])]) > 1})
    rows = [row for row in rows if len(clubs_of[normalize(row["nome"])]) == 1]
    for line in stale:
        print("[VELHA]", line)
    if twice:
        print("[FORA] em mais de um clube:", ", ".join(twice))
    with OUT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[OK] {len(rows)} membros de comissão de {len(clubs) - len(without)} clubes em {OUT}")
    print(f"[INFO] {len(without)} clubes sem tabela de 2026 na Wikipédia (fica a do FM06), {len(stale)} com tabela velha")


if __name__ == "__main__":
    main()
