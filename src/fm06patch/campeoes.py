"""Histórico real de campeões (COMP_HISTORY) das competições brasileiras e da CONMEBOL.

O jogo mostra os anos com +20 (o motor está em 2005 e a tela em 2025), então o
campeão real do ano A fica gravado no ano A − 20. Para cada competição:

- os registros que o banco já tem (até 2005) mantêm o campeão e o vice e só
  mudam de ano; time de 2005 reaproveitado como substituto de outro clube em
  2026 sai (FFFFFFFF), porque no jogo ele tem o nome do clube novo;
- a antiga Série C (hoje a Série D) passa o histórico para a nova Série C, e a
  Taça de Prata (Robertão 1967–70, título brasileiro pela CBF) vai para a Série A;
- os anos que faltam (2006–2025, Série D inteira, Taça Brasil) usam
  data/brasil/historico/campeoes.csv (scripts/coletar_historico.py): primeiro os
  registros órfãos do banco (competição FFFFFFFF, de competições que não existem
  mais), depois registros novos no fim da lista (u32 quantidade + registros de 39
  bytes; o leitor do jogo, 0x00A0AE50, lê em sequência e só exige índice = posição
  e UID único).

A Sul-Americana de 2025 fica de fora: o motor joga a de 2005 antes do primeiro
dia do jogador (ver historico.CHAMPIONS_2025).
"""

from __future__ import annotations

import csv
import re
import struct
from dataclasses import dataclass, field
from pathlib import Path

from . import historico
from .estaduais import ID as STATE_ID
from .estaduais_clubes import (LOWER_ID, STATE_FIELD, _words, normalize, state_teams, uf_of)
from .server_teams import _DATES, _string, find_brazil_teams

CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "brasil" / "historico" / "campeoes.csv"
NONE = historico.NONE
RECORD = historico.RECORD
SHIFT = 20
LAST_REAL = 2025
NEW_UID = 100_000_000          # acima de todos os UIDs do banco (máx. ~34 milhões)
COMP_IDS = {
    "A": 0x19017, "B": 0x1A2B7, "C": 319191, "D": 0x1A2B8,
    "CDB": 0x1901B, "LIB": 0x1900F, "SULA": 0x4D87F, **STATE_ID,
}
SKIP_REAL = {"SULA": {2025}}
# nação do clube no registro do server_db (código do people_db)
FOREIGN = {"ARG": 0xBB, "BOL": 0xBC, "CHI": 0xBE, "COL": 0xBF, "ECU": 0xC0, "PAR": 0xC1,
           "PER": 0xC2, "URU": 0xC3, "VEN": 0xC4, "MEX": 0x6D}
# nome na Wikipédia -> nome de 2026 (identidade) ou do FM06
ALIASES = {
    "atletico mineiro": "atletico mg", "atletico paranaense": "athletico pr", "athletico paranaense": "athletico pr",
    "atletico goianiense": "atletico go", "america mineiro": "america mg", "america de natal": "america rn",
    "sport recife": "sport", "bragantino": "red bull bragantino",
    "inter de limeira": "inter de limeira", "etti jundiai": "paulista",
    "operario ferroviario": "operario pr", "rio branco vn": "rio branco de venda nova",
}
# por nação: nome na Wikipédia -> nome no FM06
FOREIGN_ALIASES = {
    "estudiantes": "estudiantes de la plata", "racing": "racing club", "arsenal": "arsenal de sarandi",
    "ldu quito": "liga deportiva universitaria", "santa fe": "independiente santa fe", "junior": "atletico junior",
    "unam": "pumas", "uanl": "tigres", "guadalajara": "chivas guadalajara", "barcelona": "barcelona sc",
    "nacional": "nacional", "olimpia": "olimpia", "colon": "colon de santa fe", "tigre": "tigre",
}


@dataclass
class Team:
    index: int
    names: list[str]
    uf: str = ""
    nation: str = "BRA"
    substitute: bool = False
    ours: bool = False          # clube de 2026 (identidade)


@dataclass
class Report:
    lines: list[str] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)
    reused: int = 0
    appended: int = 0


def _uf_of_state(data: bytes) -> dict[int, str]:
    out = {}
    for uf, comp_id in list(STATE_ID.items()) + list(LOWER_ID.items()):
        try:
            out[historico.comp_index(data, comp_id)] = uf
        except Exception:
            pass
    return out


def brazil_teams(data: bytes, identities) -> list[Team]:
    """Times brasileiros com nomes de 2026 (identidade) ou do FM06 e o estado."""
    by_repo = {i.repo_uid: i for i in identities}
    state_uf = _uf_of_state(data)
    ufs = {}
    in_states = state_teams(data)
    for team in in_states:
        ufs[team.club_uid] = state_uf.get(struct.unpack_from("<I", data, team.offset + STATE_FIELD)[0], "")
    teams = []
    for record in find_brazil_teams(data) + in_states:
        index = struct.unpack_from("<I", data, record.offset - 8)[0] + 1
        ident = by_repo.get(record.club_uid)
        if ident and ident.tipo == "substituto":
            teams.append(Team(index, [ident.clube], ident.uf, substitute=True, ours=True))
        elif ident:
            teams.append(Team(index, [ident.clube, record.short_name, record.name], ident.uf, ours=True))
        else:
            teams.append(Team(index, [record.short_name, record.name], ufs.get(record.club_uid, "")))
    unique = {}
    for team in teams:
        unique.setdefault(team.index, team)
    return list(unique.values())


def foreign_teams(data: bytes) -> list[Team]:
    """Clubes da América do Sul e do México (registro do clube com a nação)."""
    codes = {code: nation for nation, code in FOREIGN.items()}
    pattern = re.compile(rb"(....)(....)\x00([" + re.escape(bytes(codes)) + rb"])\x00\x00\x00\x00", re.S)
    teams = []
    for match in pattern.finditer(data, 0, 0x400000):
        uid = struct.unpack("<I", match.group(2))[0]
        mark = data.find(_DATES, match.end(), match.end() + 0x600)
        if mark < 0:
            continue
        long_name, after = _string(data, mark + len(_DATES))
        short_name, _ = _string(data, after)
        needle = struct.pack("<I", uid) + b"\x0a\x00"
        at = data.find(needle, 0xE00000, 0x1300000)
        if not long_name or at < 0 or data.find(needle, at + 1, 0x1300000) >= 0:
            continue
        teams.append(Team(struct.unpack_from("<I", data, at - 4)[0] + 1, [short_name, long_name],
                          nation=codes[match.group(3)[0]]))
    return teams


def _key(text: str) -> str:
    text = normalize(text or "")
    text = re.sub(r"\b(fc|ec|sc|cr|se|ca|aa|ad|cd|ac|club|clube|futebol|esporte|sport club|de futebol)\b", " ", text)
    return " ".join(text.split())


def _base(text: str, uf: str) -> str:
    return re.sub(rf"\s+{uf.lower()}$", "", _key(text)) if uf else _key(text)


class Matcher:
    """Nome da Wikipédia -> índice do time. Por etapas (nome igual, nome do artigo, mesmas
    palavras), filtrando pelo estado; empate entre dois times dá NONE em vez de chute."""

    def __init__(self, brazil: list[Team], foreign: list[Team]):
        self.brazil = brazil
        self.foreign = foreign

    @staticmethod
    def _filter(hits: list[Team], uf: str) -> list[Team]:
        if uf:
            hits = [t for t in hits if t.uf == uf] or [t for t in hits if not t.uf]
        if len(hits) > 1:
            ours = [t for t in hits if t.ours]
            hits = ours if len(ours) == 1 else hits
        return hits

    def _pick(self, exact: list[str], label: list[str], article: str, pool: list[Team], uf: str) -> Team | None:
        def full(t: Team) -> set[str]:
            return {_key(n) for n in t.names} | {_key(re.sub(r"\s*\([^)]*\)", "", n)) for n in t.names}

        def base(t: Team) -> set[str]:
            return {_base(n, t.uf) for n in t.names}

        def primary(t: Team) -> set[str]:
            return {normalize(t.names[0])}

        label = [w for w in dict.fromkeys(label) if w]
        steps = [(exact, primary), (label, full), (label, base), ([article], full), ([article], base)]
        for wanted, names in steps:
            wanted = [w for w in wanted if w]
            hits = self._filter([t for t in pool if names(t) & set(wanted)], uf) if wanted else []
            if len(hits) == 1:
                return hits[0]
        words = [set(w.split()) - {uf.lower()} for w in label]
        hits = [t for t in pool if any(w and any(_words(n, t.uf or uf) == w for n in t.names) for w in words)]
        hits = self._filter(hits, uf)
        return hits[0] if len(hits) == 1 else None

    def find(self, name: str, article: str, where: str) -> int:
        if not name:
            return NONE
        key = _key(name)
        article_key = _key(re.sub(r"\s*\(.*?\)", "", article or ""))
        if where in FOREIGN:
            pool = [t for t in self.foreign if t.nation == where]
            team = self._pick([normalize(name)], [FOREIGN_ALIASES.get(key, key), key], article_key, pool, "")
        else:
            uf = uf_of(where) if where and where != "BRA" else ""
            team = self._pick([normalize(name)], [ALIASES.get(key, key), key], article_key, self.brazil, uf)
        return team.index if team else NONE


def load_rows(path: Path = CSV_PATH) -> dict[str, dict[int, dict]]:
    out: dict[str, dict[int, dict]] = {}
    for row in csv.DictReader(path.open(encoding="utf-8-sig")):
        comp, year = row["competicao"], int(row["ano"])
        if year <= LAST_REAL and year not in SKIP_REAL.get(comp, ()):
            out.setdefault(comp, {})[year] = row
    return out


def rewrite(data: bytes, identities, rows: dict[str, dict[int, dict]] | None = None,
            into: bytes | None = None) -> tuple[bytes, Report]:
    """Lê times e registros de `data` (banco original) e grava em `into` (o banco já
    alterado pelos outros passos; a lista de campeões tem de estar igual à do original).
    Chamar por último: os registros novos deslocam o resto do arquivo."""
    rows = load_rows() if rows is None else rows
    report = Report()
    start = historico.find_list(data)
    count = struct.unpack_from("<I", data, start)[0]
    end = start + 4 + RECORD * count
    if into is not None and into[start:end] != data[start:end]:
        raise ValueError("a lista de campeões do banco alterado não é a do original")
    out = bytearray(data if into is None else into)
    comp = {key: historico.comp_index(data, cid) for key, cid in COMP_IDS.items()}
    remap = {comp["D"]: comp["C"], comp["C"]: comp["A"]}
    ours = set(comp.values())
    brazil = brazil_teams(data, identities)
    substitute = {t.index for t in brazil if t.substitute}
    matcher = Matcher(brazil, foreign_teams(data))
    by_comp: dict[int, list[int]] = {}
    orphans = []
    for k in range(count):
        at = start + 4 + RECORD * k
        c = struct.unpack_from("<I", data, at + 1)[0]
        if c == NONE:
            orphans.append(at)
        elif c in ours:
            by_comp.setdefault(remap.get(c, c), []).append(at)

    def team_of(row: dict, side: str) -> int:
        index = matcher.find(row[side], row[f"{side}_artigo"], row[f"{side}_local"])
        if index == NONE and row[side]:
            report.unmatched.append(f"{row['competicao']} {row['ano']}: {row[side]} ({row[f'{side}_local']})")
        return index

    new_records: list[bytes] = []

    def write(at: int | None, comp_index: int, real: int, winner: int, runner: int, keep: bool) -> None:
        if at is None:
            record = bytearray(RECORD)
            struct.pack_into("<BIHIII", record, 0, 0, comp_index, real - SHIFT, winner, runner, NONE)
            record[19:31] = b"\xff" * 12
            new_records.append(bytes(record))
            return
        struct.pack_into("<IH", out, at + 1, comp_index, real - SHIFT)
        struct.pack_into("<II", out, at + 7, winner, runner)
        if not keep:
            struct.pack_into("<I", out, at + 15, NONE)
            out[at + 19:at + 31] = b"\xff" * 12

    spare_orphans = iter(orphans)
    for key, index in comp.items():
        wanted = rows.get(key, {})
        records = by_comp.get(index, [])
        kept, spare = {}, []
        for at in records:
            year = struct.unpack_from("<H", data, at + 5)[0]
            if year in wanted and year not in kept:
                kept[year] = at
            else:
                spare.append(at)
        fixed = 0
        for year, at in kept.items():
            winner, runner = struct.unpack_from("<II", data, at + 7)
            row = wanted[year]
            if winner in substitute:
                winner = team_of(row, "campeao")
                fixed += 1
            if runner in substitute:
                runner = team_of(row, "vice") if row["vice"] else NONE
                fixed += 1
            write(at, index, year, winner, runner, keep=True)
        missing = [y for y in sorted(wanted) if y not in kept]
        for year in missing:
            row = wanted[year]
            at = spare.pop(0) if spare else next(spare_orphans, None)
            if at is not None and at not in records:
                report.reused += 1
            write(at, index, year, team_of(row, "campeao"), team_of(row, "vice") if row["vice"] else NONE, keep=False)
        for at in spare:                        # registro sem ano oficial: fica de fora (vira órfão)
            struct.pack_into("<I", out, at + 1, NONE)
        report.lines.append(f"{key:5} {len(kept):3} anos do banco (ano −20, {fixed} times trocados), "
                            f"{len(missing):3} da Wikipédia")
    if new_records:
        tail = start + 4 + RECORD * count
        blob = bytearray()
        for k, record in enumerate(new_records):
            record = bytearray(record)
            struct.pack_into("<II", record, 31, count + k, NEW_UID + k)
            blob += record
        struct.pack_into("<I", out, start, count + len(new_records))
        out[tail:tail] = blob
        report.appended = len(new_records)
    return bytes(out), report
