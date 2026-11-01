"""Tira dos clubes brasileiros as pessoas queridas/não queridas de 2005 que viraram outra pessoa.

    python scripts\aplicar_relacoes.py            (simulação: mostra o que faria)
    python scripts\aplicar_relacoes.py --apply    (grava; o jogo tem de estar fechado)

Rodar depois do montar_elencos.py, do aplicar_comissao.py e do aplicar_arbitros.py: os
hospedeiros são os das listas que eles deixam em workspace/mods (jogadores, renomeados,
comissão e árbitros). A relação de pessoa (tipo 3) do registro do clube aponta para o índice da
pessoa no people_db; se a pessoa é um hospedeiro, a relação sai (o Corinthians "gostava" do
Ricardinho, que virou o Neymar). Fica quem é a mesma pessoa nos dois anos (técnico com o mesmo
nome, como o Diego Aguirre). Ver src/fm06patch/rivais.py e docs/reversing/database.md.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import rivais  # noqa: E402

MODS = ROOT / "workspace" / "mods"
HOSTS = (                                   # arquivo, coluna do UID, nome de 2026, nome do FM06
    ("brasil_2026_jogadores_hospedeiros.csv", "uid_hospedeiro", "jogador_2026", None),
    ("brasil_2026_jogadores_renomeados.csv", "uid", "nome", None),
    ("comissao_2026_hospedeiros.csv", "uid", "nome_2026", "nome_fm06"),
    ("arbitros_2026_hospedeiros.csv", "uid", "arbitro_2026", "arbitro_fm06"),
)


def game_dir() -> Path:
    return Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"])


def _words(name: str) -> set[str]:
    return set(unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower().split())


def hosts() -> tuple[set[int], list[str]]:
    """UIDs que viraram outra pessoa e os que ficam (mesma pessoa)."""
    out, same = set(), []
    for name, uid_col, new_col, old_col in HOSTS:
        path = MODS / name
        if not path.exists():
            continue
        for row in csv.DictReader(path.open(encoding="utf-8-sig")):
            new, old = _words(row[new_col]), _words(row[old_col]) if old_col else set()
            if new and old and (new <= old or old <= new):
                same.append(row[new_col])
                continue
            out.add(int(row[uid_col]))
    return out, same


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    game = game_dir()
    server_path = game / "data" / "db" / "server_db.dat"
    uids, same = hosts()
    gone = set(rivais.person_indices((game / "data" / "db" / "people_db.dat").read_bytes(), uids).values())
    db = server_path.read_bytes()
    clubs = rivais.read(db)
    changes = rivais.drop_people(clubs, gone)
    removed = sum(len(clubs[u].relations) - len(r) for u, r in changes.items())
    print(f"[OK] {len(uids)} hospedeiros ({len(gone)} com índice); {removed} pessoas queridas/não queridas "
          f"saem de {len(changes)} clubes; ficam as mesmas pessoas: {', '.join(same) or 'nenhuma'}")
    if args.apply:
        server_path.write_bytes(rivais.apply(db, clubs, changes))
        print(f"[OK] gravado {server_path}")
    else:
        print("(simulação: rode com --apply para gravar)")


if __name__ == "__main__":
    main()
