"""Monta os elencos de 2026 de todos os clubes sobre os jogadores de 2005 (hospedeiros).

    python scripts/live_player_editor.py --squads-all data/brasil/clubes/identidade_fm06.csv
    python scripts/montar_elencos.py

Entradas: data/brasil/jogadores/jogadores_2026.xlsx, identidade_fm06.csv (clube ->
UID do jogo) e workspace/elencos_2005.csv (jogadores de cada clube num New Game).
Cada jogador de 2026 ocupa um jogador de 2005 do mesmo clube: primeiro a equipe
principal (CA maior primeiro), depois a base (PA maior primeiro), até acabarem os
hospedeiros. Saída em workspace/mods/:
- brasil_2026_jogadores.lnc: CHANGE_PLAYER_NAME (copiar para data\\db\\lnc\\all);
- brasil_2026_jogadores.json: dados para o live_player_editor.py;
- brasil_2026_jogadores_hospedeiros.csv: quem virou quem;
- brasil_2026_jogadores_sem_vaga.csv: quem ficou de fora por falta de hospedeiro.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch.squad_builder import ROLE_POSITIONS, Target, build  # noqa: E402

PLAYERS = ROOT / "data" / "brasil" / "jogadores" / "jogadores_2026.xlsx"
IDENTITIES = ROOT / "data" / "brasil" / "clubes" / "identidade_fm06.csv"
HOSTS = ROOT / "workspace" / "elencos_2005.csv"
OUT = ROOT / "workspace" / "mods"
NAME = "brasil_2026_jogadores"


def _targets(path: Path) -> dict[str, list[tuple[Target, dict]]]:
    rows = openpyxl.load_workbook(path, read_only=True)["Jogadores"].iter_rows(values_only=True)
    header = next(rows)
    clubs: dict[str, list[tuple[Target, dict]]] = defaultdict(list)
    for values in rows:
        row = dict(zip(header, values))
        if not row.get("clube"):
            continue
        highlights = {}
        for item in filter(None, (row.get("destaques") or "").split(";")):
            name, _, value = item.partition("=")
            if value.strip().isdigit():
                highlights[name.strip()] = int(value)
        roles = [r for r in str(row["posicoes"]).split() if r in ROLE_POSITIONS] or ["CM"]
        target = Target(number=str(row.get("numero") or ""), common=row.get("nome_comum") or "",
                        first=row.get("primeiro_nome") or "", second=row.get("sobrenome") or "",
                        born=str(row["nascimento"])[:10], nationality=row.get("nacionalidade") or "Brasil",
                        roles=roles, foot=row.get("pe") or "D", height=int(row["altura"]), weight=int(row["peso"]),
                        ca=int(row["ca"]), pa=int(row["pa"]), highlights=highlights)
        clubs[row["clube"]].append((target, row))
    return clubs


def _hosts(path: Path) -> dict[int, list[dict]]:
    by_club: dict[int, list[dict]] = defaultdict(list)
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            by_club[int(row["clube_uid"])].append(
                {**row, "uid": int(row["uid"]), "ca": int(row["ca"]), "peso": int(row["peso"])})
    return by_club


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hospedeiros", type=Path, default=HOSTS)
    parser.add_argument("--year-shift", type=int, default=-20)   # motor 2006 = 2026 (ano exibido + 20)
    args = parser.parse_args()
    clubs = _targets(PLAYERS)
    hosts = _hosts(args.hospedeiros)
    uid_of = {r["clube_2026"]: int(r["uid_jogo"]) for r in csv.DictReader(IDENTITIES.open(encoding="utf-8-sig"))}

    lnc = ["# FM06 Brasil 2026: nomes dos jogadores de 2026"]
    players, mapping, left_out, warnings = [], [], [], []
    for club, entries in sorted(clubs.items()):
        uid = uid_of.get(club)
        pool = hosts.get(uid, []) if uid else []
        if not pool:
            warnings.append(f"{club}: sem hospedeiros (UID {uid})")
            continue
        senior = sorted((e for e in entries if e[1].get("situacao_elenco") != "Base (sub-20)"), key=lambda e: -e[0].ca)
        youth = sorted((e for e in entries if e[1].get("situacao_elenco") == "Base (sub-20)"), key=lambda e: -e[0].pa)
        chosen = (senior + youth)[:len(pool)]
        left_out += [{"clube": club, "jogador": t.display_name, "ca": t.ca, "pa": t.pa}
                     for t, _ in (senior + youth)[len(pool):]]
        text, spec, club_map, club_warnings = build([t for t, _ in chosen], pool, args.year_shift)
        lnc += text.splitlines()[1:]
        players += spec["players"]
        mapping += [{"clube": club, **m} for m in club_map]
        warnings += [f"{club}: {w}" for w in club_warnings]
        print(f"{club:28} {len(chosen):3} de {len(entries):3} jogadores ({len(pool)} hospedeiros)")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{NAME}.lnc").write_text("\r\n".join(lnc) + "\r\n", encoding="utf-16")
    (OUT / f"{NAME}.json").write_text(json.dumps({"year_shift": args.year_shift, "players": players},
                                                 ensure_ascii=False, indent=1), encoding="utf-8")
    for suffix, rows in (("hospedeiros", mapping), ("sem_vaga", left_out)):
        if rows:
            with (OUT / f"{NAME}_{suffix}.csv").open("w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
    nations = defaultdict(int)
    for w in warnings:
        if "sem doador" in w:
            nations[w.rsplit("para ", 1)[-1].split(";")[0]] += 1
    for w in warnings:
        if "sem doador" not in w:
            print("[AVISO]", w)
    if nations:
        print("[AVISO] nacionalidade sem doador (fica a do hospedeiro):", dict(nations))
    print(f"[OK] {len(players)} jogadores em {OUT / NAME}.lnc/.json; {len(left_out)} sem vaga")


if __name__ == "__main__":
    main()
