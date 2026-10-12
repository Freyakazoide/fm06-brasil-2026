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
    print("Procurando objetos das séries, IDs das competições e clubes...", flush=True)
    hits = scan(handle, {
        **{f"serie_{k}": struct.pack("<I", v["vtable"]) for k, v in SERIES.items()},
        **{f"id_{k}": struct.pack("<I", v["id"]) for k, v in SERIES.items()},
        "club": CLUB_SIGNATURE,
    })
    for key in SERIES:
        print(f"Série {key}: objeto de regras {[hex(a) for a in hits.get(f'serie_{key}', [])[:3]]}, "
              f"ID aparece em {len(hits.get(f'id_{key}', []))} lugar(es)")
    clubs = hits.get("club", [])
    print(f"Clubes: {len(clubs)}")

    # Alvos: o objeto de regras (e subobjetos) e qualquer objeto que contenha
    # o ID da série até 0x80 bytes depois do seu início.
    targets: dict[int, list[str]] = defaultdict(list)
    for key in SERIES:
        for address in hits.get(f"serie_{key}", []):
            for sub in range(0, 0x20, 4):
                targets[address + sub].append(f"{key}:regras+{sub:#x}")
        for address in hits.get(f"id_{key}", []):
            for back in range(0, 0x80, 4):
                targets[address - back].append(f"{key}:id@{address:#x}-{back:#x}")

    per_offset: dict[int, Counter] = defaultdict(Counter)
    for club in clubs:
        data = read_memory(handle, club, CLUB_SIZE)
        if not data or len(data) < CLUB_SIZE:
            continue
        for rel in range(0, CLUB_SIZE - 3, 4):
            value = struct.unpack_from("<I", data, rel)[0]
            for label in targets.get(value, ()):
                per_offset[rel][label] += 1

    print("\nCampos do Club que apontam para algo ligado às séries (deslocamento: alvo = clubes):")
    rows = [(rel, label, n) for rel, counter in per_offset.items() for label, n in counter.items()]
    rows.sort(key=lambda r: -r[2])
    for rel, label, n in rows[:40]:
        print(f"  +0x{rel:03X}  {label:28} {n}")

    # Caminho usado pelo SWAP_TEAMS: clube +0x38 -> objeto X (se +0x40 == 0);
    # a divisão fica em X+0xDC (acessor 0x00A18CE0). Também mostra X+0xEA.
    ids_by_raw = {struct.pack("<I", info["id"]): key for key, info in SERIES.items()}
    rules = {addr: k for k in SERIES for addr in hits.get(f"serie_{k}", [])}
    division = Counter()
    flag_ea = Counter()
    for club in clubs:
        head = read_memory(handle, club + 0x38, 12)
        if not head or len(head) < 12:
            continue
        x, = struct.unpack_from("<I", head, 0)
        flag = head[8]
        if flag != 0 or x < 0x10000:
            division["(sem objeto X)"] += 1
            continue
        data = read_memory(handle, x + 0xDC, 0x10)
        if not data or len(data) < 0x10:
            continue
        division[struct.unpack_from("<I", data, 0)[0]] += 1
        flag_ea[data[0xEA - 0xDC]] += 1
    print("\nDivisão pelo caminho do SWAP_TEAMS (clube +0x38 -> X, valor em X+0xDC):")
    for value, count in division.most_common(25):
        label = ""
        if isinstance(value, int):
            if value in rules:
                label = f"  = objeto de regras da Série {rules[value]}"
            elif value > 0x10000:
                target = read_memory(handle, value, 0x400)
                if target:
                    found = [f"{key}@+{target.find(raw):#x}" for raw, key in ids_by_raw.items() if target.find(raw) >= 0]
                    found += [f"regras {key}@+{target.find(struct.pack('<I', ptr)):#x}" for ptr, key in rules.items()
                              if target.find(struct.pack("<I", ptr)) >= 0]
                    vt = struct.unpack_from("<I", target, 0)[0]
                    label = f"  vtable {vt:#x}" + (f"  contém ID {found}" if found else "")
            print(f"  {value:#010x}: {count} clubes{label}")
        else:
            print(f"  {value}: {count} clubes")
    print("  X+0xEA (byte):", dict(flag_ea.most_common(8)))

    # Campos trocados pelo SWAP_TEAMS (executor em 0x00AAC550).
    ids = {struct.pack("<I", info["id"]): key for key, info in SERIES.items()}
    print("\nCampos trocados pelo SWAP_TEAMS: valores mais comuns entre os clubes")
    for rel in (0x54, 0x5C, 0x60, 0x64):
        values = Counter()
        for club in clubs:
            data = read_memory(handle, club + rel, 4)
            if data and len(data) == 4:
                values[struct.unpack("<I", data)[0]] += 1
        print(f"  +0x{rel:02X}: {len(values)} valores distintos")
        for value, count in values.most_common(12):
            note = ""
            target = read_memory(handle, value, 0x200) if value > 0x10000 else None
            if target:
                found = [f"{key}@+{target.find(raw):#x}" for raw, key in ids.items() if target.find(raw) >= 0]
                note = f"  objeto contém ID {found}" if found else ""
            print(f"      {value:#010x}: {count} clubes{note}")


if __name__ == "__main__":
    main()
