"""Rivais dos clubes brasileiros no server_db.dat (lista de relações do registro do clube).

No fim do registro do clube (ver server_teams.club_pairs):

    u8 n, n x u32 times do clube (índice na lista de times: Flamengo 290)
    u8 m, m x relação de 8 bytes: u8 tipo, u8 relação, u16 peso, u32 referência
    18 bytes
    u32 índice do clube (o par que fecha o registro)

Tipo 1 relação 5 é clube rival: a referência é o índice do clube e o peso vai de 15 a
101 (Flamengo: Vasco 90, Fluminense 80, Botafogo 70; Gre-Nal 101). Tipo 3 são pessoas
(relação 1 querida, 2 não querida). Conferido nos 695 clubes brasileiros do banco 6.0.2
(693 com a lista de times logo antes; os outros dois ficam como estão). O server_db é
lido em sequência: a lista pode crescer.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass

from .server_teams import _CLUB_TAIL, _DATES, _string

RIVAL = (1, 5)
TAIL = 18
LEVEL = {3: 90, 2: 75, 1: 60}       # intensidade da planilha -> peso


@dataclass
class Club:
    uid: int                        # UID verdadeiro (o do jogo)
    index: int                      # índice do clube (a referência das relações)
    name: str                       # nome curto no banco
    count_at: int                   # posição do u8 m
    relations: list[tuple[int, int, int, int]]

    def rivals(self) -> dict[int, int]:
        return {ref: level for kind, sub, level, ref in self.relations if (kind, sub) == RIVAL}


def _teams_before(data: bytes, count_at: int) -> bool:
    """A lista de times (u8 n, n x u32) termina logo antes do u8 m."""
    for n in range(1, 8):
        at = count_at - 4 * n - 1
        if data[at] == n and all(struct.unpack_from("<I", data, at + 1 + 4 * i)[0] < 100_000 for i in range(n)):
            return True
    return False


def read(data: bytes) -> dict[int, Club]:
    """UID verdadeiro -> relações, para os clubes brasileiros."""
    starts = [m.start() - 4 for m in re.finditer(re.escape(_CLUB_TAIL), data) if m.start() >= 8]
    clubs: dict[int, Club] = {}
    for start, following in zip(starts, starts[1:] + [len(data)]):
        mark = data.find(_DATES, start, min(start + 0x600, following))
        if mark < 0:
            continue
        own = struct.unpack_from("<I", data, start - 4)[0] + 1
        short = following - start <= 0x2000
        if short and struct.unpack_from("<I", data, following - 4)[0] == own:
            at = following - 4
        else:                       # registro que traz outros clubes depois (server_teams.club_pairs)
            at = data.find(struct.pack("<I", own), mark, following if short else start + 0x2000)
            if at < 0:
                continue
        uid = struct.unpack_from("<I", data, at + 4)[0]
        end, first = at - TAIL, at - TAIL
        while first - 8 > mark and 1 <= data[first - 8] <= 9:
            first -= 8
        for count_at in range(first - 1, end):
            size = (end - count_at - 1) // 8
            if (end - count_at - 1) % 8 == 0 and data[count_at] == size and _teams_before(data, count_at):
                long_name, after = _string(data, mark + len(_DATES))
                short_name, _ = _string(data, after)
                relations = [struct.unpack_from("<BBHI", data, count_at + 1 + 8 * i) for i in range(size)]
                clubs.setdefault(uid, Club(uid, own, short_name or long_name, count_at, relations))
                break
    return clubs


def plan(clubs: dict[int, Club], pairs: list[tuple[int, int, int]], clear: set[int] = frozenset()
         ) -> dict[int, list[tuple[int, int, int, int]]]:
    """Relações novas por UID, a partir de (UID, UID do rival, intensidade 1-3).

    Vale nos dois sentidos. Rival que já existe ganha o peso da intensidade (a 3 não
    baixa um peso maior, como o Gre-Nal 101); rival novo entra no fim; o resto da lista
    (outros rivais, pessoas) fica como está. Os clubes de ``clear`` (substitutos: o
    registro de 2005 virou outro clube) perdem os rivais de 2005, nos dois sentidos:
    o Paraná virou o Novorizontino, que não é rival do Athletico."""
    wanted: dict[int, dict[int, int]] = {}
    for a, b, level in pairs:
        if a in clubs and b in clubs and a != b:
            for x, y in ((a, b), (b, a)):
                wanted.setdefault(x, {})
                wanted[x][clubs[y].index] = max(wanted[x].get(clubs[y].index, 0), level)
    void = {clubs[u].index for u in clear if u in clubs}
    changes = {}
    for uid, club in clubs.items():
        rivals, relations, done = wanted.get(uid, {}), [], set()
        for kind, sub, level, ref in club.relations:
            if (kind, sub) == RIVAL:
                if ref in rivals:
                    new = LEVEL[rivals[ref]]
                    level = max(level, new) if rivals[ref] == 3 else new
                    done.add(ref)
                elif uid in clear or ref in void:
                    continue
            relations.append((kind, sub, level, ref))
        relations += [(*RIVAL, LEVEL[level], ref) for ref, level in rivals.items() if ref not in done]
        if relations != club.relations and len(relations) < 256:
            changes[uid] = relations
    return changes


def apply(data: bytes, clubs: dict[int, Club], changes: dict[int, list[tuple[int, int, int, int]]]) -> bytes:
    out = bytearray(data)
    for uid in sorted(changes, key=lambda u: -clubs[u].count_at):     # de trás para frente
        club, relations = clubs[uid], changes[uid]
        old_end = club.count_at + 1 + 8 * len(club.relations)
        out[club.count_at:old_end] = bytes([len(relations)]) + b"".join(struct.pack("<BBHI", *r) for r in relations)
    return bytes(out)


def load_sheet(path, uid_of: dict[str, int], fm06: dict[str, int]) -> tuple[list[tuple[int, int, int]], list[str]]:
    """Aba Rivais de data/modelos/clubes_estrutura_2026.xlsx -> ([(UID, UID do rival, intensidade)],
    nomes que não estão no jogo). Nome de 2026 (identidade_fm06) ou, fora de 2026, o nome
    curto do banco ("Paraná")."""
    import openpyxl

    rows = openpyxl.load_workbook(path, read_only=True)["Rivais"].iter_rows(values_only=True)
    header = [str(h or "") for h in next(rows)]
    pairs, missing = [], []
    for values in rows:
        row = dict(zip(header, values))
        names = [str(row.get(k) or "").strip() for k in ("clube", "rival")]
        level = int(row["intensidade"]) if str(row.get("intensidade") or "").strip() in ("1", "2", "3") else 2
        if not all(names):
            continue
        uids = [uid_of.get(n, fm06.get(n)) for n in names]
        missing += [n for n, u in zip(names, uids) if u is None]
        if None not in uids:
            pairs.append((uids[0], uids[1], level))
    return pairs, sorted(set(missing))
