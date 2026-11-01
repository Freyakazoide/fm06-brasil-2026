"""Monta data/brasil/clubes/clubes_novos_2026.csv: um clube novo para cada substituto (ficha C13).

    python scripts\\montar_clubes_novos.py            (simulação: mostra a lista)
    python scripts\\montar_clubes_novos.py --apply    (grava a planilha e a equivalencias_fm06.csv)

Os substitutos vêm da identidade_fm06.csv da última instalação (tipo "substituto", com nome; as
vagas extras ficam como estão). O nome completo vem da clubes_master.xlsx / clubes_faltando.xlsx.
O clube copiado (molde) é, em cada UF, o time brasileiro de menor reputação que está no
estadual da UF e tem o formato simples (clubes_novos.parse_team): o molde só dá a nação, a
cidade e a região, não é ocupado. Linhas que já estão na planilha ficam. Clube das séries
ganha na equivalencias_fm06.csv o próprio nome (é por ele que o brasil_2026.plan acha o clube
novo); o clube com homônimo de outro estado no FM06 (Floresta, Barra...) leva a UF no nome
curto do banco ("Floresta-CE"), e o .lnc do gerar_graficos mostra o nome de 2026. Substituto que já existe no banco com o nome (os 24 clubes que a busca perdia até 01/11,
como o Luverdense) não vira clube novo. Depois: aplicar_tudo.py completo (os elencos mudam).
"""

from __future__ import annotations

import argparse
import csv
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import clubes_novos, cores, server_teams  # noqa: E402
from fm06patch.estaduais import ID as FIRST_ID  # noqa: E402
from fm06patch.estaduais_clubes import LOWER_ID, STATE_FIELD, comp_index, normalize  # noqa: E402

CLUBES = ROOT / "data" / "brasil" / "clubes"
IDENTITY = CLUBES / "identidade_fm06.csv"
EQUIVALENTS = ROOT / "data" / "brasil" / "equivalencias_fm06.csv"
SERVER = ROOT / "workspace" / "baseline" / "server_db.original.dat"
FIELDS = ["clube_2026", "nome_longo", "uf", "doador_uid"]


def full_names() -> dict[str, str]:
    out = {}
    for sheet in ("clubes_master.xlsx", "clubes_faltando.xlsx"):
        for row in cores.sheet(CLUBES / sheet):
            out[row["clube"]] = row.get("nome_completo_2026") or row.get("nome_curto_2026") or row["clube"]
    return out


def templates(data: bytes) -> dict[str, int]:
    """UF -> UID do clube molde: o time de menor reputação no estadual da UF, com o formato
    simples e o registro do clube legível pelo clone."""
    clubs, teams = clubes_novos.club_list(data), clubes_novos.team_list(data)
    uf_of = {comp_index(data, cid): uf for uf, cid in FIRST_ID.items()}
    uf_of.update({comp_index(data, cid): uf for uf, cid in LOWER_ID.items()})
    best: dict[str, tuple[int, int]] = {}
    for i in range(len(teams.ends)):
        start = teams.start(i)
        if data[start] != 10:
            continue
        uf = uf_of.get(struct.unpack_from("<I", data, start + STATE_FIELD)[0])
        team = clubes_novos.parse_team(data, start, teams.end(i)) if uf else None
        if team is None or team.end - team.tail_at != 57:
            continue
        club = struct.unpack_from("<I", data, team.end - 8 - clubes_novos.TEAM_CLUB)[0]
        reputation = struct.unpack_from("<H", data, start + 3)[0]
        if club >= len(clubs.ends) or (uf in best and reputation >= best[uf][0]):
            continue
        try:                                            # o clone precisa achar nomes e listas do fim
            clubes_novos.club_names(data, clubs.start(club), clubs.ends[club])
            clubes_novos.club_lists(data, clubs.start(club), clubs.ends[club])
        except ValueError:
            continue
        best[uf] = (reputation, clubs.uid(data, club))
    return {uf: uid for uf, (_, uid) in best.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    data = SERVER.read_bytes()
    molds = templates(data)
    names = full_names()
    rows = {}
    if clubes_novos.SHEET.exists():
        rows = {r["clube_2026"]: r for r in csv.DictReader(clubes_novos.SHEET.open(encoding="utf-8-sig"))}
    seen = {struct.unpack("<I", m.group(2))[0]                   # o que a busca via até 01/11
            for m in server_teams._CLUB_HEADER.finditer(data, 0, server_teams.BRAZIL_END)}
    brazil = server_teams.find_brazil_teams(data)
    existing = {normalize(t.short_name) for t in brazil if t.club_uid not in seen}
    taken = {normalize(t.short_name) for t in brazil}
    equivalent = {r["clube"]: r["fm06"] for r in csv.DictReader(EQUIVALENTS.open(encoding="utf-8-sig"))}
    series = set()
    for ident in csv.DictReader(IDENTITY.open(encoding="utf-8-sig")):
        if ident["tipo"] != "substituto" or not ident["clube_2026"]:
            continue
        club, uf = ident["clube_2026"], ident["uf"]
        if "Série" in ident["onde"]:
            series.add(club)
        if normalize(equivalent.get(club) or club) in existing:     # escondido até 01/11 (Luverdense)
            print(f"[JÁ EXISTE] {club}: fica o clube do banco")
            continue
        if club not in rows and uf in molds:
            short = club                                # homônimo de outro estado no FM06: com a UF
            if normalize(club) in taken and not club.endswith(f"-{uf}"):
                short = f"{club}-{uf}"
            rows[club] = {"clube_2026": short, "nome_longo": names.get(club, club), "uf": uf,
                          "doador_uid": str(molds[uf])}
    for row in rows.values():
        print(f"{row['uf']}  {row['clube_2026']:28} {row['nome_longo']:44} molde {row['doador_uid']}")
    print(f"{len(rows)} clubes novos ({len(series)} das séries)")
    if not args.apply:
        print("(simulação: rode com --apply para gravar)")
        return
    with clubes_novos.SHEET.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(sorted(rows.values(), key=lambda r: (r["uf"], r["clube_2026"])))
    lines = list(csv.DictReader(EQUIVALENTS.open(encoding="utf-8-sig")))
    short_of = {club: row["clube_2026"] for club, row in rows.items()}
    for line in lines:
        if line["clube"] in series and not line["fm06"] and line["clube"] in short_of:
            line["fm06"] = short_of[line["clube"]]
    with EQUIVALENTS.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["clube", "estado", "fm06"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(lines)
    print(f"[OK] gravado {clubes_novos.SHEET} e {EQUIVALENTS}")


if __name__ == "__main__":
    main()
