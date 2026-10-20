"""Estádio, capacidade e cidade de 2026 dos clubes (server_db + .lnc).

- Registro do time ("0A 00"): +19 u32 índice do estádio (São Caetano 2623 = Anacleto
  Campanella, Flamengo 1205 = Maracanã, São Paulo 1130 = Morumbi).
- Registro do estádio: u32 índice da cidade, FF FF FF FF, u32 índice, u32 UID, 00,
  u32 capacidade, u32 capacidade 2 (Morumbi: São Paulo, 1130, 102549, 40000, 40000).
- Registro da cidade: u32 índice, u32 UID, 00 00, 2 floats, u8, u8 nação (0xBD).
- Nomes de estádio e cidade ficam no lang_db: u32 UID, u32 tamanho, texto
  ("São Caetano do Sul (SP)"); trocados com STADIUM_NAME_CHANGE / CITY_NAME_CHANGE.

Cada estádio de 2026 fica com um estádio do FM06: o do próprio clube quando o nome
bate ou quando ninguém mais precisa dele; se não, um estádio de clube que não usamos,
renomeado. A cidade: a do FM06 com o mesmo nome, se existir; se não, uma cidade sem
uso renomeada.
"""

from __future__ import annotations

import re
import struct
import unicodedata
from dataclasses import dataclass, field

TEAM_STADIUM = 19
NOISE = {"estadio", "do", "da", "de", "dos", "das", "e", "municipal", "olimpico"}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def key(name: str) -> str:
    """Chave do estádio sem "Estádio", "do", "Municipal"...: Rei Pelé = Estádio Rei Pelé."""
    return " ".join(sorted(set(normalize(name).split()) - NOISE)) or normalize(name)


def same_name(a: str, b: str) -> bool:
    wa, wb = set(normalize(a).split()) - NOISE, set(normalize(b).split()) - NOISE
    return bool(wa and wb) and (wa <= wb or wb <= wa)


def lang_name(lang: bytes, uid: int) -> str | None:
    """Texto do lang_db com este UID (u32 UID, u32 tamanho, UTF-16)."""
    needle = struct.pack("<I", uid)
    at = lang.find(needle)
    while at >= 0:
        size = struct.unpack_from("<I", lang, at + 4)[0]
        if 1 <= size <= 80:
            raw = lang[at + 8:at + 8 + 2 * size]
            try:
                text = raw.decode("utf-16-le")
                if text.isprintable() and lang[at + 8 + 2 * size:at + 10 + 2 * size] == b"\0\0":
                    return text
            except UnicodeDecodeError:
                pass
        at = lang.find(needle, at + 1)
    return None


def lang_uids(lang: bytes, text: str) -> list[int]:
    """UIDs do lang_db com exatamente este texto."""
    needle = struct.pack("<I", len(text)) + text.encode("utf-16-le") + b"\0\0"
    return [struct.unpack_from("<I", lang, m.start() - 4)[0] for m in re.finditer(re.escape(needle), lang)]


@dataclass
class Stadium:
    index: int
    uid: int
    at: int            # posição do par (índice, UID)
    city: int          # índice da cidade
    capacity: int


STADIUM_TABLE = (0x00E80000, 0x01000000)     # tabela de estádios do server_db 6.0.2 (sha 9FB7A4A2...)


def stadium(server: bytes, index: int) -> Stadium | None:
    """Registro do estádio: (índice da cidade, FF FF FF FF, índice, UID, 00, capacidade) na
    tabela de estádios (Maracanã em 0xEF4AEB). O mesmo número aparece em registros de cidade
    (perto do início) e em outras tabelas (0x13xxxxx): só vale um achado único na tabela."""
    needle = struct.pack("<I", index)
    found = []
    at = server.find(needle, STADIUM_TABLE[0], STADIUM_TABLE[1])
    while at >= 0:
        if server[at - 4:at] == b"\xff\xff\xff\xff" and server[at + 8] == 0:
            found.append(at)
        at = server.find(needle, at + 1, STADIUM_TABLE[1])
    if len(found) != 1:
        return None
    at = found[0]
    uid, = struct.unpack_from("<I", server, at + 4)
    return Stadium(index, uid, at, struct.unpack_from("<I", server, at - 8)[0],
                   struct.unpack_from("<I", server, at + 9)[0])


def city_index(server: bytes, uid: int, nation: int = 0xBD) -> int | None:
    """Índice da cidade com este UID (registro: índice, UID, 00 00, floats, u8, nação)."""
    needle = struct.pack("<I", uid)
    at = server.find(needle)
    while at >= 0:
        if server[at + 4:at + 6] == b"\0\0" and server[at + 15] == nation:
            return struct.unpack_from("<I", server, at - 4)[0]
        at = server.find(needle, at + 1)
    return None


def city_uid(server: bytes, index: int, nation: int = 0xBD) -> int | None:
    needle = struct.pack("<I", index)
    at = server.find(needle)
    while at >= 0:
        if server[at + 8:at + 10] == b"\0\0" and server[at + 19] == nation:
            return struct.unpack_from("<I", server, at + 4)[0]
        at = server.find(needle, at + 1)
    return None


@dataclass
class Wanted:
    club: str
    uf: str
    team_offset: int
    stadium: str
    capacity: int | None
    city: str | None


@dataclass
class Plan:
    team_stadium: dict[int, int] = field(default_factory=dict)      # offset do time -> índice do estádio
    capacity: dict[int, int] = field(default_factory=dict)          # posição do par do estádio -> capacidade
    stadium_city: dict[int, int] = field(default_factory=dict)      # posição do par do estádio -> índice da cidade
    stadium_names: dict[int, str] = field(default_factory=dict)     # UID do estádio -> nome
    city_names: dict[int, str] = field(default_factory=dict)        # UID da cidade -> nome
    report: list[str] = field(default_factory=list)


def plan(server: bytes, lang: bytes, wanted: list[Wanted], other_teams: list[int],
         keep_teams: list[int] = ()) -> Plan:
    """wanted: clubes com estádio de 2026; other_teams: offsets dos times brasileiros que
    não usamos (estádios e cidades livres); keep_teams: clubes de 2026 sem dado de estádio
    (o estádio deles não é renomeado nem cedido).

    O mesmo estádio de 2026 (Maracanã: Flamengo e Fluminense) fica com um estádio só do
    FM06: um dos que o grupo já usa, se ninguém de fora do grupo o mantiver; se não, um de
    clube que não usamos. O estádio escolhido é sempre renomeado para o nome de 2026."""
    out = Plan()
    current = {w.team_offset: struct.unpack_from("<I", server, w.team_offset + TEAM_STADIUM)[0] for w in wanted}
    locked = {struct.unpack_from("<I", server, o + TEAM_STADIUM)[0] for o in keep_teams}
    groups: dict[str, list[Wanted]] = {}
    for w in wanted:
        groups.setdefault(key(w.stadium), []).append(w)
    users: dict[int, set[str]] = {}
    for w in wanted:
        users.setdefault(current[w.team_offset], set()).add(key(w.stadium))

    by_key: dict[str, int] = {}
    claimed: set[int] = set()
    # grupos com mais clubes primeiro (Maracanã), depois um estádio que só o grupo usa
    for name, group in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        options = [current[w.team_offset] for w in group]
        options = sorted(set(options), key=lambda i: (-(users[i] == {name}), -options.count(i)))
        for index in options:
            if index not in claimed and index not in locked and stadium(server, index):
                by_key[name] = index
                claimed.add(index)
                break
    used = set(current.values()) | locked
    spare = []
    for offset in other_teams:
        index = struct.unpack_from("<I", server, offset + TEAM_STADIUM)[0]
        if index not in used and index not in spare and stadium(server, index):
            spare.append(index)
    spare_iter = iter(spare)
    for name in groups:
        if name not in by_key:
            index = next(spare_iter, None)
            if index is not None:
                by_key[name] = index

    infos = {i: stadium(server, i) for i in by_key.values()}
    used_cities = {info.city for info in infos.values()}
    spare_cities = [c for c in dict.fromkeys(stadium(server, i).city for i in spare) if c not in used_cities]
    for name, group in groups.items():
        index = by_key.get(name)
        first = group[0]
        if index is None:
            out.report.append(f"{first.club}: sem estádio livre para {first.stadium}")
            continue
        info = infos[index]
        moved = [w.club for w in group if current[w.team_offset] != index]
        for w in group:
            if current[w.team_offset] != index:
                out.team_stadium[w.team_offset] = index
        out.stadium_names[info.uid] = first.stadium
        if first.capacity:
            out.capacity[info.at] = first.capacity
        city_note = ""
        if first.city:
            target = f"{first.city} ({first.uf})" if first.uf else first.city
            existing = [c for c in (city_index(server, u) for u in lang_uids(lang, target)) if c is not None]
            if existing:
                if existing[0] != info.city:
                    out.stadium_city[info.at] = existing[0]
                city_note = f", cidade {target}"
            elif spare_cities:
                new_city = spare_cities.pop(0)
                new_uid = city_uid(server, new_city)
                if new_uid:
                    out.stadium_city[info.at] = new_city
                    out.city_names[new_uid] = target
                    city_note = f", cidade {target} (nova)"
        out.report.append(f"{', '.join(w.club for w in group)}: {first.stadium}"
                          + (f" ({first.capacity})" if first.capacity else "") + city_note
                          + (f"; estádio trocado: {', '.join(moved)}" if moved else ""))
    return out


def apply(server: bytes, result: Plan) -> bytes:
    out = bytearray(server)
    for offset, index in result.team_stadium.items():
        struct.pack_into("<I", out, offset + TEAM_STADIUM, index)
    for at, capacity in result.capacity.items():
        struct.pack_into("<II", out, at + 9, capacity, capacity)
    for at, city in result.stadium_city.items():
        struct.pack_into("<I", out, at - 8, city)
    return bytes(out)


def lnc_lines(result: Plan) -> list[str]:
    lines = []
    for uid, name in result.stadium_names.items():
        lines.append(f'"STADIUM_NAME_CHANGE"\t{uid}\t"{name}"\t""')
    for uid, name in result.city_names.items():
        lines.append(f'"CITY_NAME_CHANGE"\t{uid}\t"{name}"\t""')
    return lines


def wanted_from_sheets(identities, teams_by_repo: dict[int, int], sofascore_csv, sheet_xlsx) -> tuple[list[Wanted], dict]:
    """Estádio de 2026 de cada clube: a planilha estadios_2026 (estadio_2026, capacidade,
    cidade_2026, reputacao) e, onde ela estiver vazia, o Sofascore (estadios_sofascore.csv).
    Devolve (wanted, {uid_jogo: reputação})."""
    import csv

    sofa = {}
    if sofascore_csv.exists():
        sofa = {r["clube"]: r for r in csv.DictReader(sofascore_csv.open(encoding="utf-8-sig"))}
    sheet: dict[str, dict] = {}       # pelo nome de 2026: o uid_jogo da planilha pode ser de uma versão antiga
    if sheet_xlsx and sheet_xlsx.exists():
        import openpyxl

        rows = openpyxl.load_workbook(sheet_xlsx, read_only=True).worksheets[0].iter_rows(values_only=True)
        header = next(rows)
        for row in rows:
            row = dict(zip(header, row))
            if row.get("clube"):
                sheet[str(row["clube"]).strip()] = row
    wanted, reputations = [], {}
    for ident in identities:
        mine, theirs = sheet.get(ident.clube, {}), sofa.get(ident.clube, {})
        name = (mine.get("estadio_2026") or theirs.get("estadio") or "").strip()
        capacity = mine.get("capacidade") or theirs.get("capacidade")
        city = (mine.get("cidade_2026") or theirs.get("cidade") or "").strip()
        if mine.get("reputacao"):
            reputations[ident.uid] = int(mine["reputacao"])
        if name and ident.repo_uid in teams_by_repo:
            wanted.append(Wanted(ident.clube, ident.uf, teams_by_repo[ident.repo_uid], name.replace('"', ""),
                                 int(float(capacity)) if capacity else None, city or None))
    return wanted, reputations
