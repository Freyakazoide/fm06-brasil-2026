"""Lista e altera a divisão inicial dos times brasileiros no server_db.dat.

Exemplos (cada um é uma linha só):
    python scripts\\server_db_teams.py --list
    python scripts\\server_db_teams.py --list --serie C
    python scripts\\server_db_teams.py --set "Flamengo=C" --set "Tubarão=A"
    python scripts\\server_db_teams.py --set "Flamengo=C" --set "Tubarão=A" --apply
    python scripts\\server_db_teams.py --restore

Sem --apply só mostra o que mudaria. Com --apply, guarda uma cópia do original
em workspace\\baseline\\server_db.original.dat (só na primeira vez) e grava o
server_db.dat do jogo. --restore volta o original.

Opções de alteração (podem repetir):
    --set  "TIME=SÉRIE"     divisão em que o time começa (A, B, C)
    --pos  "TIME=N"         classificação na temporada passada (0 = nenhuma)
    --last "TIME=SÉRIE"     divisão da temporada passada (A, B, C ou -)
    --top  "C:20:NOVA_C"    move os 20 times de maior reputação da C para a NOVA_C
TIME é o nome curto, o nome longo ou o UID do clube.
NOVA_C é a nova Série C criada pelo patch serie_c_nova do fm.exe (índice 376).
Com esse patch, a C antiga (índice 86) passa a ser o 4º nível.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch.server_teams import (  # noqa: E402
    DIVISIONS,
    division_index,
    find_team,
    find_teams,
    write_team,
)

BACKUP = ROOT / "workspace" / "baseline" / "server_db.original.dat"
ORIGINAL_SHA256 = "9FB7A4A2B87798120BF4D9DA9E86E7DABB99C668802B2FB9ECB035230F66BE62"


def game_server_db() -> Path:
    config = json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))
    return Path(config["game_dir"]) / "data" / "db" / "server_db.dat"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def pairs(values: list[str], option: str) -> list[tuple[str, str]]:
    result = []
    for value in values:
        if "=" not in value:
            sys.exit(f"[ERRO] {option} espera TIME=VALOR, recebeu: {value}")
        key, _, new = value.rpartition("=")
        result.append((key, new))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", type=Path, help="server_db.dat (padrão: o do jogo, de config/local.json)")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--serie", choices=sorted(DIVISIONS))
    parser.add_argument("--set", action="append", default=[])
    parser.add_argument("--pos", action="append", default=[])
    parser.add_argument("--last", action="append", default=[])
    parser.add_argument("--top", action="append", default=[])
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()

    path = args.db or game_server_db()

    if args.restore:
        if not BACKUP.exists():
            sys.exit(f"[ERRO] não há cópia do original em {BACKUP}")
        shutil.copy2(BACKUP, path)
        print(f"[OK] original restaurado em {path}")
        return

    data = bytearray(path.read_bytes())
    teams = find_teams(bytes(data))
    teams.sort(key=lambda t: (t.serie, t.last_position or 99, t.short_name))

    if args.list or not (args.set or args.pos or args.last or args.top):
        print(f"{'Série':5} {'UID':>8}  {'Clube':26} {'Pos ant.':>8} {'Série ant.':>10} {'Reput.':>6}")
        for team in teams:
            if args.serie and team.serie != args.serie:
                continue
            print(f"{team.serie:5} {team.club_uid:>8}  {team.short_name[:26]:26} "
                  f"{team.last_position or '-':>8} {team.last_serie:>10} {team.reputation:>6}")
        counts = {key: sum(t.serie == key for t in teams) for key in DIVISIONS}
        print("Total por série:", counts)
        return

    try:
        changes = []
        for key, value in pairs(args.set, "--set"):
            team = find_team(teams, key)
            changes.append((team, "divisão", team.serie, value.upper()))
            team.division = division_index(value)
        for spec in args.top:
            source, count, dest = spec.split(":")
            pool = [t for t in teams if t.serie == source.upper()]
            for team in sorted(pool, key=lambda t: -t.reputation)[:int(count)]:
                changes.append((team, "divisão", team.serie, dest.upper()))
                team.division = division_index(dest)
        for key, value in pairs(args.pos, "--pos"):
            team = find_team(teams, key)
            changes.append((team, "classificação anterior", team.last_position, int(value)))
            team.last_position = int(value)
        for key, value in pairs(args.last, "--last"):
            team = find_team(teams, key)
            changes.append((team, "série anterior", team.last_serie, value.upper()))
            team.last_division = division_index(value)
    except (KeyError, ValueError) as error:
        sys.exit(f"[ERRO] time ou valor inválido: {error}")

    for team, field, old, new in changes:
        print(f"{team.short_name} ({team.club_uid}): {field} {old} -> {new}")
    for team in {id(t): t for t, *_ in changes}.values():
        write_team(data, team)

    counts = {key: sum(t.serie == key for t in teams) for key in DIVISIONS}
    print("Total por série depois:", counts)

    if not args.apply:
        print("\nSimulação. Para gravar, rode o mesmo comando com --apply no fim.")
        return

    if not BACKUP.exists():
        if sha256(path) != ORIGINAL_SHA256:
            sys.exit("[ERRO] o server_db.dat do jogo não é o original e não há cópia em workspace\\baseline. "
                     "Coloque o original de volta antes.")
        BACKUP.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, BACKUP)
        print(f"[OK] cópia do original em {BACKUP}")
    path.write_bytes(data)
    print(f"[OK] gravado {path}")


if __name__ == "__main__":
    main()
