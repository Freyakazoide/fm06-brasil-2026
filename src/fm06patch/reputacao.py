"""Reputação dos substitutos (TEAM+0x6C, u16 no registro "0A 00" + 3).

O substituto herda a reputação do clube do FM06 que ele ocupa (Athletic na
Série B com a do São Caetano, 7100). Passa a ter a mediana dos clubes
equivalentes da mesma série; se só joga estadual, a dos equivalentes do
estado. Nunca sobe a reputação original, a não ser no clube novo (clubes_novos.py), que vem
com a do clube molde (o de menor reputação do estado) e vai para a mediana.
"""

from __future__ import annotations

import struct
from statistics import median

from .server_teams import is_new


def plan(placements, states) -> dict[int, tuple[int, int, str]]:
    """offset do registro -> (reputação antiga, nova, clube de 2026)."""
    by_serie: dict[str, list[int]] = {}
    for p in placements:
        if p.kind == "equivalente":
            by_serie.setdefault(p.serie, []).append(p.team.reputation)
    by_uf: dict[str, list[int]] = {}
    for e in states:
        if not e.substitute and not is_new(e.team):
            by_uf.setdefault(e.uf, []).append(e.team.reputation)
    changes: dict[int, tuple[int, int, str]] = {}
    national = set()
    for p in placements:
        national.add(p.team.club_uid)
        if p.kind in ("substituto", "novo") and p.clube:      # o novo vem com a reputação do copiado
            target = int(median(by_serie[p.serie]))
            if target < p.team.reputation or p.kind == "novo":
                changes[p.team.offset] = (p.team.reputation, target, p.clube)
    for e in states:
        if (e.substitute or is_new(e.team)) and e.team.club_uid not in national and by_uf.get(e.uf):
            target = int(median(by_uf[e.uf]))
            if target < e.team.reputation or is_new(e.team):
                changes[e.team.offset] = (e.team.reputation, target, e.clube)
    return changes


def apply(data: bytes, changes: dict[int, tuple[int, int, str]]) -> bytes:
    out = bytearray(data)
    for offset, (_, value, _) in changes.items():
        struct.pack_into("<H", out, offset + 3, value)
    return bytes(out)
