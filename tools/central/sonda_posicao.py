"""Sonda: onde o jogo guarda a "Nova Posição" em treino de um jogador (só leitura).

    python tools\\central\\sonda_posicao.py antes  <nome>
    (no jogo: Treino > Geral > Nova Posição)
    python tools\\central\\sonda_posicao.py depois <nome>

Guarda, antes e depois, o objeto do jogador, o PLAYING_DATA dele e uma janela em volta de cada lugar
da memória que aponta para o jogador (R) ou guarda o UID dele; depois mostra os bytes que mudaram.
"""

from __future__ import annotations

import pickle
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import leitor  # noqa: E402
from live_player_memory import iter_regions, read_memory  # noqa: E402

SAVE = HERE.parents[1] / "workspace" / "central"
RADIUS = 0x400


def find_player(jogo: leitor.Jogo, name: str) -> int:
    for r in jogo.table(leitor.PEOPLE):
        if r and jogo.u32(r) == leitor.PLAYER_VT:
            full = f"{jogo.text(jogo.u32(r + 44))} {jogo.text(jogo.u32(r + 48))} {jogo.text(jogo.u32(r + 52))}"
            if name.lower() in full.lower():
                return r
    raise SystemExit(f"não achei {name}")


def snapshot(jogo: leitor.Jogo, r: int) -> dict[int, bytes]:
    uid = jogo.u32(r + 0x14)
    index = jogo.table(leitor.PEOPLE).index(r)              # posição na tabela de pessoas
    block = jogo.u32(r - 32)
    needles = (struct.pack("<I", uid), struct.pack("<I", r), struct.pack("<I", r - 0xCC), struct.pack("<I", r + 4),
               struct.pack("<I", block), struct.pack("<I", index))
    print(f"UID {uid}, índice {index}, PLAYING 0x{block:08X}")
    spots = {r - 0xCC, jogo.u32(r - 32)}
    for base, size in iter_regions(jogo.handle):
        if size > 64 << 20:
            continue
        data = read_memory(jogo.handle, base, size)
        if not data:
            continue
        for needle in needles:
            i = data.find(needle)
            while i != -1:
                if i % 4 == 0:
                    spots.add(base + i - RADIUS)
                i = data.find(needle, i + 1)
    out = {}
    for spot in spots:
        raw = read_memory(jogo.handle, spot, 2 * RADIUS)
        if raw:
            out[spot] = raw
    return out


def main() -> None:
    action, name = sys.argv[1], " ".join(sys.argv[2:])
    jogo = leitor.Jogo()
    r = find_player(jogo, name)
    SAVE.mkdir(parents=True, exist_ok=True)
    file = SAVE / f"sonda_posicao_{jogo.u32(r + 0x14)}.pkl"
    if action == "antes":
        snap = snapshot(jogo, r)
        file.write_bytes(pickle.dumps({"r": r, "snap": snap}))
        print(f"jogador em 0x{r:08X}; {len(snap)} janelas guardadas")
        return
    before = pickle.loads(file.read_bytes())
    for spot, old in sorted(before["snap"].items()):
        new = read_memory(jogo.handle, spot, len(old)) or b""
        diffs = [i for i in range(min(len(old), len(new))) if old[i] != new[i]]
        if diffs and len(diffs) < 80:
            print(f"janela 0x{spot:08X} (R{spot + RADIUS - r:+#x} no centro):")
            for i in diffs:
                at = spot + i
                print(f"   0x{at:08X} (R{at - r:+#x}): {old[i]:02X} -> {new[i]:02X}")


if __name__ == "__main__":
    main()
