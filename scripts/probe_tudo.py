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
    show_continental(handle, found, clubs_by_uid(db) if db else {})
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nGravado em {OUTPUT}")


if __name__ == "__main__":
    main()
