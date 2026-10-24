"""Clubes de 2026 dos outros países da CONMEBOL (primeira divisão), sobre os clubes do FM06.

Os dados vêm do Sofascore pelo scripts/coletar_estrangeiros.py (no PC de quem joga) e
ficam em data/estrangeiros:

- identidade_estrangeiros.csv: clube de 2026 -> clube do FM06 (UID do jogo, o mesmo
  formato da data/brasil/clubes/identidade_fm06.csv, tipo "estrangeiro");
- jogadores_estrangeiros_2026.xlsx: os elencos, no formato da jogadores_2026.xlsx;
- tecnicos_estrangeiros_2026.csv: o técnico de cada clube;
- carreiras_estrangeiros_2026.csv: as carreiras pelas transferências.

O nome do clube de 2026 leva o país ("River Plate (ARG)", "Nacional (URU)"): há clubes de
2026 com o mesmo nome no Brasil e em mais de um país. Clube de 2026 que não existe no
FM06 fica de fora (sem substituto). Os scripts do mod leem estes arquivos junto com os
do Brasil (montar_elencos, reforcar_elencos, aplicar_comissao, aplicar_historico).
"""

from __future__ import annotations

import csv
import re
import struct
from pathlib import Path

from . import elenco_times, people_contracts
from . import historico_jogadores as hj
from .server_teams import _DATES, _string, club_pairs

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "estrangeiros"
IDENTITIES = DATA / "identidade_estrangeiros.csv"
PLAYERS = DATA / "jogadores_estrangeiros_2026.xlsx"
COACHES = DATA / "tecnicos_estrangeiros_2026.csv"
CAREERS = DATA / "carreiras_estrangeiros_2026.csv"
BR_IDENTITIES = ROOT / "data" / "brasil" / "clubes" / "identidade_fm06.csv"
BR_PLAYERS = ROOT / "data" / "brasil" / "jogadores" / "jogadores_2026.xlsx"

# país (alpha2 do Sofascore) -> (código da nação no banco, sigla, nome, "série" do CA)
NATIONS = {
    "AR": (0xBB, "ARG", "Argentina", "A"),
    "UY": (0xC3, "URU", "Uruguai", "B"),
    "CO": (0xBF, "COL", "Colômbia", "B"),
    "PY": (0xC1, "PAR", "Paraguai", "B"),
    "EC": (0xC0, "ECU", "Equador", "B"),
    "CL": (0xBE, "CHI", "Chile", "B"),
    "PE": (0xC2, "PER", "Peru", "C"),
    "BO": (0xBC, "BOL", "Bolívia", "C"),
    "VE": (0xC4, "VEN", "Venezuela", "C"),
}
FIELDS = ["clube_2026", "pais", "uid_jogo", "uid_repo", "fm06_nome", "tipo", "onde", "sofascore_id", "sofascore_nome"]
# uid_repo: o "UID do repositório" (server_teams.club_pairs), usado para achar o registro do clube


def display_name(name: str, alpha2: str) -> str:
    return f"{name} ({NATIONS[alpha2][1]})"


def _closing_pairs(server: bytes, nation: int) -> list[tuple[int, int, int, int]]:
    """Os clubes que o server_teams.club_pairs perde quando o índice do clube (ou o
    anterior) é o próprio código de uma nação: Bolívar é o 188 (0xBC) e The Strongest o 189
    (0xBD), e o "00 + nação" achado no par (índice, UID) parte o registro no lugar errado.
    Aqui o par que fecha o registro é o (índice, UID) seguido do começo de outro clube
    (00 + nação, com o marcador de datas logo depois)."""
    out = []
    for match in re.finditer(re.escape(b"\x00" + struct.pack("<I", nation)), server):
        start = match.start() - 4
        mark = server.find(_DATES, start, start + 0x600) if start >= 4 else -1
        if mark < 0:
            continue
        repo = struct.unpack_from("<I", server, start)[0]
        own = struct.unpack_from("<I", server, start - 4)[0] + 1
        if not 1 < own < people_contracts.MAX_CLUB_INDEX:
            continue
        closing = re.compile(re.escape(struct.pack("<I", own)) + rb"(....)\x00.\x00\x00\x00", re.S)
        for found in closing.finditer(server, mark, mark + 0x2000):
            if server.find(_DATES, found.start() + 4, found.start() + 0x604) >= 0:
                out.append((repo, own, struct.unpack("<I", found.group(1))[0], mark))
                break
    return out


def fm06_clubs(server: bytes, alpha2: str, brazil: set[int] = frozenset()) -> list[dict]:
    """Clubes do FM06 do país: UID do jogo, UID do repositório, índice e nomes. O par
    "00 + nação" também aparece por acaso em outros registros (belgas, brasileiros, o EC
    0xC0 em números quaisquer): em todos os clubes de verdade dos 10 países da CONMEBOL o
    UID do repositório é menor que o do jogo e não zero, o que tira os falsos; os
    brasileiros (``brazil``) ficam de fora."""
    pairs = club_pairs(server, NATIONS[alpha2][0])
    known = {index for _, index, _, _ in pairs}
    pairs += [p for p in _closing_pairs(server, NATIONS[alpha2][0]) if p[1] not in known]
    out = []
    for repo, index, uid, mark in pairs:
        if (uid in brazil or not 0 < repo < uid < people_contracts.MAX_UID
                or not 1 < index < people_contracts.MAX_CLUB_INDEX):
            continue
        long_name, after = _string(server, mark + len(_DATES))
        short_name, _ = _string(server, after)
        if long_name:
            out.append({"uid": uid, "repo": repo, "index": index, "long": long_name, "short": short_name or long_name})
    return out


# nomes do Sofascore que não casam sozinhos -> nome (longo ou curto) do clube no FM06
ALIASES = {
    "AR": {"Gimnasia y Esgrima": "Gimnasia y Esgrima de La Plata", "Gimnasia La Plata": "Gimnasia y Esgrima de La Plata",
           "Gimnasia y Esgrima LP": "Gimnasia y Esgrima de La Plata",
           "Gimnasia Mendoza": "Gimnasia y Esgrima de Mendoza",
           "Independiente Rivadavia": "Independiente Rivadavia de Mendoza"},
    "BO": {"GV San José": "C San José"},
    "CL": {"Deportes Iquique": "CD Municipal Iquique"},
    "CO": {"Alianza FC": "Alianza Petrolera AS", "Junior Barranquilla": "CPD Junior",
           "Internacional de Bogotá": "CD La Equidad S"},       # a La Equidad com o nome de 2025
    "EC": {"Universidad Católica": "CDU Católica"},
    "PY": {"Nacional Asunción": "C Nacional FC"},
    "VE": {"Universidad Central": "UC de Venezuela"},
}
# o que o nome do Sofascore pode ter a mais que o do FM06 ("Deportes Tolima" e "Tolima")
_PREFIXES = {"deportes", "deportivo", "atletico", "independiente", "sociedad", "corporacion", "asociacion",
             "sport", "sporting", "fbc", "ad", "sd", "cs"}


def _keys(club: dict) -> set[frozenset[str]]:
    """O nome longo e o curto, com e sem o país ou a cidade entre parênteses."""
    names = {club["long"], club["short"]}
    return {hj._key(n) for n in names | {re.sub(r"\s*\(.*?\)", "", n) for n in names} if n.strip()}


def match(name: str, clubs: list[dict], aliases: dict[str, str | int] | None = None) -> tuple[dict | None, str]:
    """(clube do FM06, como casou: apelido, nome ou aproximado) do nome do Sofascore.

    Pelo nome todo (sem "Club", "CA", "FC"...) igual ao longo ou ao curto; senão, um só
    clube cujo nome tem o do Sofascore e mais só forma jurídica ("Deportivo Recoleta" para
    "Recoleta"), ou cujo nome está no do Sofascore com só um prefixo a mais ("Tolima" para
    "Deportes Tolima"). A cidade a mais não casa: "Central Córdoba" (o de Santiago del
    Estero) não é o "Central Córdoba de Rosario" do FM06."""
    if aliases and name in aliases:
        target = aliases[name]
        if isinstance(target, int):
            found = [c for c in clubs if c["uid"] == target]
        else:
            found = [c for c in clubs if hj._key(target) in (hj._key(c["long"]), hj._key(c["short"]))]
        return (found[0], "apelido") if len(found) == 1 else (None, "sem clube")
    key = hj._key(name)
    keys = [(c, _keys(c)) for c in clubs]
    for exact in ([c for c in clubs if key in (hj._key(c["long"]), hj._key(c["short"]))],
                  [c for c, own in keys if key in own]):     # "Huracán" antes do "Huracán (TA)"
        if exact:
            return (exact[0], "nome") if len(exact) == 1 else (None, "sem clube")
    near = [c for c, own in keys if any(key < k and hj._generic(k - key) for k in own)]
    if not near:
        near = [c for c, own in keys
                if any(k < key and k - hj._GENERIC and key - k <= _PREFIXES | hj._GENERIC for k in own)]
    return (near[0], "aproximado") if len(near) == 1 else (None, "sem clube")


def match_club(name: str, clubs: list[dict], aliases: dict[str, str | int] | None = None) -> dict | None:
    return match(name, clubs, aliases)[0]


def identity_rows(path: Path | None = None) -> list[dict]:
    """Linhas da identidade_estrangeiros.csv com clube do FM06 (as sem UID ficam de fora)."""
    path = path or IDENTITIES
    if not path.exists():
        return []
    return [r for r in csv.DictReader(path.open(encoding="utf-8-sig")) if str(r.get("uid_jogo") or "").isdigit()]


def all_identities() -> list[dict]:
    """Brasil + estrangeiros, no formato da identidade_fm06.csv."""
    rows = list(csv.DictReader(BR_IDENTITIES.open(encoding="utf-8-sig")))
    return rows + identity_rows()


def write_all_identities(path: Path) -> Path:
    """Grava Brasil + estrangeiros (clube_2026, uid_jogo, tipo, pais) num CSV só: o do
    live_player_editor.py --squads-all, que conta os jogadores de 2005 de cada clube."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["clube_2026", "uid_jogo", "tipo", "pais"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_identities())
    return path


def club_indexes(server: bytes, rows: list[dict] | None = None) -> dict[int, int]:
    """UID do jogo -> índice do clube (o do contrato das pessoas no people_db), dos clubes
    da identidade_estrangeiros.csv."""
    rows = identity_rows() if rows is None else rows
    brazil = set(people_contracts.brazil_club_indexes(server))
    found: dict[int, int] = {}
    for alpha2 in {r["pais"] for r in rows if r.get("pais") in NATIONS}:
        for club in fm06_clubs(server, alpha2, brazil):
            found.setdefault(club["uid"], club["index"])
    return {int(r["uid_jogo"]): found[int(r["uid_jogo"])] for r in rows if int(r["uid_jogo"]) in found}


def team_values(server: bytes) -> dict[int, int]:
    """UID do jogo -> valor do campo "time" das pessoas do clube, pelo registro do time
    (elenco_times): o dos clubes brasileiros (people_contracts.club_teams) acha o registro
    pelo UID do repositório, que nos estrangeiros às vezes casa antes com outro trecho."""
    by_uid: dict[int, list[int]] = {}
    for team in elenco_times.all_teams(server):
        by_uid.setdefault(team.uid, []).append(team.value)
    return {uid: values[0] for uid, values in by_uid.items() if len(values) == 1}


def player_files() -> list[Path]:
    return [p for p in (BR_PLAYERS, PLAYERS) if p.exists()]


def nation_of(uid: int, rows: list[dict] | None = None) -> int:
    """Código da nação do clube de 2026 (estrangeiro) ou 0xBD (Brasil)."""
    for row in rows if rows is not None else identity_rows():
        if int(row["uid_jogo"]) == uid and row.get("pais") in NATIONS:
            return NATIONS[row["pais"]][0]
    return 0xBD
