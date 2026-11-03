r"""Sonda do filtro compartilhado (Central x Pesquisar > Jogadores). Só anota e lê; não muda a busca.

Em 0x786F32 (pedido de busca, depois de o jogo escolher o conjunto em 0x54AA10: esi = conjuntos do
humano, [esi+8] = índice escolhido) um desvio grava esi e conta os pedidos. A foto guarda cada conjunto
(0x120 bytes) e os objetos que ele aponta (1 nível, 0x80 bytes), para comparar duas fotos.

    python tools\re\filtro_busca.py instalar
    python tools\re\filtro_busca.py foto pesquisar_idade      (depois de abrir a tela)
    python tools\re\filtro_busca.py diff antes depois
    python tools\re\filtro_busca.py desfazer
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools" / "re"), str(ROOT / "scripts")]

import chamada_remota as cr  # noqa: E402
from fm06patch.exe_cave import SECTION_VA as B  # noqa: E402
from live_player_memory import read_memory  # noqa: E402

SITE, OLD = 0x00786F32, bytes.fromhex("807E08FF7E6B")      # cmp byte [esi+8],-1 ; jle 0x786FA3
SLOT, STUB = B + 0xDC00, B + 0xDC10
OUT = ROOT / "workspace" / "filtro"


def stub_code() -> bytes:
    code = b"\x89\x35" + SLOT.to_bytes(4, "little") + b"\xFF\x05" + (SLOT + 4).to_bytes(4, "little")
    code += bytes.fromhex("807E08FF") + b"\x0F\x8E" + (0x00786FA3 - (STUB + len(code) + 4 + 6)).to_bytes(4, "little", signed=True)
    code += b"\xE9" + (0x00786F38 - (STUB + len(code) + 5)).to_bytes(4, "little", signed=True)
    return code


def main() -> None:
    _, h = cr.game()
    raw = lambda at, n: read_memory(h, at, n) or b""
    u = lambda at: struct.unpack("<I", raw(at, 4))[0]
    action = sys.argv[1]
    if action == "instalar":
        if raw(SITE, 6) != OLD:
            raise SystemExit(f"bytes inesperados em 0x{SITE:08X}: {raw(SITE, 6).hex()} (já instalada?)")
        if raw(STUB, 0x40) != bytes(0x40) and raw(STUB, len(stub_code())) != stub_code():
            raise SystemExit("área da sonda ocupada")
        cr.poke(h, SLOT, bytes(8))
        cr.poke(h, STUB, stub_code())
        cr.poke(h, SITE, b"\xE9" + (STUB - (SITE + 5)).to_bytes(4, "little", signed=True) + b"\x90")
        print("sonda instalada: abra a busca no jogo")
    elif action == "desfazer":
        cr.poke(h, SITE, OLD)
        print("original de volta")
    elif action == "foto":
        sets, calls = u(SLOT), u(SLOT + 4)
        if not sets:
            raise SystemExit("ainda sem pedido de busca: abra a tela no jogo")
        data, count = u(sets + 0x10), u(sets + 0x14)
        shot = {"pedidos": calls, "conjuntos": sets, "escolhido": raw(sets + 8, 1)[0], "itens": []}
        for i in range(min(count, 16)):
            s = u(data + 4 * i)
            body = raw(s, 0x120)
            children = {}
            for k in range(0, len(body), 4):
                p = struct.unpack_from("<I", body, k)[0]
                if 0x01000000 < p < 0x7FFF0000 and p != s:
                    child = raw(p, 0x80)
                    if child:
                        children[f"{k:#x}"] = [p, child.hex()]
            shot["itens"].append({"end": s, "tipo": body[5], "corpo": body.hex(), "filhos": children})
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f"{sys.argv[2]}.json").write_text(json.dumps(shot, indent=1), encoding="utf-8")
        print(f"pedidos {calls}, escolhido {shot['escolhido']}, tipos {[x['tipo'] for x in shot['itens']]}")
    elif action == "diff":
        a, b = (json.loads((OUT / f"{name}.json").read_text(encoding="utf-8")) for name in sys.argv[2:4])
        print(f"escolhido: {a['escolhido']} -> {b['escolhido']}")
        for x, y in zip(a["itens"], b["itens"]):
            ca, cb = bytes.fromhex(x["corpo"]), bytes.fromhex(y["corpo"])
            for k in range(0, len(ca), 4):
                if ca[k:k + 4] != cb[k:k + 4]:
                    print(f"  conjunto tipo {x['tipo']} +{k:#05x}: {ca[k:k+4].hex()} -> {cb[k:k+4].hex()}")
            for key in sorted(set(x["filhos"]) & set(y["filhos"])):
                pa, da = x["filhos"][key]; pb, db = y["filhos"][key]
                da, db = bytes.fromhex(da), bytes.fromhex(db)
                if pa == pb and da != db:
                    diffs = [f"+{k:#x}: {da[k:k+4].hex()}->{db[k:k+4].hex()}" for k in range(0, min(len(da), len(db)), 4) if da[k:k+4] != db[k:k+4]]
                    print(f"  conjunto tipo {x['tipo']} [{key}]=0x{pa:08X}: " + "; ".join(diffs[:8]))


if __name__ == "__main__":
    main()
