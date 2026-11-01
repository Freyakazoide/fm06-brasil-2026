"""Lesões do começo de 2026 (aba Lesoes da lesoes_suspensoes_2026.xlsx): STARTING_INJURY no server_db.dat.

    python scripts\\aplicar_lesoes.py            (simulação: mostra o que faria)
    python scripts\\aplicar_lesoes.py --apply    (grava; o jogo tem de estar fechado)

Rodar depois do montar_elencos.py: o jogador é achado pelo clube e nome comum na
jogadores_2026.xlsx (nascimento), pelo nome e nascimento no brasil_2026_jogadores.json (UID do
hospedeiro) e pelo UID no people_db (índice da pessoa). A lesão vai para o fim da lista
STARTING_INJURY do server_db do jogo, com as datas do motor (ano - 20); o início vai no
máximo até 22/12/2025 (lesão que começa depois do New Game não pega). Rodar de novo não
duplica (src/fm06patch/lesoes.py, ficha C3b).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import lesoes  # noqa: E402

SHEET = ROOT / "data" / "modelos" / "lesoes_suspensoes_2026.xlsx"
PLAYERS_SHEET = ROOT / "data" / "brasil" / "jogadores" / "jogadores_2026.xlsx"
PLAYERS = ROOT / "workspace" / "mods" / "brasil_2026_jogadores.json"


def game_dir() -> Path:
    return Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"])


def births() -> dict[tuple[str, str], str]:
    """(clube, nome comum) -> nascimento AAAA-MM-DD na jogadores_2026.xlsx."""
    rows = openpyxl.load_workbook(PLAYERS_SHEET, read_only=True, data_only=True)["Jogadores"].iter_rows(values_only=True)
    header = [str(h or "").strip() for h in next(rows)]
    out = {}
    for values in rows:
        row = dict(zip(header, values))
        name = str(row.get("nome_comum") or "").strip() or \
            f"{row.get('primeiro_nome') or ''} {row.get('sobrenome') or ''}".strip()
        born = row.get("nascimento")
        if row.get("clube") and name and born:
            born = born.date().isoformat() if isinstance(born, dt.datetime) else str(born)[:10]
            out[(str(row["clube"]).strip(), name)] = born
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    game = game_dir()
    server_path = game / "data" / "db" / "server_db.dat"
    people = (game / "data" / "db" / "people_db.dat").read_bytes()
    born_of = births()
    uid_of = {(p["name"], p.get("birth_date")): p["uid"]
              for p in json.loads(PLAYERS.read_text(encoding="utf-8"))["players"]}
    wanted, problems = [], []
    for row in lesoes.load_sheet(SHEET):
        label = f"{row.nome} ({row.clube})"
        kind = lesoes.kind_of(row.lesao)
        born = born_of.get((row.clube, row.nome))
        uid = uid_of.get((row.nome, born))
        index = lesoes.person_index(people, uid) if uid else None
        if kind is None:
            problems.append(f"{label}: tipo de lesão não reconhecido em {row.lesao!r}")
        elif uid is None:
            problems.append(f"{label}: jogador não achado (nascimento {born})")
        elif index is None:
            problems.append(f"{label}: UID {uid} sem registro único no people_db")
        else:
            start = min(row.desde, lesoes.LATEST_START)          # início depois do New Game não pega
            injury = lesoes.Injury(index, kind[0], lesoes.engine_date(start), lesoes.engine_date(row.volta))
            wanted.append(injury)
            print(f"{label}: UID {uid}, pessoa {index}, lesão {kind[0]} ({kind[1]}), "
                  f"{row.desde} a {row.volta} (motor {injury.start} a {injury.end})")
    for problem in problems:
        print("[AVISO]", problem)
    db, new = lesoes.add(server_path.read_bytes(), wanted)
    print(f"[OK] {len(new)} lesões novas na STARTING_INJURY ({len(wanted) - len(new)} já estavam)")
    if args.apply:
        server_path.write_bytes(db)
        print(f"[OK] gravado {server_path}")
    else:
        print("(simulação: rode com --apply para gravar)")


if __name__ == "__main__":
    main()
