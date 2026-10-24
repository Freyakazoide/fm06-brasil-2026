"""Carreira de todos os jogadores de 2026 a partir das transferências do Sofascore.

    python scripts\\montar_carreiras.py [--cache workspace\\sofascore]

Lê, no cache do coletar_sofascore.py, o /player/<id>/transfer-history de cada jogador
da jogadores_2026.xlsx (o id vem da coluna fonte_url) e grava
data/brasil/jogadores/carreiras_2026.csv: uma linha por passagem, no formato da aba
Historico da historico_carreira.xlsx (clube, temporada, empréstimo), com o valor da
transferência em euros e sem jogos e gols (o Sofascore não dá por passagem). O
aplicar_historico.py usa a planilha primeiro e este arquivo para os outros jogadores.
Clube de 2026 sai com o nome de 2026 (pelo id do Sofascore em times.json; os que só estão
nos estaduais, pelo nome sem "FC", "EC"...); os outros com o nome do Sofascore, casado
depois com o banco do jogo.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import historico_jogadores as hj  # noqa: E402

PLAYERS = ROOT / "data" / "brasil" / "jogadores" / "jogadores_2026.xlsx"
IDENTITIES = ROOT / "data" / "brasil" / "clubes" / "identidade_fm06.csv"
_PREFIX = {"ad", "aa", "ec", "se", "ge", "fc", "sc", "ac", "clube", "esporte", "futebol"}
OUT = ROOT / "data" / "brasil" / "jogadores" / "carreiras_2026.csv"
FIELDS = ["clube_2026", "nome_comum", "nascimento", "temporada", "clube", "emprestimo", "jogos", "gols",
          "valor_eur", "fonte", "atualizado"]


def cached(cache: Path, path: str):
    key = cache / (hashlib.md5(path.encode()).hexdigest() + ".json")
    return json.loads(key.read_text()) if key.exists() else None


def _plain(name: str) -> frozenset[str]:
    tokens = hj._tokens(re.sub(r"-([A-Z]{2})$", r" uf\1", name))     # "Rio Branco-AC": o AC é o estado
    return frozenset(t for t in tokens if t not in _PREFIX) or frozenset(tokens)


def team_name(side: dict | None, fallback: str | None, names_2026: dict[int, str],
              by_plain: dict[frozenset[str], str]) -> str | None:
    if side and side.get("id") in names_2026:
        return names_2026[side["id"]]
    name = (side or {}).get("name") or fallback
    return by_plain.get(_plain(name), name) if name else name


def transfers(history: dict, names_2026: dict[int, str], by_plain: dict[frozenset[str], str]) -> list[hj.Transfer]:
    out = []
    for t in history.get("transferHistory", []):
        if not t.get("transferDateTimestamp"):
            continue
        fee = (t.get("transferFeeRaw") or {})
        euros = int(fee["value"]) if fee.get("currency") == "EUR" and fee.get("value") else None
        out.append(hj.Transfer(dt.datetime.fromtimestamp(t["transferDateTimestamp"], dt.timezone.utc).date(),
                               team_name(t.get("transferFrom"), t.get("fromTeamName"), names_2026, by_plain),
                               team_name(t.get("transferTo"), t.get("toTeamName"), names_2026, by_plain),
                               int(t.get("type") or 0), euros))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=ROOT / "workspace" / "sofascore")
    parser.add_argument("--times", default="times.json", help="lista de clubes no cache (times_estrangeiros.json)")
    parser.add_argument("--jogadores", type=Path, default=PLAYERS)
    parser.add_argument("--saida", type=Path, default=OUT)
    args = parser.parse_args()
    times_path = args.cache / args.times
    times = json.loads(times_path.read_text(encoding="utf-8"))
    brazil = args.cache / "times.json"      # nos estrangeiros, os clubes brasileiros de 2026 também
    if times_path.name != brazil.name and brazil.exists():
        times += json.loads(brazil.read_text(encoding="utf-8"))
    names_2026 = {}
    for team in times:                      # o sub-20 com " U20": a origem na base não vira passagem
        for key, suffix in (("sofascore_id", ""), ("sub20_id", " U20")):
            if team.get(key):
                names_2026[int(team[key])] = team["clube"] + suffix
    # clubes de 2026 fora do times.json (só estaduais): pelo nome sem "FC", "EC"... ("Capital FC")
    known = set(names_2026.values())
    plain: dict[frozenset[str], set[str]] = {}
    for row in csv.DictReader(IDENTITIES.open(encoding="utf-8-sig")):
        if row["clube_2026"] not in known:
            plain.setdefault(_plain(row["clube_2026"]), set()).add(row["clube_2026"])
    by_plain = {key: next(iter(names)) for key, names in plain.items() if len(names) == 1}
    updated = dt.date.fromtimestamp(times_path.stat().st_mtime).isoformat()

    rows = openpyxl.load_workbook(args.jogadores, read_only=True)["Jogadores"].iter_rows(values_only=True)
    header = next(rows)
    out, players, missing = [], 0, 0
    for values in rows:
        row = dict(zip(header, values))
        match = re.search(r"sofascore\.com/player/[^/]+/(\d+)", str(row.get("fonte_url") or ""))
        if not row.get("clube") or not match:
            continue
        history = cached(args.cache, f"/player/{match.group(1)}/transfer-history")
        if not history:
            missing += 1
            continue
        name = row.get("nome_comum") or f"{row.get('primeiro_nome') or ''} {row.get('sobrenome') or ''}".strip()
        passages = hj.passages_from_transfers(transfers(history, names_2026, by_plain))
        if passages:
            players += 1
        for p in passages:
            out.append({"clube_2026": row["clube"], "nome_comum": name, "nascimento": str(row["nascimento"])[:10],
                        "temporada": p.label, "clube": p.club, "emprestimo": "sim" if p.loan else "não",
                        "jogos": "", "gols": "", "valor_eur": p.fee or "", "fonte": row["fonte_url"],
                        "atualizado": updated})
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    with args.saida.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(out)
    print(f"[OK] {players} jogadores, {len(out)} passagens em {args.saida.relative_to(ROOT)} "
          f"({missing} sem transferências no cache)")


if __name__ == "__main__":
    main()
