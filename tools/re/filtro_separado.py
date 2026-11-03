r"""Teste na memória: filtro da Central separado do Pesquisar > Jogadores (instalar / estado / desfazer).

O pedido de busca (0x786F25) escolhe o conjunto do humano por tipo; Central e Pesquisar usam o mesmo
(tipo 1), cujo filtro é o objeto em [conjunto+0x124] (lido por 0x6AF1A0; trocado e apagado em
0xA6BCF0, que aceita nulo). Em 0x786F32, logo depois da escolha, o desvio troca esse ponteiro
conforme a tela que pediu: seção atual (gravada pelo patch em .fm26+0xD7F4) = 'tcdv' -> filtro da
Central; outra -> o outro. O que está fora fica guardado aqui. O lado que ainda não tem filtro recebe uma cópia feita pelo
clone do jogo (nulo travou 0xCC4C40 no teste de 03/11). Se o contêiner mudar (outro save carregado), o estado recomeça.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools" / "re"), str(ROOT / "scripts")]

import chamada_remota as cr  # noqa: E402
from fm06patch.exe_cave import SECTION_VA as B  # noqa: E402
from live_player_memory import read_memory  # noqa: E402

SITE, OLD = 0x00786F32, bytes.fromhex("807E08FF7E6B")      # cmp byte [esi+8],-1 ; jle 0x786FA3
JLE_TO, BACK = 0x00786FA3, 0x00786F38
SECTION_NOW = B + 0xD7F4                                     # seção atual (gancho de abertura)
CONT, SAVED, INSTALLED, SWAPS, CLONES = B + 0xDCC0, B + 0xDCC4, B + 0xDCC8, B + 0xDCCC, B + 0xDCD0
CREATE = 0x00CC47F0                                         # cria pela fábrica (usado no clone 0xA6AED3)
STUB = B + 0xDD00
TCDV = int.from_bytes(b"tcdv", "big")


def le(v: int) -> bytes:
    return (v & 0xFFFFFFFF).to_bytes(4, "little")


def stub_code() -> bytes:
    from fm06patch.centro import filter_code
    return filter_code(STUB, CONT, SECTION_NOW)


def main() -> None:
    _, h = cr.game()
    raw = lambda at, n: read_memory(h, at, n) or b""
    u = lambda at: struct.unpack("<I", raw(at, 4))[0]
    action = sys.argv[1]
    jump = b"\xE9" + le(STUB - (SITE + 5)) + b"\x90"
    if action == "instalar":
        site = raw(SITE, 6)
        if site != OLD and site[:1] != b"\xE9":
            raise SystemExit(f"bytes inesperados em 0x{SITE:08X}: {site.hex()}")
        cr.poke(h, SITE, OLD)                                # tira a sonda antiga, se houver
        cr.poke(h, CONT, bytes(16))
        cr.poke(h, STUB, stub_code())
        cr.poke(h, SITE, jump)
        print(f"filtro separado instalado ({len(stub_code())} bytes em 0x{STUB:08X})")
    elif action == "atualizar":                              # troca só o código, mantém os filtros guardados
        cr.poke(h, SITE, OLD)
        cr.poke(h, STUB, stub_code())
        cr.poke(h, SITE, jump)
        print(f"código atualizado ({len(stub_code())} bytes), estado mantido")
    elif action == "desfazer":
        cr.poke(h, SITE, OLD)
        print("original de volta (o filtro que estiver no conjunto fica)")
    else:
        cont, saved, inst, swaps = u(CONT), u(SAVED), raw(INSTALLED, 1)[0], u(SWAPS)
        sec = raw(SECTION_NOW, 4)[::-1].decode("latin1")
        now = 0
        if cont:
            s = u(u(cont + 0x10) + 4)
            now = u(s + 0x124)
        print(f"seção {sec} | instalado: {'Central' if inst else 'outro'} 0x{now:08X} | guardado 0x{saved:08X} | trocas {swaps} | clones {u(CLONES)}")


if __name__ == "__main__":
    main()
