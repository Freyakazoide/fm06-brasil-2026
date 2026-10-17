"""Gera .lnc (nomes) e .json (injetor) para montar um elenco.

    python scripts/build_squad.py data/brasil/flamengo_2026.csv workspace/elenco_flamengo_2005.csv

O segundo arquivo vem de:

    python scripts/live_player_editor.py --squad <UID do clube> --out workspace/elenco_flamengo_2005.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch.squad_builder import build, read_hosts, read_targets, write_outputs  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("elenco", type=Path, help="planilha do elenco desejado")
    parser.add_argument("hospedeiros", type=Path, help="CSV do --squad")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "workspace" / "mods")
    parser.add_argument("--year-shift", type=int, default=-20)   # motor 2006 = 2026 (ano exibido + 20)
    args = parser.parse_args()

    targets = read_targets(args.elenco)
    hosts = read_hosts(args.hospedeiros)
    lnc, spec, mapping, warnings = build(targets, hosts, args.year_shift)
    paths = write_outputs(args.out_dir, args.elenco.stem, lnc, spec, mapping)

    print(f"{len(targets)} jogadores, {len(hosts)} hospedeiros ({len(hosts) - len(targets)} sobram)")
    for row in mapping:
        print(f"  {row['numero']:>3} {row['jogador_2026']:22} <- UID {row['uid_hospedeiro']} (CA {row['ca_hospedeiro']})")
    for warning in warnings:
        print("AVISO:", warning)
    print("\nArquivos:")
    for kind, path in paths.items():
        print(f"  {kind:5} {path}")


if __name__ == "__main__":
    main()
