"""Põe os técnicos e as comissões de 2026 nos clubes (people_db.dat + .lnc).

    python scripts/aplicar_comissao.py            (simulação)
    python scripts/aplicar_comissao.py --apply    (grava o people_db.dat e o .lnc do jogo)

Cada pessoa de data/brasil/comissao/comissao_2026.csv (scripts/coletar_comissao.py)
ocupa alguém do FM06 com o mesmo cargo no clube (técnico, auxiliar, treinador,
fisioterapeuta/médico, olheiro): o .lnc dá o nome (CHANGE_PLAYER_NAME, aplicado no
New Game) e o people_db recebe a nacionalidade e, do técnico, o nascimento (20
anos antes, como os jogadores). Clube sem gente bastante naquele cargo recebe
alguém do mesmo cargo de um clube brasileiro fora de 2026 (muda o clube do
contrato). Quem sobra no clube ganha um nome de hoje. O técnico das seleções
de data/brasil/comissao/selecoes_2026.csv (linha com nome) ocupa o técnico da seleção
no banco (Parreira -> Ancelotti). A pessoa de 2005 que é alguém de 2026 (mesmo nome e
nascimento: o Ancelotti do Milan, o Forlán jogador) também ganha nome de hoje, do país
dela, para o jogo não ter dois. Rodar depois do montar_elencos.py (usa a lista dos
jogadores montados).

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

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import comissao, elenco_times, historico, nomes_regens, people_contracts  # noqa: E402

STAFF_CSV = ROOT / "data" / "brasil" / "comissao" / "comissao_2026.csv"
IDENTITIES = ROOT / "data" / "brasil" / "clubes" / "identidade_fm06.csv"
PEOPLE_BACKUP = ROOT / "workspace" / "baseline" / "people_db.original.dat"
SERVER_BACKUP = ROOT / "workspace" / "baseline" / "server_db.original.dat"
REPORT = ROOT / "workspace" / "mods" / "comissao_2026_hospedeiros.csv"
LNC_NAME = "brasil_2026_comissao.lnc"
REGEN_NAMES = ROOT / "data" / "modelos" / "nomes_regens.xlsx"   # nomes de hoje para quem sobra
NATIONAL_CSV = ROOT / "data" / "brasil" / "comissao" / "selecoes_2026.csv"   # técnicos das seleções
PLAYERS = ROOT / "workspace" / "mods" / "brasil_2026_jogadores.json"            # do montar_elencos.py
RENAMED = ROOT / "workspace" / "mods" / "brasil_2026_jogadores_renomeados.csv"  # idem
PLAYERS_SHEET = ROOT / "data" / "brasil" / "jogadores" / "jogadores_2026.xlsx"


def game_dir() -> Path:
    return Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"])


def wanted_2026(result: comissao.Plan) -> tuple[list[tuple[set[str], str]], set[int]]:
    """(nomes, nascimento) de quem está no jogo em 2026 e os UIDs que já ganham nome novo:
    a comissão (inclusive os técnicos das seleções), os jogadores montados (montar_elencos.py)
    e os jogadores de 2005 que ficam nos clubes de 2026 com nome de hoje."""
    wanted = [({row.nome}, row.nascimento) for _, row in result.renames if row.nascimento]
    taken = {person.uid for person, _ in result.renames} | {person.uid for person, _ in result.fillers}
    if PLAYERS.exists():
        spec = json.loads(PLAYERS.read_text(encoding="utf-8"))
        taken |= {p["uid"] for p in spec["players"]}
        placed = {(p["club_uid"], p["name"], p["birth_date"]) for p in spec["players"]}
        uid_of = {r["clube_2026"]: int(r["uid_jogo"]) for r in csv.DictReader(IDENTITIES.open(encoding="utf-8-sig"))}
        rows = openpyxl.load_workbook(PLAYERS_SHEET, read_only=True)["Jogadores"].iter_rows(values_only=True)
        header = next(rows)
        for values in rows:
            row = dict(zip(header, values))
            full = f"{row.get('primeiro_nome') or ''} {row.get('sobrenome') or ''}".strip()
            name, born = row.get("nome_comum") or full, str(row.get("nascimento") or "")[:10]
            if (uid_of.get(row.get("clube")), name, born) in placed:
                wanted.append(({name, full}, born))
    if RENAMED.exists():
        taken |= {int(r["uid"]) for r in csv.DictReader(RENAMED.open(encoding="utf-8-sig")) if r["uid"].isdigit()}
    return wanted, taken


def add_namesakes(result: comissao.Plan, people: bytes, server: bytes) -> None:
    """A pessoa de 2005 que é alguém de 2026 (Ancelotti no Milan, Forlán no Villarreal, Tite...)
    ganha um nome de hoje do país dela: senão o jogo tem dois."""
    wanted, taken = wanted_2026(result)
    found = comissao.namesakes(comissao.read_people(people, server), wanted, taken)
    if not found:
        return
    names = comissao.names_by_nation(server)
    if REGEN_NAMES.exists():                        # nomes de hoje primeiro; senão os do banco do país
        names.update(nomes_regens.load_sheet(REGEN_NAMES))
    for person in found:
        filler = nomes_regens.Filler(names, person.nation)
        filler = filler if filler else nomes_regens.Filler(names)
        result.fillers.append((person, tuple(n.replace('"', "") for n in filler.name(person.uid))))
    print(f"[OK] {len(found)} pessoas de 2005 que também estão em 2026 (mesmo nome e nascimento) "
          "ganham nome de hoje: " + ", ".join(sorted(p.common or p.name for p in found)))


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
    if NATIONAL_CSV.exists():                       # técnico da seleção: o de 2005 vira o de 2026
        managers = comissao.read_national_managers(original, server)
        taken = {person.uid for person, _ in result.renames} | {person.uid for person, _ in result.fillers}
        for row in csv.DictReader(NATIONAL_CSV.open(encoding="utf-8-sig")):
            if not row["nome"].strip():
                continue
            hosts = [p for p in managers.get(comissao.nation_code(row["nacao"]), []) if p.uid not in taken]
            if len(hosts) > 1:                      # Venezuela: Páez e um "Kevin Terry"
                hosts = [p for p in hosts if p.name == row.get("tecnico_fm06", "").strip()]
            if len(hosts) != 1:
                print(f"[AVISO] seleção {row['nacao']}: {len(hosts)} técnicos no banco; fica como está")
                continue
            result.renames.append((hosts[0], comissao.Wanted(0, f"Seleção {row['nacao']}", "tecnico", row["nome"],
                                                             row["nacionalidade"], row["nascimento"])))
            print(f"[OK] seleção {row['nacao']}: {hosts[0].name} -> {row['nome']}")
    add_namesakes(result, original, server)
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
    # quem vem de outro clube entra na comissão do time no server_db (elenco_times): a lista de
    # auxiliares e treinadores, a de fisioterapeutas e médicos ou o técnico
    club_uid = {index: uid for uid, index in indexes.items()}
    moves = []
    for person, club, team in result.moves:
        index = comissao.person_index(original, person)
        kind = elenco_times.LIST_OF_JOB.get(person.job)
        if index is not None and kind and club in club_uid:
            moves.append(elenco_times.Move(index, club_uid[club], team, kind))
    server_path = game / "data" / "db" / "server_db.dat"
    server_data, missing = elenco_times.apply(server_path.read_bytes(), moves)
    server_path.write_bytes(server_data)
    print(f"[OK] {len(moves) - len(missing)} da comissão mudados de clube no {server_path.name}"
          + (f" ({len(missing)} sem o time do clube novo)" if missing else ""))
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
