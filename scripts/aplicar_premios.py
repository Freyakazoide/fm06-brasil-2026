"""Histórico de prêmios do Brasil (Bola de Ouro de 2006 a 2025) no server_db.dat.

    python scripts\\aplicar_premios.py            (simulação: mostra o que faria)
    python scripts\\aplicar_premios.py --apply    (grava; o jogo tem de estar fechado)

Rodar depois do montar_elencos.py e do aplicar_comissao.py: o vencedor com jogador_2026 e
clube_2026 preenchidos na planilha (o mesmo nome e clube das listas de hospedeiros de
workspace/mods) fica ligado à pessoa e o prêmio aparece na ficha dele; os outros entram só com
o nome. A ligação é explícita porque há homônimos (um "Gabriel Jesus" no Barra, um "Estêvão"
no CRB). Os anos do histórico do Brasil que o banco já tinha passam a −20 (o jogo mostra
+20). Em qualquer prêmio, a ligação com uma pessoa de 2005 que virou outra de 2026 sai e
fica só o nome (os hospedeiros são os do aplicar_relacoes.py). A planilha é a data/modelos/premios_historico.xlsx; rodar de novo não grava duas vezes
(src/fm06patch/premios.py).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import premios, rivais  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
import aplicar_relacoes  # noqa: E402

SHEET = ROOT / "data" / "modelos" / "premios_historico.xlsx"
MODS = ROOT / "workspace" / "mods"
HOSTS = (("brasil_2026_jogadores_hospedeiros.csv", "jogador_2026", "uid_hospedeiro"),
         ("comissao_2026_hospedeiros.csv", "nome_2026", "uid"))


def game_dir() -> Path:
    return Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"])


def hosts() -> dict[str, list[tuple[str, int]]]:
    """nome de 2026 -> [(clube, UID do hospedeiro)]."""
    out: dict[str, list[tuple[str, int]]] = {}
    for name, name_col, uid_col in HOSTS:
        path = MODS / name
        if path.exists():
            for row in csv.DictReader(path.open(encoding="utf-8-sig")):
                out.setdefault(row[name_col].strip(), []).append((row["clube"].strip(), int(row[uid_col])))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    game = game_dir()
    server_path = game / "data" / "db" / "server_db.dat"
    winners = premios.load_sheet(SHEET)
    by_name = hosts()
    chosen: dict[int, int | None] = {}
    for year, (name, now, club) in winners.items():
        found = [uid for c, uid in by_name.get(now, []) if c == club] if now else []
        chosen[year] = found[0] if len(found) == 1 else None
        if now and len(found) != 1:
            print(f"[AVISO] {year} {name}: {now} ({club}) não achado nos hospedeiros")
    people = (game / "data" / "db" / "people_db.dat").read_bytes()
    index = rivais.person_indices(people, {u for u in chosen.values() if u})
    gone = set(rivais.person_indices(people, aplicar_relacoes.hosts()[0]).values())
    golden = {year: (name, index.get(chosen[year], premios.NONE)) for year, (name, _, _) in winners.items()}
    for year in sorted(golden):
        name, person = golden[year]
        print(f"{year} {name}: " + (f"pessoa {person}" if person != premios.NONE else "só o nome"))
    db, lines = premios.apply(server_path.read_bytes(), golden, gone)
    for line in lines:
        print("[OK]", line)
    if args.apply:
        server_path.write_bytes(db)
        print(f"[OK] gravado {server_path}")
    else:
        print("(simulação: rode com --apply para gravar)")


if __name__ == "__main__":
    main()
