"""Mostra as fases de cada série brasileira na memória do jogo.

Uso (com o jogo aberto e o save carregado; uma linha só):
    python -u scripts\\probe_stages.py fm_brasil.exe

Para cada série (A, B, C nova, D = antiga C) mostra quantas fases a
competição deve ter (+0x100), quantas já foram criadas (+0x98) e, para cada
fase criada, a classe (RTTI) e os primeiros bytes. Serve para ver se a fase
seguinte (playoff, grupos, mata-mata) foi criada e se tem times.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from live_player_memory import find_process_id, iter_regions, open_process, read_memory  # noqa: E402

IMAGE = (0x00400000, 0x015C4000)   # fm.exe na memória (com a seção .fm26)
COMPS = {
    "Série A": 0x0113B2FC,
    "Série B": 0x0113B5B4,
    "Série C (nova)": 0x012BA614,
    "Série D (antiga C)": 0x0113B86C,
}


def u32(data: bytes, at: int) -> int:
    return struct.unpack_from("<I", data, at)[0]


def class_name(handle, vtable: int) -> str:
    try:
        col = u32(read_memory(handle, vtable - 4, 4), 0)
        td = u32(read_memory(handle, col + 12, 4), 0)
        raw = read_memory(handle, td + 8, 80)
        return raw.split(b"\0", 1)[0].decode("latin1")
    except Exception:
        return "?"


def hexdump(data: bytes, base: int = 0) -> str:
    lines = []
    for at in range(0, len(data), 16):
        chunk = data[at:at + 16]
        lines.append(f"      +{base + at:03X}: " + " ".join(f"{b:02x}" for b in chunk))
    return "\n".join(lines)


def find_objects(handle, vtables: dict[str, int]) -> dict[str, list[int]]:
    needles = {name: struct.pack("<I", vt) for name, vt in vtables.items()}
    found = {name: [] for name in vtables}
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


def array_items(handle, data: bytes, at: int) -> list[int]:
    """ARRAY do jogo: vtable em +0, ponteiro dos itens em +4, quantidade (byte) em +8."""
    ptr, count = u32(data, at + 4), data[at + 8]
    if ptr < 0x10000 or count == 0:
        return []
    raw = read_memory(handle, ptr, 4 * count)
    if not raw or len(raw) < 4 * count:
        return []
    return [u32(raw, 4 * i) for i in range(count)]


def stage_list(handle, comp: bytes) -> list[int]:
    return array_items(handle, comp, 0x90)


def show_actions(handle, stage: bytes) -> None:
    """Ações de destino da fase (LEAGUE_FATE_ACTION_*, lista em +0x8C)."""
    for action in array_items(handle, stage, 0x8C):
        data = read_memory(handle, action, 0x20) or b""
        if len(data) < 0x1C:
            continue
        print(f"      ação {class_name(handle, u32(data, 0))}: zona {data[8]}, "
              f"próxima fase {u32(data, 0x14):#x}, {u32(data, 0x18):#x}")


def main() -> None:
    handle = open_process(find_process_id(sys.argv[1] if len(sys.argv) > 1 else "fm_brasil.exe"))
    print("Procurando as séries na memória...", flush=True)
    found = find_objects(handle, COMPS)
    for name, addresses in found.items():
        print(f"\n=== {name}: {len(addresses)} objeto(s)")
        for address in addresses[:2]:
            comp = read_memory(handle, address, 0x200)
            if not comp or len(comp) < 0x200:
                continue
            print(f"  objeto {address:#x}: fases previstas (+0x100) = {comp[0x100]}, "
                  f"fases criadas (+0x98) = {comp[0x98]}")
            print("    bytes +0x90..+0xAF:")
            print(hexdump(comp[0x90:0xB0], 0x90))
            for index, stage in enumerate(stage_list(handle, comp)):
                data = read_memory(handle, stage, 0xA0) or b""
                vt = u32(data, 0) if len(data) >= 4 else 0
                print(f"    fase {index}: {stage:#x} {class_name(handle, vt)}")
                print(hexdump(data[:0xA0]))
                if len(data) >= 0xA0:
                    show_actions(handle, data)


if __name__ == "__main__":
    main()
