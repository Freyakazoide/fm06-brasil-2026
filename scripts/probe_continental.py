"""Mostra quais clubes estão marcados para a Libertadores e a Sul-Americana.

Uso (com o jogo aberto e o save carregado; uma linha só):
    python -u scripts\\probe_continental.py fm_brasil.exe

A Libertadores (0x00C06440) escolhe, para cada país, os clubes cujo
TEAM+0xB4 aponta para ela. Este probe lista esses clubes, com a divisão em
que jogam (TEAM+0x54) e o byte TEAM+0xB8 (gravado junto, por 0x00A1CE70).
Serve para descobrir a regra de vagas do Brasil no FM06.
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from live_player_memory import find_process_id, iter_regions, open_process, read_memory  # noqa: E402
from fm06patch.server_teams import club_names  # noqa: E402

IMAGE = (0x00400000, 0x015C4000)
COMPS = {"Libertadores": 0x01154CF4, "Sul-Americana": 0x01154A3C, "Recopa": 0x01154784}
TEAM_SIGNATURE = struct.pack("<II", 0x010EDF6C, 0x010EDF5C)


def u32(data: bytes, at: int) -> int:
    return struct.unpack_from("<I", data, at)[0]


def class_name(handle, vtable: int) -> str:
    try:
        col = u32(read_memory(handle, vtable - 4, 4), 0)
        td = u32(read_memory(handle, col + 12, 4), 0)
        return read_memory(handle, td + 8, 80).split(b"\0", 1)[0].decode("latin1")
    except Exception:
        return "?"


def scan(handle, needles: dict[str, bytes]) -> dict[str, list[int]]:
    found = {name: [] for name in needles}
    for base, size in iter_regions(handle):
        if IMAGE[0] <= base < IMAGE[1]:
            continue
        offset = 0
        while offset < size:
            data = read_memory(handle, base + offset, min(4 * 1024 * 1024, size - offset))
            if not data:
                break
            for name, needle in needles.items():
                pos = data.find(needle)
                while pos >= 0:
                    if pos % 4 == 0:
                        found[name].append(base + offset + pos)
                    pos = data.find(needle, pos + 1)
            offset += len(data)
    return found


def server_db() -> bytes:
    try:
        game = Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"])
        return (game / "data" / "db" / "server_db.dat").read_bytes()
    except Exception:
        return b""


def main() -> None:
    handle = open_process(find_process_id(sys.argv[1] if len(sys.argv) > 1 else "fm_brasil.exe"))
    print("Procurando competições e times na memória...", flush=True)
    needles = {name: struct.pack("<I", vt) for name, vt in COMPS.items()}
    needles["TEAM"] = TEAM_SIGNATURE
    found = scan(handle, needles)
    comps = {}
    for name in COMPS:
        for address in found[name]:
            comps[address] = name
    print("Competições:", {name: [hex(a) for a in found[name]] for name in COMPS})
    db = server_db()
    rows = []
    for team in found["TEAM"]:
        data = read_memory(handle, team, 0xC0) or b""
        if len(data) < 0xC0:
            continue
        target = u32(data, 0xB4)
        if target not in comps:
            continue
        club = u32(data, 0x38)
        head = read_memory(handle, club, 0x20) or b""
        uid = u32(head, 0x14) if len(head) >= 0x18 else 0
        name = club_names(db, uid)[1] if db and uid else ""
        division = u32(data, 0x54)
        div_vt = u32(read_memory(handle, division, 4) or b"\0\0\0\0", 0) if division else 0
        rows.append((comps[target], name or f"clube {uid}", class_name(handle, div_vt) if div_vt else "-",
                     data[0x60], data[0xB8]))
    for comp in COMPS:
        mine = [r for r in rows if r[0] == comp]
        print(f"\n=== {comp}: {len(mine)} clube(s) marcados")
        for _, name, division, last_pos, flag in sorted(mine, key=lambda r: (r[2], r[3])):
            print(f"  {name:28} divisão {division:28} pos. anterior {last_pos:3}  +0xB8 = {flag}")


if __name__ == "__main__":
    main()
