"""Vagas da Libertadores de 2026 (ver docs/CALENDARIO_2026.md).

O FM06 monta a Libertadores com 38 clubes:
1. participantes (0x00C06710): campeão + N por país (ARG 5, BRA 5, demais 3,
   México incluído);
2. fase preliminar (0x00C05260): 12 clubes, o pior de cada país e mais um do
   país do campeão (6 confrontos);
3. grupos (0x00C05430): os que sobraram por país (ARG 4, BRA 4, demais 2) +
   os 6 da preliminar, em 4 potes de 8 pelo país (pote 1 = ARG e BRA, pote 2 =
   COL, MEX, PAR, URU).

Patch: Brasil 7, Argentina 6, México 0 (continua 38). A vaga do México na
preliminar vai para a Argentina (com 11 clubes o 11º ficava sem adversário e
o jogo caía); nos grupos o Brasil leva 6 e o México 0; o pote 1 fica com 10 e
um desvio passa os 2 brasileiros piores para o pote 2, como estavam os
mexicanos.
"""

from __future__ import annotations

from .exe_cave import SECTION_VA, Asm, off, sec_off, section_swaps, u32

POTS_HOOK = 0x00C05695            # push -1 ×3 (antes de 0x00ACD4B0), depois do cálculo dos potes
POTS_BACK = 0x00C0569B
POTS_STUB = SECTION_VA + 0x4000

# (endereço, bytes originais, bytes novos)
IMMEDIATES = (
    (0xC06773, b"\x6A\x05", b"\x6A\x06"),                          # participantes: Argentina 6
    (0xC067A1, b"\x6A\x05", b"\x6A\x07"),                          # participantes: Brasil 7
    (0xC067F5, b"\x6A\x03", b"\x6A\x00"),                          # participantes: México 0
    (0xC05332, b"\x68\x7B\x01\x00\x00", b"\x68\x71\x06\x00\x00"),  # preliminar: México -> Argentina
    (0xC05486, b"\x6A\x04", b"\x6A\x06"),                          # grupos: Brasil 6
    (0xC054BF, b"\x6A\x02", b"\x6A\x00"),                          # grupos: México 0
)


def _pots_stub() -> bytes:
    """Pote 1 com mais de 8: passa para o pote 2 os primeiros do pote 1 a partir da posição 4.

    A lista dos grupos começa com os 4 argentinos e segue com os brasileiros do
    pior para o melhor (0x00C04E00 pega do fim dos participantes). Potes:
    bytes em [esp+0x38+i]; quantidade de clubes: word em [esp+0x30].
    """
    a = Asm(POTS_STUB)
    a.raw(b"\x0F\xB7\x4C\x24\x30")             # movzx ecx, word [esp+0x30]
    a.raw(b"\x33\xC0\x33\xD2")                 # xor eax, eax ; xor edx, edx
    count = len(a.code)
    a.raw(b"\x3B\xC1\x7D\x0B")                 # cmp eax, ecx ; jge +11
    a.raw(b"\x80\x7C\x04\x38\x01\x75\x01\x42") # cmp byte [esp+eax+0x38], 1 ; jne +1 ; inc edx
    a.raw(b"\x40\xEB\x00")                     # inc eax ; jmp count
    a.code[-1] = (count - len(a.code)) & 0xFF
    a.raw(b"\xB8\x04\x00\x00\x00")             # mov eax, 4
    demote = len(a.code)
    a.raw(b"\x83\xFA\x08\x7E\x14")             # cmp edx, 8 ; jle done
    a.raw(b"\x3B\xC1\x7D\x10")                 # cmp eax, ecx ; jge done
    a.raw(b"\x80\x7C\x04\x38\x01\x75\x06")     # cmp byte [esp+eax+0x38], 1 ; jne +6
    a.raw(b"\xC6\x44\x04\x38\x02\x4A")         # mov byte [esp+eax+0x38], 2 ; dec edx
    a.raw(b"\x40\xEB\x00")                     # inc eax ; jmp demote
    a.code[-1] = (demote - len(a.code)) & 0xFF
    a.push(-1).push(-1).push(-1)               # instruções substituídas
    a.jmp(POTS_BACK)
    return bytes(a.code)


def build(data: bytes):
    from .exe_patches import Swap

    swaps = list(section_swaps(data))
    stub = _pots_stub()
    swaps.append(Swap(sec_off(POTS_STUB), bytes(len(stub)), stub))
    swaps.append(Swap(off(POTS_HOOK), b"\x6A\xFF" * 3,
                      b"\xE9" + u32(POTS_STUB - (POTS_HOOK + 5)) + b"\x90"))
    swaps += [Swap(off(va), old, new) for va, old, new in IMMEDIATES]
    return tuple(swaps)
