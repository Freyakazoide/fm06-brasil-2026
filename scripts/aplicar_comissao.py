"""Põe os técnicos e as comissões de 2026 nos clubes (people_db.dat + .lnc).

    python scripts/aplicar_comissao.py            (simulação)
    python scripts/aplicar_comissao.py --apply    (grava o people_db.dat e o .lnc do jogo)

Cada pessoa de data/brasil/comissao/comissao_2026.csv (scripts/coletar_comissao.py)
ocupa alguém do FM06 com o mesmo cargo no clube (técnico, auxiliar, treinador,
fisioterapeuta/médico, olheiro): o .lnc dá o nome (CHANGE_PLAYER_NAME, aplicado no
New Game) e o people_db recebe a nacionalidade e, do técnico, o nascimento (20
anos antes, como os jogadores). Clube sem gente bastante naquele cargo recebe
alguém do mesmo cargo de um clube brasileiro fora de 2026 (muda o clube do
contrato). Quem sobra no clube continua com o nome de 2005.

Grava sobre o people_db atual do jogo (depois do reforcar_elencos.py; os dois mexem
em pessoas diferentes) e lê as pessoas da cópia original
(workspace/baseline/people_db.original.dat). Se rodar o reforcar_elencos.py de novo,
rode este também. Depois: New Game.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import struct
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import comissao, historico, nomes_regens, people_contracts  # noqa: E402

STAFF_CSV = ROOT / "data" / "brasil" / "comissao" / "comissao_2026.csv"
IDENTITIES = ROOT / "data" / "brasil" / "clubes" / "identidade_fm06.csv"
PEOPLE_BACKUP = ROOT / "workspace" / "baseline" / "people_db.original.dat"
SERVER_BACKUP = ROOT / "workspace" / "baseline" / "server_db.original.dat"
REPORT = ROOT / "workspace" / "mods" / "comissao_2026_hospedeiros.csv"
LNC_NAME = "brasil_2026_comissao.lnc"
REGEN_NAMES = ROOT / "data" / "modelos" / "nomes_regens.xlsx"   # nomes de hoje para quem sobra


def game_dir() -> Path:
    return Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    game = game_dir()
    people_path = game / "data" / "db" / "people_db.dat"
    if not PEOPLE_BACKUP.exists():
        PEOPLE_BACKUP.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(people_path, PEOPLE_BACKUP)
        print(f"[OK] cópia do people_db original em {PEOPLE_BACKUP}")
    original = PEOPLE_BACKUP.read_bytes()
    server = (SERVER_BACKUP if SERVER_BACKUP.exists() else game / "data" / "db" / "server_db.dat").read_bytes()

    identities = list(csv.DictReader(IDENTITIES.open(encoding="utf-8-sig")))
    uid_of = {r["clube_2026"]: int(r["uid_jogo"]) for r in identities}
    repo_of = {int(r["uid_jogo"]): int(r["uid_repo"]) for r in identities}
    wanted, unknown = [], set()
    for row in csv.DictReader(STAFF_CSV.open(encoding="utf-8-sig")):
        if row["clube"] not in uid_of:
            unknown.add(row["clube"])
            continue
        wanted.append(comissao.Wanted(uid_of[row["clube"]], row["clube"], row["cargo"], row["nome"],
                                      row["nacionalidade"] or "BRA", row["nascimento"]))   # sem dado: brasileiro
    if unknown:
        print("[AVISO] clubes da planilha sem identidade no jogo:", ", ".join(sorted(unknown)))

    print("Lendo o staff do people_db...", flush=True)
    staff = comissao.read_staff(original, server)
    indexes = people_contracts.brazil_club_indexes(server)
    ours = set(repo_of)
    club_index = {uid: indexes[uid] for uid in ours if uid in indexes}
    # campo "time" de quem vem de fora: o mesmo do staff que o clube já tem (é o índice do time,
    # historico.team_index; um a menos aponta para outro time e o New Game trava)
    current: dict[int, Counter] = {}
    for person in staff:
        value = struct.unpack_from("<I", original, person.team_at)[0]
        if value != comissao.NONE:
            current.setdefault(person.club, Counter())[value] += 1
    team_index = {}
    for uid in ours:
        if uid in club_index and club_index[uid] in current:
            team_index[uid] = current[club_index[uid]].most_common(1)[0][0]
            continue
        try:
            team_index[uid] = historico.team_index(server, repo_of[uid])
        except ValueError:
            pass
    spare = {index for uid, index in indexes.items() if uid not in ours}
    foreign = {person.club for person in staff} - set(indexes.values())
    result = comissao.plan(staff, [w for w in wanted if w.club_uid in team_index], club_index, team_index, spare,
                           foreign)
    filler = nomes_regens.Filler(nomes_regens.load_sheet(REGEN_NAMES)) if REGEN_NAMES.exists() else None
    if filler:                                      # staff de 2005 que sobra: nome brasileiro de hoje
        comissao.fill_names(result, staff, set(club_index.values()), filler.name)
    for line in result.report:
        print("  ", line)
    managers = sum(1 for _, row in result.renames if row.cargo == "tecnico")
    print(f"[OK] {len(result.renames)} pessoas renomeadas ({managers} técnicos), "
          f"{len(result.moves)} trazidas de clubes fora de 2026; {len(result.fillers)} que sobram com nome de hoje")
    foreign = {row.nacionalidade for _, row in result.renames
               if row.nacionalidade and comissao.nation_code(row.nacionalidade) is None}
    if foreign:
        print("[AVISO] nacionalidade sem código no jogo (fica a do FM06):", ", ".join(sorted(foreign)))
    if not args.apply:
        print("\nSimulação. Para gravar, rode de novo com --apply.")
        return

    current = people_path.read_bytes()
    if len(current) != len(original):
        sys.exit(f"[ERRO] {people_path} não tem o tamanho do original; restaure o people_db e rode de novo.")
    people_path.write_bytes(comissao.apply(current, result))
    lnc_text = comissao.lnc_text(result)
    lnc_path = game / "data" / "db" / "lnc" / "all" / LNC_NAME
    lnc_path.parent.mkdir(parents=True, exist_ok=True)
    lnc_path.write_text(lnc_text, encoding="utf-16")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    (REPORT.parent / LNC_NAME).write_text(lnc_text, encoding="utf-16")
    with REPORT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["clube", "cargo", "nome_2026", "uid", "nome_fm06", "trazido_de_outro_clube"])
        moved = {person.uid for person, _, _ in result.moves}
        for person, row in result.renames:
            writer.writerow([row.clube, row.cargo, row.nome, person.uid, person.name, "sim" if person.uid in moved else ""])
    print(f"[OK] gravado {people_path}")
    print(f"[OK] gravado {lnc_path} (cópia em {REPORT.parent / LNC_NAME}); lista em {REPORT}")
    print("Agora: New Game (o .lnc dá os nomes no New Game).")


if __name__ == "__main__":
    main()
