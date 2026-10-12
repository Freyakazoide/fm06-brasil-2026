"""Descobre em qual campo do objeto Club o jogo guarda a divisão do clube.

Com o FM06 aberto numa partida (depois do New Game):

    python scripts/probe_club_division.py              (jogo aberto pelo fm.exe)
    python scripts/probe_club_division.py fm_c64.exe   (jogo aberto por uma cópia)

1. Acha os objetos das Séries A, B e C pela vtable de cada classe.
2. Acha todos os objetos Club pela assinatura (0x010EFFCC, 0x010EFFB8).
3. Para cada deslocamento do Club, conta quantos clubes apontam para cada
   série. O campo da divisão é o que dá algo como A=20, B=20, C=128.

Também testa o ID da competição (0x19017...) e o índice na tabela do banco
(73, 85, 86), caso o campo não seja ponteiro.
"""

from __future__ import annotations

import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from live_player_memory import find_process_id, iter_regions, open_process, read_memory  # noqa: E402


CLUB_SIGNATURE = struct.pack("<II", 0x010EFFCC, 0x010EFFB8)
CLUB_SIZE = 440
SERIES = {
    "A": {"vtable": 0x0113B2FC, "id": 0x19017, "index": 73},
    "B": {"vtable": 0x0113B5B4, "id": 0x1A2B7, "index": 85},
    "C": {"vtable": 0x0113B86C, "id": 0x1A2B8, "index": 86},
}


def scan(handle, needles: dict[str, bytes], align: int = 4) -> dict[str, list[int]]:
    found = defaultdict(list)
    for base, size in iter_regions(handle):
        offset = 0
        while offset < size:
            data = read_memory(handle, base + offset, min(4 * 1024 * 1024, size - offset))
            if not data:
                break
            for key, needle in needles.items():
                pos = data.find(needle)
                while pos >= 0:
                    if (base + offset + pos) % align == 0:
                        found[key].append(base + offset + pos)
                    pos = data.find(needle, pos + 1)
            offset += len(data)
    return found


def main() -> None:
    handle = open_process(find_process_id(sys.argv[1] if len(sys.argv) > 1 else "fm.exe"))
    print("Procurando objetos das séries e clubes...", flush=True)
    hits = scan(handle, {
        **{f"serie_{k}": struct.pack("<I", v["vtable"]) for k, v in SERIES.items()},
        "club": CLUB_SIGNATURE,
    })
    series_ptr = {}
    for key, info in SERIES.items():
        objects = hits.get(f"serie_{key}", [])
        print(f"Série {key}: {len(objects)} objeto(s) {[hex(a) for a in objects[:3]]}")
        if objects:
            series_ptr[key] = objects[0]
    clubs = hits.get("club", [])
    print(f"Clubes: {len(clubs)}")

    targets = {}
    for key, address in series_ptr.items():
        for sub in (0, 4, 8, 12, 16):
            targets[address + sub] = f"{key}:ptr+{sub}"
    for key, info in SERIES.items():
        targets[info["id"]] = f"{key}:id"

    per_offset: dict[int, Counter] = defaultdict(Counter)
    for club in clubs:
        data = read_memory(handle, club, CLUB_SIZE)
        if not data or len(data) < CLUB_SIZE:
            continue
        for rel in range(0, CLUB_SIZE - 3, 2):
            value = struct.unpack_from("<I", data, rel)[0]
            if value in targets:
                per_offset[rel][targets[value]] += 1
            small = struct.unpack_from("<H", data, rel)[0]
            for key, info in SERIES.items():
                if small == info["index"]:
                    per_offset[rel][f"{key}:index16"] += 1

    print("\nCampos do Club que apontam para as séries (deslocamento: contagem):")
    ranked = sorted(per_offset.items(), key=lambda item: -sum(item[1].values()))
    for rel, counter in ranked[:25]:
        print(f"  +0x{rel:03X}: {dict(counter)}")


if __name__ == "__main__":
    main()
