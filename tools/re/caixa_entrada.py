r"""Caixa de entrada do humano na memória (só leitura): foto e comparação, para mapear a notícia lida.

A lista é o NEWS_ITEM_ARRAY (vtable 0x010F6DD4) em [humano - 0x1E0]: +4 dados, +8 quantidade. Cada
notícia: vtable da classe (RTTI ..._NEWS), +0x14 data (u16 dia, u16 ano do motor), +0x18 marcas,
+0x1C número de série. Conferido em 03/11 (75 notícias; Jhonnathan em MEDIA_PLAYER_FORM_NEWS +0x34).

    python tools\re\caixa_entrada.py foto antes
    python tools\re\caixa_entrada.py diff antes depois
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "central")]

import leitor  # noqa: E402

ARRAY_VT, ARRAY_REL = 0x010F6DD4, -0x1E0
OUT = ROOT / "workspace" / "imprensa"


def inbox(jogo: leitor.Jogo) -> list[tuple[int, bytes]]:
    human = next(p for p in jogo.table(leitor.PEOPLE) if p and jogo.u32(p) == leitor.HUMAN_VT)
    array = human + ARRAY_REL
    if jogo.u32(array) != ARRAY_VT:
        raise SystemExit(f"NEWS_ITEM_ARRAY não está em humano{ARRAY_REL:#x}")
    data, count = jogo.u32(array + 4), jogo.u32(array + 8)
    return [(p, jogo.raw(p, 0x80)) for p in struct.unpack(f"<{count}I", jogo.raw(data, 4 * count))]


def main() -> None:
    action = sys.argv[1]
    OUT.mkdir(parents=True, exist_ok=True)
    if action == "foto":
        items = inbox(leitor.Jogo())
        (OUT / f"caixa_{sys.argv[2]}.json").write_text(json.dumps([[p, b.hex()] for p, b in items]), encoding="utf-8")
        print(f"{len(items)} notícias")
    elif action == "diff":
        a, b = (dict((p, bytes.fromhex(x)) for p, x in json.loads((OUT / f"caixa_{n}.json").read_text(encoding="utf-8"))) for n in sys.argv[2:4])
        for p in sorted(set(a) | set(b)):
            if p not in a or p not in b:
                print(f"0x{p:08X} {'nova' if p in b else 'saiu'}")
                continue
            for k in range(0, 0x80):
                if a[p][k] != b[p][k]:
                    serial = struct.unpack_from("<I", b[p], 0x1C)[0]
                    print(f"0x{p:08X} série {serial:#x} +{k:#x}: {a[p][k]:02x} -> {b[p][k]:02x}")


if __name__ == "__main__":
    main()
