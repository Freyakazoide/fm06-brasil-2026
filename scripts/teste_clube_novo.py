"""Teste 1 da ficha C13: um clube novo, clonado de outro, no server_db do jogo instalado.

    python scripts\\teste_clube_novo.py            (simulação)
    python scripts\\teste_clube_novo.py --apply    (grava; o jogo tem de estar fechado)

Cria o "Clube Teste 2026" (UID 9000001), brasileiro, copiado do registro do clube do jogo
com UID 330 (o Paraná de 2005, hoje Novorizontino), com um time sem jogadores e sem divisão.
Esperado: o New Game abre e o clube aparece na busca. Desfazer: o próximo aplicar_tudo.py
refaz o server_db.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import clubes_novos  # noqa: E402

DONOR_UID = 330
NEW_UID = 9_000_001
NAME, SHORT = "Clube Teste 2026", "Teste 2026"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    game = Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"])
    path = game / "data" / "db" / "server_db.dat"
    data = path.read_bytes()
    clubs, teams = clubes_novos.club_list(data), clubes_novos.team_list(data)
    if any(clubs.uid(data, i) == NEW_UID for i in range(len(clubs.ends))):
        sys.exit("[OK] o clube de teste já está no banco")
    donor = next(i for i in range(len(clubs.ends)) if clubs.uid(data, i) == DONOR_UID)
    n_at, _ = clubes_novos.club_lists(data, clubs.start(donor), clubs.ends[donor])
    team_index = struct.unpack_from("<I", data, n_at + 1)[0]
    team = clubes_novos.parse_team(data, teams.start(team_index), teams.end(team_index))
    if team is None or team.end - team.tail_at != 57:
        sys.exit(f"[ERRO] o time {team_index} do doador não tem o formato simples")
    club_bytes = clubes_novos.clone_club(data, clubs, donor, NEW_UID, NAME, SHORT, [len(teams.ends)])
    team_bytes = clubes_novos.clone_team(data, team, len(clubs.ends), len(teams.ends), NEW_UID)
    out = clubes_novos.add(data, clubs, teams, club_bytes, team_bytes)
    after_clubs, after_teams = clubes_novos.club_list(out), clubes_novos.team_list(out)
    assert after_clubs.uid(out, len(after_clubs.ends) - 1) == NEW_UID
    assert after_teams.uid(out, len(after_teams.ends) - 1) == NEW_UID
    print(f"doador: clube {donor} (UID {DONOR_UID}), time {team_index}")
    print(f"novo: clube {len(clubs.ends)} e time {len(teams.ends)}, UID {NEW_UID}, "
          f"{len(club_bytes)} + {len(team_bytes)} bytes")
    if args.apply:
        backup = ROOT / "workspace" / "server_db.antes_teste_clube_novo.dat"
        backup.write_bytes(data)
        path.write_bytes(out)
        print(f"[OK] gravado {path} (cópia de antes em {backup})")
    else:
        print("(simulação: rode com --apply para gravar)")


if __name__ == "__main__":
    main()
