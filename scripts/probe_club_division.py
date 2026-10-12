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
TEAM_SIGNATURE = struct.pack("<II", 0x010EDF6C, 0x010EDF5C)
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


def class_name(handle, vtable: int) -> str:
    """Nome da classe C++ pelo RTTI do MSVC (vtable-4 -> COL -> TypeDescriptor)."""
    try:
        col, = struct.unpack("<I", read_memory(handle, vtable - 4, 4))
        td, = struct.unpack("<I", read_memory(handle, col + 12, 4))
        raw = read_memory(handle, td + 8, 80)
        return raw.split(b"\0", 1)[0].decode("latin1")
    except Exception:
        return f"vtable {vtable:#x}"


def main() -> None:
    handle = open_process(find_process_id(sys.argv[1] if len(sys.argv) > 1 else "fm.exe"))
    print("Procurando objetos das séries, IDs das competições e clubes...", flush=True)
    hits = scan(handle, {
        **{f"serie_{k}": struct.pack("<I", v["vtable"]) for k, v in SERIES.items()},
        **{f"id_{k}": struct.pack("<I", v["id"]) for k, v in SERIES.items()},
        "club": CLUB_SIGNATURE,
        "team": TEAM_SIGNATURE,
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

    # Caminho usado pelo SWAP_TEAMS (0x00AAC550): o nome leva a um TEAM;
    # TEAM+0x38 é o CLUB (se TEAM+0x40 == 0) e a divisão fica em CLUB+0xDC
    # (acessor 0x00A18CE0). Os objetos achados aqui já são CLUB.
    ids_by_raw = {struct.pack("<I", info["id"]): key for key, info in SERIES.items()}
    rules = {addr: k for k in SERIES for addr in hits.get(f"serie_{k}", [])}
    division = Counter()
    flag_ea = Counter()
    for club in clubs:
        data = read_memory(handle, club + 0xDC, 0x10)
        if not data or len(data) < 0x10:
            continue
        division[struct.unpack_from("<I", data, 0)[0]] += 1
        flag_ea[data[0xEA - 0xDC]] += 1
    print("\nDivisão de cada clube (CLUB+0xDC): valor = clubes, classe do objeto apontado")
    for value, count in division.most_common(40):
        label = ""
        if value in rules:
            label = f"  = objeto de regras da Série {rules[value]}"
        if value > 0x10000:
            target = read_memory(handle, value, 0x400)
            if target and len(target) >= 4:
                label += f"  {class_name(handle, struct.unpack_from('<I', target, 0)[0])}"
                found = [f"ID {key}@+{target.find(raw):#x}" for raw, key in ids_by_raw.items() if target.find(raw) >= 0]
                found += [f"regras {key}@+{target.find(struct.pack('<I', ptr)):#x}" for ptr, key in rules.items()
                          if target.find(struct.pack("<I", ptr)) >= 0]
                if found:
                    label += f"  contém {found}"
        print(f"  {value:#010x}: {count} clubes{label}")
    print("  CLUB+0xEA (byte):", dict(flag_ea.most_common(8)))

    # Objetos TEAM (Principal, Reservas, Sub-20…): o SWAP_TEAMS troca os
    # campos +0x54, +0x5C, +0x60 (byte) e +0x64 deles.
    teams = hits.get("team", [])
    club_set = set(clubs)
    links = Counter()
    for team in teams:
        data = read_memory(handle, team + 0x38, 12)
        if not data or len(data) < 12:
            continue
        club = struct.unpack_from("<I", data, 0)[0]
        links["TEAM+0x38 é um CLUB" if club in club_set else "TEAM+0x38 não é CLUB"] += 1
        links[f"TEAM+0x40 = {data[8]}"] += 1
    print(f"\nTimes (TEAM): {len(teams)}")
    for label, count in sorted(links.items()):
        print(f"  {label}: {count}")
    print(f"  CLUB: {class_name(handle, 0x010EFFCC)}  TEAM: {class_name(handle, 0x010EDF6C)}")

    # Campos do TEAM trocados pelo SWAP_TEAMS: qual deles aponta para a divisão?
    for rel, size in ((0x54, 4), (0x5C, 4), (0x60, 1), (0x64, 4)):
        values = Counter()
        for team in teams:
            data = read_memory(handle, team + rel, size)
            if data and len(data) == size:
                values[data[0] if size == 1 else struct.unpack("<I", data)[0]] += 1
        by_class = Counter()
        names = {}
        for value, count in values.items():
            name = ""
            if size == 4 and value > 0x10000:
                head = read_memory(handle, value, 4)
                if head and len(head) == 4:
                    name = class_name(handle, struct.unpack("<I", head)[0])
            names[value] = name
            by_class[name or "(não é objeto)"] += count
        print(f"\nTEAM+0x{rel:02X}: {len(values)} valores distintos; por classe: {dict(by_class.most_common(8))}")
        for value, count in values.most_common(15):
            note = f"  = regras da Série {rules[value]}" if value in rules else ""
            print(f"    {value:#010x}: {count} times  {names[value]}{note}")

if __name__ == "__main__":
    main()
