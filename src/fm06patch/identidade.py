"""Quem é cada clube do FM06 em 2026 (um clube do jogo = um clube de 2026).

Junta as séries (brasil_2026.plan) e os estaduais (estaduais_clubes.plan): o
nome de 2026 vem da série; se o clube não está numa série, do estadual; vaga
extra da Série D sem clube de 2026 fica com o nome do FM06. O UID do jogo
(CLUB+0x14, o dos gráficos e do .lnc) é o do registro seguinte ao do
repositório (server_teams.true_uids).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .estaduais_clubes import uf_of
from .server_teams import true_uids


@dataclass
class Identity:
    uid: int            # UID do jogo
    repo_uid: int       # UID do repositório (mapa_2026.csv)
    clube: str          # nome de 2026
    uf: str
    fm06: str           # nome original no FM06
    tipo: str           # equivalente / substituto
    onde: str           # "Série A", "estadual SP"...


def build(data: bytes, placements, states) -> list[Identity]:
    uids = true_uids(data)
    found: dict[int, Identity] = {}
    for p in placements:
        if p.clube:
            found[p.team.club_uid] = Identity(uids[p.team.club_uid], p.team.club_uid, p.clube, uf_of(p.estado),
                                              p.team.short_name, p.kind, f"Série {p.serie}")
    for e in states:
        known = found.get(e.team.club_uid)
        if known is None:
            found[e.team.club_uid] = Identity(uids[e.team.club_uid], e.team.club_uid, e.clube, e.uf,
                                              e.team.short_name,
                                              "substituto" if e.substitute else "equivalente", f"estadual {e.uf}")
        else:
            known.onde += f", estadual {e.uf}"
    for p in placements:
        if p.clube:
            continue
        if p.team.club_uid in found:
            found[p.team.club_uid].onde = f"Série {p.serie} (vaga extra), " + found[p.team.club_uid].onde
        else:
            found[p.team.club_uid] = Identity(uids[p.team.club_uid], p.team.club_uid, p.team.short_name, "",
                                              p.team.short_name, "vaga extra", f"Série {p.serie}")
    return sorted(found.values(), key=lambda i: (i.onde, i.clube))


def write_report(path: Path, identities: list[Identity]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["uid_jogo", "uid_repo", "clube_2026", "uf", "fm06_nome", "tipo", "onde"])
        for i in identities:
            writer.writerow([i.uid, i.repo_uid, i.clube, i.uf, i.fm06, i.tipo, i.onde])


def read_report(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))
