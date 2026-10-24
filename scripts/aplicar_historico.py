"""Histórico de carreira (aba Histórico) dos jogadores de 2026: data/db/pl_hist_*.dat.

    python scripts\\aplicar_historico.py            (simulação: mostra o que faria)
    python scripts\\aplicar_historico.py --apply    (grava; o jogo tem de estar fechado)
    python scripts\\aplicar_historico.py --restore  (volta o original)

Rodar depois do montar_elencos.py (e do aplicar_comissao.py) e antes do New Game em que
os nomes entram: o jogo lê o histórico no New Game.
- quem está em data/modelos/historico_carreira.xlsx ganha a carreira de verdade (jogos
  e gols de cada passagem repartidos por igual entre as temporadas dela, e o valor das
  transferências que a carreiras_2026.csv tiver);
- os outros jogadores de 2026 ganham os clubes por onde passaram e o valor de cada
  transferência (data/brasil/jogadores/carreiras_2026.csv, do montar_carreiras.py, e a
  data/estrangeiros/carreiras_estrangeiros_2026.csv dos clubes da CONMEBOL), sem jogos
  e gols;
- quem não está em nenhum dos dois e a comissão de 2026 perdem a carreira do jogador de
  2005 que ocupam (fica só a temporada atual);
- os jogadores de 2005 que sobram (nome de hoje) ficam com a carreira que tinham.
Parte sempre do original (cópias em workspace/baseline/pl_hist_*.original.dat). Lista
do que entrou em workspace/mods/historico_2026.csv.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import json
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import estrangeiros, historico_jogadores as hj, traducao  # noqa: E402

FILES = ("index", "id", "dt")
SHA256 = {"index": "3FD46578A293D8B2AD99297F71BD19387A6B144AC95793F20309B9CC3503FB53",   # 6.0.2
          "id": "873E5442F3F8B99FDE7BAB6DFB1300D50FC5740BF1E977FCC4C004E8D8AE015B",
          "dt": "D8EC837EA720F4F8E117037BFFAE0322EEC1C9DC014890ECBA87FEAAEAB4CE18"}
BASELINE = ROOT / "workspace" / "baseline"
MODS = ROOT / "workspace" / "mods"
SHEET = ROOT / "data" / "modelos" / "historico_carreira.xlsx"
CAREERS = ROOT / "data" / "brasil" / "jogadores" / "carreiras_2026.csv"   # do montar_carreiras.py
IDENTITIES = ROOT / "data" / "brasil" / "clubes" / "identidade_fm06.csv"
PLAYERS = MODS / "brasil_2026_jogadores.json"           # do montar_elencos.py
STAFF = MODS / "comissao_2026_hospedeiros.csv"          # do aplicar_comissao.py
REPORT = MODS / "historico_2026.csv"
MISSING = MODS / "historico_2026_clubes_faltando.csv"


def game_dir() -> Path:
    return Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"])


def game_file(game: Path, name: str) -> Path:
    return game / "data" / "db" / f"pl_hist_{name}.dat"


def backup(name: str) -> Path:
    return BASELINE / f"pl_hist_{name}.original.dat"


def originals(game: Path) -> list[bytes] | None:
    if all(backup(n).exists() for n in FILES):
        return [backup(n).read_bytes() for n in FILES]
    out = []
    for name in FILES:
        path = game_file(game, name)
        if not path.exists():
            print(f"[AVISO] {path} não existe: histórico não mexido.")
            return None
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest().upper() != SHA256[name]:
            print(f"[AVISO] {path.name} do jogo não é o original e não há cópia em workspace\\baseline: "
                  "histórico não mexido.")
            return None
        out.append(data)
    BASELINE.mkdir(parents=True, exist_ok=True)
    for name, data in zip(FILES, out):
        backup(name).write_bytes(data)
    print(f"[OK] cópia do histórico original em {BASELINE}")
    return out


def club_names(game: Path, wanted: set[int] | None = None) -> dict[int, tuple[str, str]]:
    path = BASELINE / "lang_db.original.dat"
    lang = (path if path.exists() else game / "data" / "db" / "lang_db.dat").read_bytes()
    start, end = traducao.sections(lang)[hj.LANG_CLUBS]
    return hj.lang_clubs(lang, start, end, wanted)


def _sheet(path: Path) -> dict[tuple[str, str, str], list[hj.Passage]]:
    rows = openpyxl.load_workbook(path, read_only=True)["Historico"].iter_rows(values_only=True)
    header = next(rows)
    out: dict[tuple[str, str, str], list[hj.Passage]] = defaultdict(list)
    for values in rows:
        row = dict(zip(header, values))
        if not row.get("nome_comum") or not row.get("clube") or not row.get("temporada"):
            continue
        start, end = hj.period(row["temporada"])
        number = (lambda v: int(v) if str(v or "").strip().isdigit() else None)
        out[(row["clube_2026"], row["nome_comum"], str(row.get("nascimento") or "")[:10])].append(hj.Passage(
            start, end, row["clube"], number(row.get("jogos")), number(row.get("gols")),
            str(row.get("emprestimo") or "").strip().lower() in ("sim", "s", "yes")))
    return out


def _careers(path: Path) -> dict[tuple[str, str, str], list[hj.Passage]]:
    out: dict[tuple[str, str, str], list[hj.Passage]] = defaultdict(list)
    if not path.exists():
        return out
    for row in csv.DictReader(path.open(encoding="utf-8-sig")):
        start, end = hj.period(row["temporada"])
        fee = row.get("valor_eur", "")
        out[(row["clube_2026"], row["nome_comum"], row["nascimento"][:10])].append(hj.Passage(
            start, end, row["clube"], None, None, row["emprestimo"] == "sim", int(fee) if fee.isdigit() else None))
    return out


def _with_fees(passages: list[hj.Passage], transfers: list[hj.Passage], clubs: hj.Clubs,
               transfer_clubs: hj.Clubs) -> list[hj.Passage]:
    """Valor de cada chegada (carreiras_2026.csv) nas passagens da planilha: o mesmo clube
    no jogo, começando no mesmo ano ou com um de diferença."""
    fees = [(transfer_clubs.find(t.club)[0], t.start, t.fee) for t in transfers if t.fee and not t.loan]
    out = []
    for p in passages:
        if p.fee is None and not p.loan:
            uid = clubs.find(p.club)[0]
            fee = next((f for club, start, f in fees if uid is not None and club == uid and abs(start - p.start) <= 1),
                       None)
            p = dataclasses.replace(p, fee=fee)
        out.append(p)
    return out


def plan(game: Path, history: hj.History) -> tuple[dict[int, list[hj.Season]], list[dict], list[str]]:
    """(carreira nova por UID, linhas do relatório, avisos)."""
    spec = json.loads(PLAYERS.read_text(encoding="utf-8"))
    shift = spec.get("year_shift", -20)
    careers: dict[int, list[hj.Season]] = {p["uid"]: [] for p in spec["players"]}
    staff = 0
    if STAFF.exists():
        for row in csv.DictReader(STAFF.open(encoding="utf-8-sig")):
            if row.get("uid", "").isdigit():
                careers.setdefault(int(row["uid"]), [])
                staff += 1
    identities = list(csv.DictReader(IDENTITIES.open(encoding="utf-8-sig"))) + estrangeiros.identity_rows()
    uid_of = {r["clube_2026"]: int(r["uid_jogo"]) for r in identities}
    stand_ins = {int(r["uid_jogo"]) for r in identities if r["tipo"] == "substituto"}
    refs = history.club_refs()          # substituto só pelo nome de 2026: "Paraná" não vira o Novorizontino
    names = {uid: pair for uid, pair in club_names(game).items() if uid not in stand_ins}
    by_source = {"planilha": hj.Clubs(names, refs, uid_of),
                 "transferências": hj.Clubs(names, refs, uid_of, strict=True)}   # já vem com o nome de 2026
    by_name = defaultdict(list)
    for player in spec["players"]:
        by_name[(player["club_uid"], player["name"])].append(player)

    found_by: dict[str, dict[int, tuple[dict, str, str, list[hj.Passage]]]] = {}
    warnings, absent = [], 0
    transfers = {**_careers(estrangeiros.CAREERS), **_careers(CAREERS)}   # clubes da CONMEBOL + Brasil
    for source, rows in (("planilha", _sheet(SHEET)), ("transferências", transfers)):
        found_by[source] = {}
        for (club, name, born), passages in rows.items():
            found = by_name.get((uid_of.get(club), name), [])
            found = [p for p in found if p.get("birth_date") == born] or (found if len(found) == 1 else [])
            if found:
                found_by[source].setdefault(found[0]["uid"], (found[0], club, name, passages))
            elif source == "planilha":
                warnings.append(f"{name} ({club}, {born}): não está no elenco montado; sem histórico novo")
            else:
                absent += 1

    report = []
    missing, near = Counter(), set()
    done = {"planilha": 0, "transferências": 0}
    for source, players in found_by.items():
        clubs = by_source[source]
        for uid, (player, club, name, passages) in players.items():
            if source == "transferências" and uid in found_by["planilha"]:
                continue                            # a planilha vem antes das transferências
            if source == "planilha" and uid in found_by["transferências"]:
                passages = _with_fees(passages, found_by["transferências"][uid][3], clubs, by_source["transferências"])
            matches = hj.seasons(passages, clubs, player["club_uid"], shift)
            careers[uid] = hj.merge([s for *_, seasons in matches for s in seasons])
            done[source] += 1
            for passage, club_uid, how, seasons in matches:
                if club_uid is None:
                    missing[hj.clean(passage.club)] += 1
                elif how == "aproximado":
                    near.add(f"{hj.clean(passage.club)} -> {clubs.names[club_uid][0]}")
                report.append({"jogador": name, "clube_2026": club, "uid": uid, "fonte": source,
                               "temporada": passage.label, "clube": passage.club,
                               "emprestimo": "sim" if passage.loan else "",
                               "jogos": passage.apps, "gols": passage.goals, "valor_eur": passage.fee or "",
                               "clube_no_jogo": (hj.BRAZIL.get(hj.clean(passage.club), hj.clean(passage.club))
                                                 if how == "brasil" else clubs.names.get(club_uid, ("",))[0]),
                               "uid_clube": club_uid or "", "casou_por": how,
                               "temporadas_no_jogo": " ".join(f"{s.year - shift}:{s.apps}/{s.goals}" for s in seasons)})
    rest = len(spec["players"]) - sum(done.values())
    print(f"[OK] histórico: {done['planilha']} jogadores com a carreira da planilha, {done['transferências']} "
          f"com os clubes das transferências; os outros {rest} jogadores de 2026 e {staff} da comissão ficam "
          "sem a carreira do jogador de 2005 que ocupam")
    if absent:
        print(f"[INFO] {absent} jogadores da carreiras_2026.csv não estão no elenco montado (sem vaga)")
    if missing:
        passages_out = sum(missing.values())
        top = ", ".join(f"{club} ({n})" for club, n in missing.most_common(12))
        warnings.append(f"{len(missing)} clubes ({passages_out} passagens) não existem no banco de 2005 e ficam de "
                        f"fora; os mais comuns: {top}. Lista em {MISSING.relative_to(ROOT)}")
    if near:
        print(f"[CONFIRA] {len(near)} clubes achados por aproximação (lista em {REPORT.relative_to(ROOT)}, "
              "casou_por = aproximado)")
    if missing:
        MODS.mkdir(parents=True, exist_ok=True)
        with MISSING.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["clube", "passagens"])
            writer.writerows(missing.most_common())
    return careers, report, warnings


def apply(game: Path, write: bool) -> None:
    data = originals(game)
    if data is None:
        return
    if not PLAYERS.exists():
        print(f"[AVISO] falta {PLAYERS.relative_to(ROOT)} (rode o montar_elencos.py): histórico não mexido.")
        return
    history = hj.History(*data)
    careers, report, warnings = plan(game, history)
    for warning in warnings:
        print("[AVISO]", warning)
    if not write:
        return
    history.replace(careers)
    for name, content in zip(FILES, history.files()):
        game_file(game, name).write_bytes(content)
    MODS.mkdir(parents=True, exist_ok=True)
    if report:
        with REPORT.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(report[0]))
            writer.writeheader()
            writer.writerows(report)
    print(f"[OK] gravados pl_hist_index.dat, pl_hist_id.dat e pl_hist_dt.dat em {game / 'data' / 'db'} "
          f"(lista em {REPORT.relative_to(ROOT)})")


def restore(game: Path) -> None:
    if all(backup(n).exists() for n in FILES):
        for name in FILES:
            shutil.copy2(backup(name), game_file(game, name))
        print("[OK] histórico de carreira original restaurado")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    game = game_dir()
    if args.restore:
        restore(game)
        return
    apply(game, args.apply)
    if not args.apply:
        print("\nSimulação. Para gravar, feche o jogo e rode de novo com --apply.")


if __name__ == "__main__":
    main()
