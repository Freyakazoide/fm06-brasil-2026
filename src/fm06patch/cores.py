"""Cores de 2026 dos clubes no server_db.dat (tela do clube e uniforme da partida).

No registro do clube, logo depois do nome curto: u8 N e N conjuntos de 7 bytes
(u16 cor 1, u16 cor 2, u16 cor 3, u8 padrão), cores em RGB555. Conjunto 0 =
uniforme 1 (a tela do clube usa cor 1 no texto e cor 2 no fundo: Flamengo
preto sobre vermelho, São Caetano branco sobre azul 0x0090), conjunto 1 =
uniforme 2. Padrão: 01 lisa, 03 listras verticais (Atlético Mineiro), 0D
listras horizontais (Flamengo). O COLOUR_CHANGE do .lnc (0x00AAA1B0) grava o
mesmo conjunto em memória: cor 1, cor 2 e cor 2.

As cores vêm de data/brasil/clubes/uniformes_2026.xlsx: fundo = camisa, frente =
secundária (ou branco/preto quando ela não contrasta).
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

from .estaduais_clubes import same_club
from .server_teams import _CLUB_TAIL, _DATES, _string

UNIFORMES = Path(__file__).resolve().parents[2] / "data" / "brasil" / "clubes" / "uniformes_2026.xlsx"
# nome nas séries/estaduais -> nome na planilha de uniformes
KIT_ALIASES = {"Parnamirim/ABC-D": "Parnamirim", "Gazin Porto Velho": "Porto Velho"}
PATTERNS = {"lisa": 0x01, "listras verticais": 0x03, "listras verticais finas": 0x03, "listras horizontais": 0x0D}


def rgb(hex_color: str | None, default: str = "#FFFFFF") -> tuple[int, int, int]:
    value = (hex_color or default).strip().lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def luma(color) -> float:
    return 0.3 * color[0] + 0.59 * color[1] + 0.11 * color[2]


def contrast(color) -> tuple[int, int, int]:
    return (255, 255, 255) if luma(color) < 150 else (20, 20, 20)


def rgb555(color) -> int:
    r, g, b = color
    return (r >> 3) << 10 | (g >> 3) << 5 | (b >> 3)


def sheet(path: Path) -> list[dict]:
    import openpyxl

    rows = openpyxl.load_workbook(path, read_only=True).worksheets[0].iter_rows(values_only=True)
    header = next(rows)
    return [dict(zip(header, row)) for row in rows if row[header.index("clube")]]


def kit_rows(identities: list[dict], kits: list[dict]) -> dict[int, dict]:
    """UID do jogo -> linha de uniformes_2026 (nome igual primeiro, depois nome parecido).
    identities: uid_jogo, clube_2026, uf (identidade_fm06.csv)."""
    found: dict[int, dict] = {}
    free = list(kits)
    for exact in (True, False):
        for ident in identities:
            uid = int(ident["uid_jogo"])
            if uid in found:
                continue
            name, uf = KIT_ALIASES.get(ident["clube_2026"], ident["clube_2026"]), ident["uf"]
            for row in free:
                if row["uf"] not in (None, "", uf):
                    continue
                if row["clube"] == name if exact else same_club(row["clube"], name, uf):
                    found[uid] = row
                    free.remove(row)
                    break
    return found


def club_colours(row: dict) -> list[tuple[int, tuple, tuple, int]]:
    """(conjunto, frente, fundo, padrão) dos uniformes 1, 2 e 3."""
    sets = []
    for index, n in enumerate((1, 2, 3)):
        if not row.get(f"uni{n}_camisa"):
            continue
        back = rgb(row[f"uni{n}_camisa"])
        front = rgb(row.get(f"uni{n}_secundaria") or row.get(f"uni{n}_detalhes"), "#FFFFFF")
        if abs(luma(front) - luma(back)) < 70:
            front = contrast(back)
        sets.append((index, front, back, PATTERNS.get((row.get(f"uni{n}_modelo") or "lisa").strip().lower(), 0x01)))
    return sets


def colour_sets(data: bytes) -> dict[int, tuple[int, int]]:
    """UID do repositório -> (posição do u8 N, N)."""
    starts = [m.start() - 4 for m in re.finditer(re.escape(_CLUB_TAIL), data) if m.start() >= 8]
    found = {}
    for start, following in zip(starts, starts[1:] + [len(data)]):
        mark = data.find(_DATES, start, min(start + 0x600, following))
        if mark < 0:
            continue
        long_name, after = _string(data, mark + len(_DATES))
        if not long_name:
            continue
        _, at = _string(data, after)
        if 1 <= data[at] <= 4:
            found.setdefault(struct.unpack_from("<I", data, start)[0], (at, data[at]))
    return found


def apply(data: bytes, colours: dict[int, list]) -> tuple[bytes, int]:
    """colours: UID do repositório -> club_colours(). Devolve (banco, nº de clubes)."""
    out = bytearray(data)
    sets = colour_sets(data)
    done = 0
    for repo_uid, values in colours.items():
        if repo_uid not in sets:
            continue
        at, count = sets[repo_uid]
        for index, front, back, pattern in values:
            if index < count:
                struct.pack_into("<HHHB", out, at + 1 + 7 * index, rgb555(front), rgb555(back), rgb555(back), pattern)
        done += 1
    return bytes(out), done


def plan(identities, path: Path = UNIFORMES) -> dict[int, list]:
    """Cores de 2026 dos substitutos (UID do repositório -> conjuntos)."""
    rows = kit_rows([{"uid_jogo": i.uid, "clube_2026": i.clube, "uf": i.uf} for i in identities], sheet(path))
    return {i.repo_uid: club_colours(rows[i.uid]) for i in identities if i.tipo == "substituto" and i.uid in rows}
