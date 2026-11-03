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
    c = bytearray()
    def rel(target: int, size: int) -> bytes:
        return le(target - (STUB + len(c) + size))
    c += b"\x60"                                             # pushad
    c += b"\xA1" + le(CONT)                                  # mov eax, [CONT]
    c += b"\x39\xF0"                                         # cmp eax, esi
    c += b"\x74\x17"                                         # je mesmo (+23 = 6 + 10 + 7)
    c += b"\x89\x35" + le(CONT)                              # mov [CONT], esi
    c += b"\xC7\x05" + le(SAVED) + le(0)                     # mov [SAVED], 0
    c += b"\xC6\x05" + le(INSTALLED) + b"\x01"               # mov byte [INSTALLED], 1 (o do save é da Central)
    c += b"\x0F\xBE\x46\x08"                                 # mesmo: movsx eax, byte [esi+8]
    c += b"\x85\xC0"                                         # test eax, eax
    fim_js = len(c); c += b"\x0F\x88" + le(0)                # js fim
    c += b"\x3A\x46\x14"                                     # cmp al, [esi+0x14]
    fim_jae = len(c); c += b"\x0F\x83" + le(0)               # jae fim
    c += b"\x8B\x4E\x10"                                     # mov ecx, [esi+0x10]  (dados da lista)
    c += b"\x8B\x1C\x81"                                     # mov ebx, [ecx+eax*4] (conjunto)
    c += b"\x85\xDB"                                         # test ebx, ebx
    fim_jz = len(c); c += b"\x0F\x84" + le(0)                # jz fim
    c += b"\x80\x7B\x05\x01"                                 # cmp byte [ebx+5], 1  (tipo jogadores)
    fim_jne = len(c); c += b"\x0F\x85" + le(0)               # jne fim
    c += b"\x31\xD2"                                         # xor edx, edx
    c += b"\x81\x3D" + le(SECTION_NOW) + le(TCDV)            # cmp dword [SECTION_NOW], 'tcdv'
    c += b"\x0F\x94\xC2"                                     # sete dl
    c += b"\x3A\x15" + le(INSTALLED)                         # cmp dl, [INSTALLED]
    fim_je = len(c); c += b"\x0F\x84" + le(0)                # je fim
    # primeira troca: o outro lado ainda não tem filtro. Nulo trava 0xCC4C40 (dump de 03/11), então
    # clona o atual como o jogo faz em 0xA6AEC4: fábrica = (f+4)->vfunc8; novo = 0xCC47F0(fábrica)-4;
    # novo->vfunc58(f) copia o conteúdo.
    c += b"\x83\x3D" + le(SAVED) + b"\x00"                   # cmp dword [SAVED], 0
    troca_jne = len(c); c += b"\x0F\x85" + le(0)             # jne troca
    c += b"\x8B\x8B\x24\x01\x00\x00"                         # mov ecx, [ebx+0x124]   (f)
    c += b"\x85\xC9"                                         # test ecx, ecx
    fim_jz2 = len(c); c += b"\x0F\x84" + le(0)               # jz fim
    c += b"\x51"                                             # push ecx               (guarda f)
    c += b"\x83\xC1\x04"                                     # add ecx, 4
    c += b"\x8B\x01"                                         # mov eax, [ecx]
    c += b"\xFF\x50\x08"                                     # call [eax+8]           (fábrica)
    c += b"\x50"                                             # push eax
    c += b"\xE8" + rel(CREATE, 5)                            # call 0xCC47F0
    c += b"\x83\xC4\x04"                                     # add esp, 4
    c += b"\x5A"                                             # pop edx                (f)
    c += b"\x85\xC0"                                         # test eax, eax
    fim_jz3 = len(c); c += b"\x0F\x84" + le(0)               # jz fim
    c += b"\x83\xE8\x04"                                     # sub eax, 4             (novo)
    c += b"\xA3" + le(SAVED)                                 # mov [SAVED], eax
    c += b"\x52"                                             # push edx               (f)
    c += b"\x89\xC1"                                         # mov ecx, eax
    c += b"\x8B\x00"                                         # mov eax, [eax]
    c += b"\xFF\x50\x58"                                     # call [eax+0x58]        (novo.copia(f))
    c += b"\xFF\x05" + le(CLONES)                            # inc dword [CLONES]
    troca = len(c)
    c += b"\x31\xD2"                                         # xor edx, edx  (dl de novo: as chamadas o perdem)
    c += b"\x81\x3D" + le(SECTION_NOW) + le(TCDV)            # cmp dword [SECTION_NOW], 'tcdv'
    c += b"\x0F\x94\xC2"                                     # sete dl
    c[troca_jne + 2:troca_jne + 6] = le(troca - (troca_jne + 6))
    c += b"\x8B\x83\x24\x01\x00\x00"                         # mov eax, [ebx+0x124]
    c += b"\x8B\x0D" + le(SAVED)                             # mov ecx, [SAVED]
    c += b"\x89\x8B\x24\x01\x00\x00"                         # mov [ebx+0x124], ecx
    c += b"\xA3" + le(SAVED)                                 # mov [SAVED], eax
    c += b"\x88\x15" + le(INSTALLED)                         # mov [INSTALLED], dl
    c += b"\xFF\x05" + le(SWAPS)                             # inc dword [SWAPS]
    fim = len(c)
    for at in (fim_js, fim_jae, fim_jz, fim_jne, fim_je, fim_jz2, fim_jz3):
        c[at + 2:at + 6] = le(fim - (at + 6))
    c += b"\x61"                                             # popad
    c += b"\x80\x7E\x08\xFF"                                 # cmp byte [esi+8], -1   (original)
    c += b"\x0F\x8E" + rel(JLE_TO, 6)                        # jle 0x786FA3           (original)
    c += b"\xE9" + rel(BACK, 5)                              # jmp 0x786F38
    return bytes(c)


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
