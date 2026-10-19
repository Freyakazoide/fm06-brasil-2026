"""Campeões e vices reais (até 2025) das competições brasileiras e da CONMEBOL.

    python scripts/coletar_historico.py [--cache workspace/wiki]

Lê as tabelas de campeões da Wikipédia em inglês (wikitexto, um pedido a cada
2,5 s, guardado no cache) e grava data/brasil/historico/campeoes.csv:
Séries A (lista unificada da CBF, desde 1959, e a Copa dos Campeões de 1937), B, C
e D, Libertadores, Sul-Americana e os 27 estaduais. A Copa do Brasil vem da lista
abaixo (a página da Wikipédia tem as finais em ida e volta, difíceis de ler).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import wikitables  # noqa: E402

OUT = ROOT / "data" / "brasil" / "historico" / "campeoes.csv"
LAST_YEAR = 2025
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

NATIONAL = {
    "A": ("List of Brazilian football champions", None),
    "B": ("Campeonato Brasileiro Série B", "==Champions of Série B=="),
    "C": ("Campeonato Brasileiro Série C", "==Champions=="),
    "D": ("Campeonato Brasileiro Série D", "==List of champions=="),
    "LIB": ("List of Copa Libertadores finals", "==List of finals=="),
    "SULA": ("List of Copa Sudamericana finals", "==List of finals=="),
}
STATES = {
    "SP": "Campeonato Paulista", "RJ": "Campeonato Carioca", "MG": "Campeonato Mineiro",
    "RS": "Campeonato Gaúcho", "PR": "Campeonato Paranaense", "SC": "Campeonato Catarinense",
    "BA": "Campeonato Baiano", "PE": "Campeonato Pernambucano", "CE": "Campeonato Cearense",
    "GO": "Campeonato Goiano", "PA": "Campeonato Paraense", "AM": "Campeonato Amazonense",
    "MA": "Campeonato Maranhense", "PI": "Campeonato Piauiense", "RN": "Campeonato Potiguar",
    "PB": "Campeonato Paraibano", "AL": "Campeonato Alagoano", "SE": "Campeonato Sergipano",
    "ES": "Campeonato Capixaba", "MT": "Campeonato Mato-Grossense", "MS": "Campeonato Sul-Mato-Grossense",
    "DF": "Campeonato Brasiliense", "TO": "Campeonato Tocantinense", "RO": "Campeonato Rondoniense",
    "AC": "Campeonato Acreano", "RR": "Campeonato Roraimense", "AP": "Campeonato Amapaense",
}
# anos sem edição oficial que aparecem nas tabelas (pedido de reconhecimento, módulos da Copa João Havelange)
SKIP = {"B": {1979, 1986, 1987, 2000}, "C": {2000}}
# Copa do Brasil: (ano, campeão, estado, vice, estado)
COPA_DO_BRASIL = [
    (1989, "Grêmio", "RS", "Sport", "PE"), (1990, "Flamengo", "RJ", "Goiás", "GO"),
    (1991, "Criciúma", "SC", "Grêmio", "RS"), (1992, "Internacional", "RS", "Fluminense", "RJ"),
    (1993, "Cruzeiro", "MG", "Grêmio", "RS"), (1994, "Grêmio", "RS", "Ceará", "CE"),
    (1995, "Corinthians", "SP", "Grêmio", "RS"), (1996, "Cruzeiro", "MG", "Palmeiras", "SP"),
    (1997, "Grêmio", "RS", "Flamengo", "RJ"), (1998, "Palmeiras", "SP", "Cruzeiro", "MG"),
    (1999, "Juventude", "RS", "Botafogo", "RJ"), (2000, "Cruzeiro", "MG", "São Paulo", "SP"),
    (2001, "Grêmio", "RS", "Corinthians", "SP"), (2002, "Corinthians", "SP", "Brasiliense", "DF"),
    (2003, "Cruzeiro", "MG", "Flamengo", "RJ"), (2004, "Santo André", "SP", "Flamengo", "RJ"),
    (2005, "Paulista", "SP", "Fluminense", "RJ"), (2006, "Flamengo", "RJ", "Vasco da Gama", "RJ"),
    (2007, "Fluminense", "RJ", "Figueirense", "SC"), (2008, "Sport", "PE", "Corinthians", "SP"),
    (2009, "Corinthians", "SP", "Internacional", "RS"), (2010, "Santos", "SP", "Vitória", "BA"),
    (2011, "Vasco da Gama", "RJ", "Coritiba", "PR"), (2012, "Palmeiras", "SP", "Coritiba", "PR"),
    (2013, "Flamengo", "RJ", "Atlético Paranaense", "PR"), (2014, "Atlético Mineiro", "MG", "Cruzeiro", "MG"),
    (2015, "Palmeiras", "SP", "Santos", "SP"), (2016, "Grêmio", "RS", "Atlético Mineiro", "MG"),
    (2017, "Cruzeiro", "MG", "Flamengo", "RJ"), (2018, "Cruzeiro", "MG", "Corinthians", "SP"),
    (2019, "Athletico Paranaense", "PR", "Internacional", "RS"), (2020, "Palmeiras", "SP", "Grêmio", "RS"),
    (2021, "Atlético Mineiro", "MG", "Athletico Paranaense", "PR"), (2022, "Flamengo", "RJ", "Corinthians", "SP"),
    (2023, "São Paulo", "SP", "Flamengo", "RJ"), (2024, "Flamengo", "RJ", "Atlético Mineiro", "MG"),
    (2025, "Corinthians", "SP", "Vasco da Gama", "RJ"),
]
FIELDS = ["competicao", "ano", "campeao", "campeao_artigo", "campeao_local", "vice", "vice_artigo", "vice_local"]


class Wiki:
    def __init__(self, cache: Path):
        self.cache = cache
        cache.mkdir(parents=True, exist_ok=True)
        self.last = 0.0

    def raw(self, title: str, lang: str = "en", follow: bool = True) -> str:
        key = self.cache / f"{lang}_{hashlib.md5(title.encode()).hexdigest()}.txt"
        if key.exists():
            text = key.read_text(encoding="utf-8")
        else:
            url = (f"https://{lang}.wikipedia.org/w/index.php?title="
                   f"{urllib.parse.quote(title.replace(' ', '_'))}&action=raw")
            for attempt in range(6):
                time.sleep(max(0.0, 2.5 - (time.time() - self.last)))
                self.last = time.time()
                done = subprocess.run(["curl", "-s", "-m", "30", "-A", UA, "-w", "\n%{http_code}", url],
                                      capture_output=True)
                body, _, code = done.stdout.rpartition(b"\n")
                if code == b"200":
                    text = body.decode("utf-8", "replace")
                    break
                if code == b"404":
                    text = ""
                    break
                time.sleep(30 * (attempt + 1))              # 429: a Wikipédia pede calma
            else:
                raise RuntimeError(f"{title}: HTTP {code.decode()}")
            key.write_text(text, encoding="utf-8")
        redirect = re.match(r"\s*#(?:REDIRECT|REDIRECIONAMENTO)\s*\[\[([^\]|#]+)", text, re.I)
        if follow and redirect:
            return self.raw(redirect.group(1).strip(), lang, follow=False)
        return text


def collect(wiki: Wiki) -> list[dict]:
    rows = []

    def add(comp: str, table: dict) -> None:
        for year in sorted(table):
            if year > LAST_YEAR or year in SKIP.get(comp, ()):
                continue
            (champ, champ_link, champ_where), (runner, runner_link, runner_where) = table[year]
            rows.append(dict(zip(FIELDS, (comp, year, champ, champ_link or "", champ_where or "",
                                          runner or "", runner_link or "", runner_where or ""))))

    for comp, (title, heading) in NATIONAL.items():
        text = wiki.raw(title)
        add(comp, wikitables.champions(wikitables.section(text, heading) if heading else text))
    add("CDB", {y: ((c, "", cu), (r, "", ru)) for y, c, cu, r, ru in COPA_DO_BRASIL})
    for uf, title in STATES.items():
        add(uf, {y: ((c[0], c[1], uf), (r[0], r[1], uf if r[0] else "")) for y, (c, r) in
                 wikitables.champions(wiki.raw(title)).items()})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=ROOT / "workspace" / "wiki")
    args = parser.parse_args()
    rows = collect(Wiki(args.cache))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    by_comp: dict[str, list[int]] = {}
    for row in rows:
        by_comp.setdefault(row["competicao"], []).append(int(row["ano"]))
    for comp, years in by_comp.items():
        print(f"{comp:5} {len(years):3} anos ({min(years)}–{max(years)})")
    print(f"[OK] {len(rows)} campeões em {OUT}")


if __name__ == "__main__":
    main()
