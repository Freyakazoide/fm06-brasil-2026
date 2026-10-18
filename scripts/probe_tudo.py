"""Probe único: tudo o que os testes da temporada precisam, numa varredura só.

Uso (com o jogo aberto e o save carregado; uma linha só):
    python -u scripts\\probe_tudo.py fm_brasil.exe

Mostra e grava em workspace\\probe_saida.txt:
- a data do jogo (ano exibido, +20);
- estaduais: ano e fases de cada estado e do contêiner; para estado com fase
  faltando, a classe e os bytes da fase de liga;
- séries A, B, C, D e Copa do Brasil: ano e fases;
- Libertadores, Sul-Americana e Recopa: ano e participantes (+0x190), com país
  e divisão de cada clube.
"""

from __future__ import annotations

import datetime
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from live_player_memory import find_process_id, open_process, read_memory  # noqa: E402
from probe_stages import (COMPS, CONTAINER_VTABLE, STATE_VTABLE, UF, class_name,  # noqa: E402
                          find_objects, hexdump, stage_list, u32)
from probe_continental import COMPS as CONTINENTAL, server_db  # noqa: E402
from fm06patch.server_teams import clubs_by_uid  # noqa: E402

NATION = {0x671: "ARG", 0x672: "BOL", 0x673: "BRA", 0x674: "CHI", 0x675: "COL", 0x676: "ECU",
          0x677: "PAR", 0x678: "PER", 0x679: "URU", 0x67A: "VEN", 0x17B: "MEX", 0x186: "EUA"}
OUTPUT = ROOT / "workspace" / "probe_saida.txt"
GAME_DATE = 0x014EAB38             # SI_DATE atual: u16 dia do ano (base 0), u16 ano
lines: list[str] = []


def out(text: str = "") -> None:
    print(text, flush=True)
    lines.append(text)


def year(comp: bytes) -> int:
    return struct.unpack_from("<H", comp, 0x9C)[0]


def division_name(handle, division: int) -> str:
    vt = u32(read_memory(handle, division, 4) or b"\0\0\0\0", 0) if division else 0
    return class_name(handle, vt).removeprefix(".?AV").removesuffix("@@") if vt else "-"


def team_row(handle, names: dict, team: int) -> tuple[str, str, str, str]:
    """País, clube (UID), divisão atual e temporada passada (divisão e posição)."""
    data = read_memory(handle, team, 0x64) or b""
    if len(data) < 0x64:
        return "?", "?", "?", "?"
    head = read_memory(handle, u32(data, 0x38), 0xE0) or b""
    uid = u32(head, 0x14) if len(head) >= 0x18 else 0
    nation = u32(head, 0xDC) if len(head) >= 0xE0 else 0
    nation_head = (read_memory(handle, nation, 0x18) or b"") if nation else b""
    nation_uid = u32(nation_head, 0x14) if len(nation_head) >= 0x18 else 0
    name = names.get(uid, ("", "?"))[1]           # clubes de fora do Brasil: sem nome no mapa
    last = f"{division_name(handle, u32(data, 0x5C))} {data[0x60]}º"
    return NATION.get(nation_uid, f"{nation_uid:#x}"), f"{name} ({uid})", division_name(handle, u32(data, 0x54)), last


def participants(handle, comp: bytes) -> list[int]:
    ptr, count = u32(comp, 0x194), struct.unpack_from("<H", comp, 0x198)[0]
    if ptr < 0x10000 or not count or count > 64:    # Recopa e outras classes: +0x190 não é a lista
        return []
    raw = read_memory(handle, ptr, 4 * count) or b""
    return [u32(raw, 4 * i) for i in range(len(raw) // 4)]


def show_states(handle, found) -> None:
    out(f"=== Estaduais ({len(found['estadual'])} objetos)")
    for address in found["contêiner"]:
        comp = read_memory(handle, address, 0x200) or b""
        if len(comp) >= 0x200:
            out(f"  contêiner: ano {year(comp)}, fases {comp[0x98]}/{comp[0x100]}")
    rows = []
    for address in found["estadual"]:
        comp = read_memory(handle, address, 0x1C4) or b""
        if len(comp) >= 0x1C4 and u32(comp, 0x1A4) in UF:
            rows.append((UF[u32(comp, 0x1A4)], comp))
    newest = max((year(c) for _, c in rows), default=0)
    for uf, comp in sorted(rows, key=lambda r: (r[0], year(r[1]))):
        problem = year(comp) < newest            # fase faltando é normal durante o estadual
        out(f"  {uf}: ano {year(comp)}, fases {comp[0x98]}/{comp[0x100]}, clubes {comp[0x1A8]}, "
            f"grupos {comp[0x1A9]}, classificados {comp[0x1AB]}{'   <-- PROBLEMA' if problem else ''}")
        if problem:
            for index, stage in enumerate(stage_list(handle, comp)):
                data = read_memory(handle, stage, 0xA0) or b""
                vt = u32(data, 0) if len(data) >= 4 else 0
                out(f"    fase {index}: {class_name(handle, vt)}")
                out(hexdump(data))


def show_national(handle, found) -> None:
    out("\n=== Competições nacionais")
    for name in COMPS:
        for address in found[name][:2]:
            comp = read_memory(handle, address, 0x200) or b""
            if len(comp) >= 0x200:
                out(f"  {name}: ano {year(comp)}, fases {comp[0x98]}/{comp[0x100]}")


def show_continental(handle, found, names: dict) -> None:
    for name in CONTINENTAL:
        for address in found[name]:
            comp = read_memory(handle, address, 0x200) or b""
            if len(comp) < 0x200:
                continue
            teams = participants(handle, comp)
            out(f"\n=== {name}: ano {year(comp)}, fases {comp[0x98]}/{comp[0x100]}, "
                f"{len(teams)} participante(s)")
            rows = sorted(team_row(handle, names, t) for t in teams)
            counts: dict[str, int] = {}
            for nation, club, division, last in rows:
                counts[nation] = counts.get(nation, 0) + 1
                out(f"  {nation}  {club:28} {division:16} passada: {last}")
            if counts:
                out("  por país: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))


TEAM_VTABLE = 0x010EDF6C


def is_team(handle, ptr: int) -> bool:
    raw = read_memory(handle, ptr, 4) if ptr > 0x10000 else None
    return bool(raw) and u32(raw, 0) == TEAM_VTABLE


def position_entries(handle, table: int) -> list[tuple[int, int]]:
    """Tabela de posições finais (competição+0xA4): lista em +0x2C (ponteiro +0x30,
    quantidade word +0x34); cada item tem o TEAM em +0 e o tipo em +8 (0 campeão, 1 vice,
    2 terceiro). O tamanho do item não é conhecido: tenta ponteiros e depois structs."""
    head = read_memory(handle, table, 0x40) or b""
    if len(head) < 0x38:
        return []
    ptr, count = u32(head, 0x30), struct.unpack_from("<H", head, 0x34)[0]
    if ptr < 0x10000 or not 0 < count <= 200:
        return []
    raw = read_memory(handle, ptr, 4 * count) or b""
    items = [u32(raw, 4 * i) for i in range(len(raw) // 4)]
    if items and all(is_team(handle, u32(read_memory(handle, it, 4) or b"\0\0\0\0", 0)) for it in items[:3]):
        out = []
        for it in items:
            item = read_memory(handle, it, 12) or b""
            if len(item) == 12:
                out.append((u32(item, 0), item[8]))
        return out
    for stride in (12, 16, 20, 24, 28, 32, 8):
        raw = read_memory(handle, ptr, stride * count) or b""
        if len(raw) == stride * count and all(is_team(handle, u32(raw, stride * i)) for i in range(min(count, 3))):
            return [(u32(raw, stride * i), raw[stride * i + 8]) for i in range(count)]
    return []


def show_cup(handle, found, names: dict) -> None:
    """Copa do Brasil: o que decide se o campeão vai para o histórico."""
    for address in found.get("Copa do Brasil", []):
        comp = read_memory(handle, address, 0x200) or b""
        if len(comp) < 0x200:
            continue
        out("\n=== Copa do Brasil (detalhe)")
        out(f"  ano {year(comp)}, fases {comp[0x98]}/{comp[0x100]}, +0xA8={comp[0xA8]} +0xAC={comp[0xAC]} "
            f"+0xFC={comp[0xFC]} +0x101={comp[0x101]}")
        record = u32(comp, 0x1C)
        rec = (read_memory(handle, record, 0x30) or b"") if record > 0x10000 else b""
        if len(rec) >= 0x2C:
            winner = team_row(handle, names, u32(rec, 0x24))[1] if is_team(handle, u32(rec, 0x24)) else "?"
            out(f"  campeão em título: {winner} (ano {struct.unpack_from('<h', rec, 0x20)[0]})")
        for index, stage in enumerate(stage_list(handle, comp)):
            data = read_memory(handle, stage, 0x30) or b""
            if len(data) >= 0x28:
                out(f"  fase {index}: {class_name(handle, u32(data, 0))}, +9={data[9]}, "
                    f"clubes {struct.unpack_from('<H', data, 0x24)[0]}")
        table = u32(comp, 0xA4)
        entries = position_entries(handle, table) if table > 0x10000 else []
        out(f"  tabela de posições (+0xA4): {len(entries)} itens com clube")
        for team, kind in entries:
            if kind <= 3:
                out(f"    tipo {kind}: {team_row(handle, names, team)[1]}")


def show_date(handle) -> None:
    raw = read_memory(handle, GAME_DATE, 4) or b""
    if len(raw) == 4:
        day, engine_year = struct.unpack("<HH", raw)
        date = datetime.date(engine_year, 1, 1) + datetime.timedelta(days=day)
        out(f"=== Data do jogo: {date.day:02d}/{date.month:02d}/{engine_year + 20} (motor {engine_year})\n")


def main() -> None:
    handle = open_process(find_process_id(sys.argv[1] if len(sys.argv) > 1 else "fm_brasil.exe"))
    print("Procurando tudo na memória (1 a 2 minutos)...", flush=True)
    vtables = dict(COMPS)
    vtables.update(CONTINENTAL)
    vtables.update({"estadual": STATE_VTABLE, "contêiner": CONTAINER_VTABLE})
    found = find_objects(handle, vtables)
    db = server_db()
    show_date(handle)
    show_states(handle, found)
    show_national(handle, found)
    names = clubs_by_uid(db) if db else {}
    show_continental(handle, found, names)
    show_cup(handle, found, names)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nGravado em {OUTPUT}")


if __name__ == "__main__":
    main()
