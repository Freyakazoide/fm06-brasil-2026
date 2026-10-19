"""Saldo inicial e público médio de 2026 dos clubes das Séries A, B, C e D.

    python scripts/montar_financas.py [--sofascore workspace/sofascore] [--wiki workspace/wiki]

Grava data/brasil/clubes/financas_2026.csv (pode editar à mão; o
scripts/aplicar_brasil_2026.py grava o que estiver lá):

- saldo_rs: estimado pelo tamanho do clube, a torcida no Sofascore (seguidores) em
  relação à mediana da série: base × (torcida / mediana) ^ 0,6, com piso e teto por
  série. Base: A R$ 45 mi, B R$ 8 mi, C R$ 2,5 mi, D R$ 600 mil.
- publico_medio: média de público de 2025 na Wikipédia (tabelas de público das
  páginas das Séries de 2025), quando houver; senão, estimativa: média da série ×
  (torcida / mediana) ^ 0,5, entre 0,35 e 2,2 vezes a média. Médias: A 26.222 (2025,
  Wikipédia), B 9.000, C 4.500, D 1.800 (estimadas).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from coletar_historico import Wiki  # noqa: E402
from coletar_sofascore import Sofascore  # noqa: E402
from fm06patch import wikitables  # noqa: E402
from fm06patch.estaduais_clubes import normalize  # noqa: E402

OUT = ROOT / "data" / "brasil" / "clubes" / "financas_2026.csv"
BASE = {"A": 45e6, "B": 8e6, "C": 2.5e6, "D": 0.6e6}
LIMITS = {"A": (12e6, 180e6), "B": (2.5e6, 30e6), "C": (0.8e6, 8e6), "D": (0.15e6, 2.5e6)}
AVERAGE_CROWD = {"A": 26222, "B": 9000, "C": 4500, "D": 1800}
FIELDS = ["serie", "clube", "uf", "torcida_sofascore", "saldo_rs", "publico_medio", "fonte_publico"]


def balance(serie: str, fans: int, median: float) -> int:
    value = BASE[serie] * (max(fans, 1) / median) ** 0.6
    low, high = LIMITS[serie]
    return int(round(min(high, max(low, value)), -4))


def estimated_crowd(serie: str, fans: int, median: float) -> int:
    factor = min(2.2, max(0.35, (max(fans, 1) / median) ** 0.5))
    return int(round(AVERAGE_CROWD[serie] * factor, -2))


def attendance_tables(wiki: Wiki) -> dict[str, int]:
    """Nome do clube (normalizado) -> público médio, das tabelas "Attendance" de 2025."""
    found: dict[str, int] = {}
    for serie in "ABCD":
        text = wiki.raw(f"2025 Campeonato Brasileiro Série {serie}")
        for head in re.finditer(r"\n=+\s*(Attendance|Average attendance)[^=\n]*=+", text, re.I):
            body = text[head.end():text.find("\n==", head.end() + 1)]
            for table in wikitables.tables(body):
                rows = wikitables.rows(table)
                if not rows:
                    continue
                header = [wikitables._plain(h).lower() for h in rows[0]]
                average = next((i for i, h in enumerate(header) if "average" in h or "avg" in h), None)
                team = next((i for i, h in enumerate(header) if "team" in h or "club" in h), None)
                if average is None or team is None:
                    continue
                for cells in rows[1:]:
                    if len(cells) != len(header):
                        continue
                    name = wikitables.link_text(cells[team])[0]
                    number = re.sub(r"[^\d]", "", wikitables._plain(cells[average]))
                    if name and number:
                        found.setdefault(normalize(name), int(number))
    return found


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sofascore", type=Path, default=ROOT / "workspace" / "sofascore")
    parser.add_argument("--wiki", type=Path, default=ROOT / "workspace" / "wiki")
    args = parser.parse_args()
    teams = json.loads((args.sofascore / "times.json").read_text(encoding="utf-8"))
    api = Sofascore(args.sofascore)
    fans = {t["clube"]: ((api.get(f"/team/{t['sofascore_id']}") or {}).get("team", {}).get("userCount") or 0)
            for t in teams}
    medians = {s: statistics.median(fans[t["clube"]] for t in teams if t["serie"] == s) for s in "ABCD"}
    crowds = attendance_tables(Wiki(args.wiki))
    rows = []
    for team in teams:
        keys = [normalize(team["clube"]), normalize(team["sofascore_nome"]),
                normalize(re.sub(r"-[A-Z]{2}$", "", team["clube"]))]
        crowd = next((crowds[k] for k in keys if k in crowds), None)
        rows.append({"serie": team["serie"], "clube": team["clube"], "uf": team["estado"],
                     "torcida_sofascore": fans[team["clube"]],
                     "saldo_rs": balance(team["serie"], fans[team["clube"]], medians[team["serie"]]),
                     "publico_medio": crowd or estimated_crowd(team["serie"], fans[team["clube"]], medians[team["serie"]]),
                     "fonte_publico": "Wikipédia 2025" if crowd else "estimativa"})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    real = sum(1 for r in rows if r["fonte_publico"] == "Wikipédia 2025")
    print(f"[OK] {len(rows)} clubes em {OUT} (público: {real} da Wikipédia, {len(rows) - real} estimados)")


if __name__ == "__main__":
    main()
