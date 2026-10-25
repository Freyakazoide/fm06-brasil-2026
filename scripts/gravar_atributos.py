"""Grava atributos, posições, personalidade, CA/PA e dados pessoais dos jogadores de 2026 no people_db.dat.

    python scripts/gravar_atributos.py                          (simulação, todos)
    python scripts/gravar_atributos.py --uids 3300989,316261    (simulação, só esses)
    python scripts/gravar_atributos.py --apply [--uids ...]     (grava o people_db.dat do jogo)

Lê workspace/mods/brasil_2026_jogadores.json (montar_elencos.py; o mesmo do injetor) e grava
por cima do people_db.dat atual do jogo (depois do aplicar_comissao.py): os 79 bytes da T3,
a personalidade da T2 e, no registro do jogador, reputações, CA, PA, peso, altura,
nascimento (com o year_shift do JSON) e nação. O CA gravado é o "coerente" com os atributos
(fm06patch.atributos_jogadores.choose_ca); a coluna ca_planilha do relatório guarda o
original. Ainda não grava: preferred moves e jogos/gols pela seleção (continuam no injetor).
Depois: New Game. Relatório em workspace/mods/atributos_2026.csv.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import atributos_jogadores  # noqa: E402

PLAYERS = ROOT / "workspace" / "mods" / "brasil_2026_jogadores.json"
SERVER_BACKUP = ROOT / "workspace" / "baseline" / "server_db.original.dat"
REPORT = ROOT / "workspace" / "mods" / "atributos_2026.csv"


def game_dir() -> Path:
    return Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--uids", help="só estes UIDs (separados por vírgula)")
    parser.add_argument("--people", type=Path, help="people_db.dat a usar (padrão: o do jogo)")
    parser.add_argument("--out", type=Path, help="grava aqui em vez de por cima do --people")
    args = parser.parse_args()

    people_path = args.people or game_dir() / "data" / "db" / "people_db.dat"
    server_path = SERVER_BACKUP if SERVER_BACKUP.exists() else game_dir() / "data" / "db" / "server_db.dat"
    spec = json.loads(PLAYERS.read_text(encoding="utf-8"))
    players = spec["players"]
    if args.uids:
        wanted = {int(u) for u in args.uids.split(",")}
        players = [p for p in players if p["uid"] in wanted]
        missing = wanted - {p["uid"] for p in players}
        if missing:
            sys.exit(f"[ERRO] UIDs fora do {PLAYERS.name}: {sorted(missing)}")
    people = people_path.read_bytes()
    print(f"Planejando {len(players)} jogador(es) em {people_path}...", flush=True)
    changes = atributos_jogadores.plan(people, server_path.read_bytes(), players, spec.get("year_shift", 0))

    warned = [c for c in changes if c.warnings]
    for change in warned[:30]:
        print(f"[AVISO] {change.uid} {change.name}: " + "; ".join(change.warnings))
    if len(warned) > 30:
        print(f"[AVISO] ... e mais {len(warned) - 30} (veja {REPORT.name})")
    moved = [c for c in changes if c.ca != c.ca_sheet]
    written = [c for c in changes if c.writes]
    print(f"[OK] {len(written)} de {len(changes)} jogadores com gravação; CA ajustado em {len(moved)} "
          f"(diferença média {sum(abs(c.ca - c.ca_sheet) for c in moved) / max(1, len(moved)):.1f})")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with REPORT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["uid", "nome", "ca_planilha", "ca_gravado", "pa_gravado", "ajuste_new_game", "gravado", "avisos"])
        for c in changes:
            writer.writerow([c.uid, c.name, c.ca_sheet, c.ca, c.pa, c.shift,
                             ", ".join(label for _, _, label in c.writes), "; ".join(c.warnings)])
    print(f"[OK] relatório em {REPORT}")
    if not args.apply:
        print("\nSimulação. Para gravar, rode de novo com --apply.")
        return
    out = args.out or people_path
    out.write_bytes(atributos_jogadores.apply(people, changes))
    print(f"[OK] gravado {out}. Agora: New Game.")


if __name__ == "__main__":
    main()
