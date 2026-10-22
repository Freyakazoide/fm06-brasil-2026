"""Histórico de carreira (aba Histórico) dos jogadores de 2026: data/db/pl_hist_*.dat.

    python scripts\\aplicar_historico.py            (simulação: mostra o que faria)
    python scripts\\aplicar_historico.py --apply    (grava; o jogo tem de estar fechado)
    python scripts\\aplicar_historico.py --restore  (volta o original)

Rodar depois do montar_elencos.py (e do aplicar_comissao.py) e antes do New Game em que
os nomes entram: o jogo lê o histórico no New Game.
- quem está em data/modelos/historico_carreira.xlsx ganha a carreira de verdade (jogos
  e gols de cada passagem repartidos por igual entre as temporadas dela);
- os outros jogadores de 2026 e a comissão de 2026 perdem a carreira do jogador de 2005
  que ocupam (fica só a temporada atual);
- os jogadores de 2005 que sobram (nome de hoje) ficam com a carreira que tinham.
Parte sempre do original (cópias em workspace/baseline/pl_hist_*.original.dat). Lista
do que entrou em workspace/mods/historico_2026.csv.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import historico_jogadores as hj, traducao  # noqa: E402

FILES = ("index", "id", "dt")
SHA256 = {"index": "3FD46578A293D8B2AD99297F71BD19387A6B144AC95793F20309B9CC3503FB53",   # 6.0.2
          "id": "873E5442F3F8B99FDE7BAB6DFB1300D50FC5740BF1E977FCC4C004E8D8AE015B",
          "dt": "D8EC837EA720F4F8E117037BFFAE0322EEC1C9DC014890ECBA87FEAAEAB4CE18"}
BASELINE = ROOT / "workspace" / "baseline"
MODS = ROOT / "workspace" / "mods"
SHEET = ROOT / "data" / "modelos" / "historico_carreira.xlsx"
IDENTITIES = ROOT / "data" / "brasil" / "clubes" / "identidade_fm06.csv"
PLAYERS = MODS / "brasil_2026_jogadores.json"           # do montar_elencos.py
STAFF = MODS / "comissao_2026_hospedeiros.csv"          # do aplicar_comissao.py
REPORT = MODS / "historico_2026.csv"


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


def club_names(game: Path, wanted: set[int]) -> dict[int, tuple[str, str]]:
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
    uid_of = {r["clube_2026"]: int(r["uid_jogo"]) for r in csv.DictReader(IDENTITIES.open(encoding="utf-8-sig"))}
    refs = history.club_refs()
    clubs = hj.Clubs(club_names(game, set(refs)), refs, uid_of)
    by_name = defaultdict(list)
    for player in spec["players"]:
        by_name[(player["club_uid"], player["name"])].append(player)

    report, warnings, done = [], [], 0
    missing, near = set(), set()
    for (club, name, born), passages in _sheet(SHEET).items():
        found = by_name.get((uid_of.get(club), name), [])
        found = [p for p in found if p.get("birth_date") == born] or (found if len(found) == 1 else [])
        if not found:
            warnings.append(f"{name} ({club}, {born}): não está no elenco montado; sem histórico novo")
            continue
        player = found[0]
        matches = hj.seasons(passages, clubs, player["club_uid"], shift)
        careers[player["uid"]] = hj.merge([s for *_, seasons in matches for s in seasons])
        done += 1
        for passage, uid, how, seasons in matches:
            if uid is None:
                missing.add(hj.clean(passage.club))
            elif how == "aproximado":
                near.add(f"{hj.clean(passage.club)} -> {clubs.names[uid][0]}")
            report.append({"jogador": name, "clube_2026": club, "uid": player["uid"], "temporada": passage.label,
                           "clube": passage.club, "emprestimo": "sim" if passage.loan else "",
                           "jogos": passage.apps, "gols": passage.goals,
                           "clube_no_jogo": (hj.BRAZIL.get(hj.clean(passage.club), hj.clean(passage.club))
                                             if how == "brasil" else clubs.names.get(uid, ("",))[0]),
                           "uid_clube": uid or "", "casou_por": how,
                           "temporadas_no_jogo": " ".join(f"{s.year - shift}:{s.apps}/{s.goals}" for s in seasons)})
    print(f"[OK] histórico: {done} jogadores com a carreira da planilha; os outros "
          f"{len(spec['players']) - done} jogadores de 2026 e {staff} da comissão ficam sem a carreira "
          "do jogador de 2005 que ocupam")
    if missing:
        warnings.append(f"{len(missing)} clubes da planilha não existem no banco de 2005 (a passagem fica de fora): "
                        + ", ".join(sorted(missing)))
    if near:
        print("[CONFIRA] clubes achados por aproximação: " + "; ".join(sorted(near)))
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
