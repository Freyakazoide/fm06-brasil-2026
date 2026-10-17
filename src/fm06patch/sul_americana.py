"""Sul-Americana 2026 (SAM_SUD_CUP, ver docs/CALENDARIO_2026.md).

Mata-mata de 28 clubes em 6 rodadas, no lugar dos 34 do FM06:
- 1ª fase (código 0x19): 16 clubes dos 8 países menores, 2 por país, em
  confrontos do mesmo país (como no original);
- 2ª fase (0x1A): os 8 vencedores, 4 confrontos (no lugar dos playoffs);
- oitavas: 6 argentinos + 6 brasileiros + os 4 da 2ª fase;
- quartas, semifinal e final (jogo único em 21/11).

Participantes (0x00C06FE0 -> 0x00C068C0): Brasil 8 -> 6 (7º a 12º da Série A,
sem quem está na Libertadores), México e EUA 0; o campeão anterior não é
inscrito à parte (em 2026 ele vai à Libertadores) e pode entrar pela tabela;
a exclusão de quem está na Libertadores vale para Brasil, Argentina e Peru.
A competição passa a ser montada em 25/1 (era 1/8), para as datas de abril
existirem; o chaveamento da 1ª fase (0x00C05FD0) vira uma tabela fixa.
"""

from __future__ import annotations

from .exe_cave import SECTION_VA, Asm, off, sec_off, section_swaps, u32

BRACKET_HOOK = 0x00C06108          # chaveamento à mão dos argentinos e brasileiros
BRACKET_BACK = 0x00C06287          # criação do mata-mata com a lista
LIST_ADD = 0x005583D0
BRACKET_STUB = SECTION_VA + 0x4200
BRACKET_TABLE = SECTION_VA + 0x4240
FINAL_HOOK = 0x00C07916
FINAL_BACK = 0x00C0791B
FINAL_STUB = SECTION_VA + 0x4280
R16_DATE = 0x00C07701              # código morto reaproveitado para a data das oitavas
R16_DATE_BACK = 0x00C076C5
THURSDAY = 5                       # dia da semana das rodadas (a Libertadores é na quarta)

ARG, BRA = 0x30, 0x20              # lista da Argentina em [esp+0x2C], Brasil em [esp+0x1C] (+4 do ebx)
# vagas 16–27 da lista: A2 B5 A0 B1 B2 A5 A3 B4 A1 B0 B3 A4 (melhores fora de casa no 1º
# jogo; o 1º da Argentina e o do Brasil só se cruzam na final)
BRACKET_ORDER = ((2, ARG), (5, BRA), (0, ARG), (1, BRA), (2, BRA), (5, ARG),
                 (3, ARG), (4, BRA), (1, ARG), (0, BRA), (3, BRA), (4, ARG))

# (endereço, original, novo)
CHANGES = (
    # participantes
    (0xC0704C, "6a08", "6a06"),            # Brasil 6
    (0xC07088, "6a02", "6a00"),            # México 0
    (0xC070D3, "6a01", "6a00"),            # EUA 0
    (0xC070FE, "7423", "eb23"),            # campeão anterior não é inscrito à parte
    (0xC06AEE, "7460", "eb60"),            # ... e pode entrar pela tabela do país
    (0xC06BD6, "7458", "eb58"),
    (0xC06C4D, "83e802", "83e8fe"),        # exclusão da Libertadores: Brasil, Argentina, Peru
    (0xC06C52, "83e803", "83e807"),
    # montada em 25/1, temporada a partir de janeiro
    (0xC05F6A, "6a076a01", "6a006a19"),
    (0xC05F7D, "06", "00"),
    # mata-mata (0x00C07380)
    (0xC073B1, "22", "1c"),                # 28 clubes
    (0xC07479, "1c", "10"),                # 1ª fase: 16 clubes
    (0xC0749F, "0e", "08"),                # 8 confrontos
    (0xC07589, "6a1053558d", "e9a1000000"),  # sem as vagas 16–27 na 1ª fase
    (0xC076E5, "06", "0c"),                # oitavas: 12 entram
    (0xC076EC, "0e", "07"),                # 7 dias entre os jogos
    (0xC076FF, "6a1c", "eb52"),            # sem as vagas antigas 28–33
    (0xC076B5, "536a", "eb4a"),            # data das oitavas no código reaproveitado
    (0xC07790, "6a04", "6a01"),            # vencedores da 2ª fase nos confrontos 1, 2, 5, 6
    (0xC0779F, "6a05", "6a02"),
    (0xC077AD, "6a06", "6a05"),
    (0xC077BC, "6a07", "6a06"),
    (0xC078EF, "55", "53"),                # final na data exata
    # datas (push mês, push dia; mês começa em 0)
    (0xC0744B, "6a06", "6a03"), (0xC0744D, "6a13", "6a01"),   # sorteio 1/4
    (0xC07465, "6a07", "6a03"), (0xC07467, "6a09", "6a0f"),   # 1ª fase 15/4
    (0xC0765C, "6a07", "6a06"), (0xC0765E, "6a17", "6a16"),   # 2ª fase 22/7
    (0xC077F4, "6a09", "6a08"), (0xC077F6, "6a12", "6a10"),   # quartas 16/9
    (0xC0788D, "6a0a", "6a09"), (0xC0788F, "6a16", "6a15"),   # semifinal 21/10
    (0xC078F5, "6a0b", "6a0a"), (0xC078F7, "6a06", "6a15"),   # final 21/11
    (0xC0745E, "6a04", "6a05"), (0xC07655, "6a04", "6a05"),   # quinta: 1ª e 2ª fases
    (0xC077ED, "6a04", "6a05"),                               # quinta: quartas
)


def _bracket_stub() -> bytes:
    a = Asm(BRACKET_STUB)
    a.raw(b"\x53\xBB" + u32(BRACKET_TABLE))          # push ebx ; mov ebx, tabela
    loop = len(a.code)
    a.raw(b"\x0F\xB6\x03\x3C\xFF")                   # movzx eax, byte [ebx] ; cmp al, 0xFF
    je_done = len(a.code); a.raw(b"\x74\x00")
    a.raw(b"\x0F\xB6\x53\x01\x8D\x0C\x14")           # movzx edx, byte [ebx+1] ; lea ecx, [esp+edx]
    a.raw(b"\x50\x8B\x01\xFF\x50\x28")               # push eax ; lista.get(índice)
    a.raw(b"\x85\xC0\x74\x0A")                       # test eax, eax ; je próximo
    a.raw(b"\x50\x8D\x4C\x24\x14").call(LIST_ADD)    # lista principal ([esp+0xC]).add(clube)
    a.raw(b"\x83\xC3\x02")                           # próximo: add ebx, 2
    a.raw(b"\xEB" + bytes([(loop - (len(a.code) + 2)) & 0xFF]))
    a.code[je_done + 1] = len(a.code) - (je_done + 2)
    a.raw(b"\x5B").jmp(BRACKET_BACK)
    return bytes(a.code)


def _bracket_table() -> bytes:
    return bytes(x for pair in BRACKET_ORDER for x in pair) + b"\xFF\xFF"


def _final_stub() -> bytes:
    a = Asm(FINAL_STUB)
    a.raw(b"\x66\x89\x7C\x24\x42")                   # instrução substituída
    a.raw(b"\xC6\x44\x24\x50\x01")                   # rodada +0x34 = 1 jogo
    a.jmp(FINAL_BACK)
    return bytes(a.code)


def _r16_date() -> bytes:
    a = Asm(R16_DATE)
    # (hora 19:30, dia 12, agosto, 2000, quinta, 0) -> 0x00B3B760 em 0x00C076C5
    a.raw(b"\x53\x6A" + bytes([THURSDAY]) + b"\x68" + u32(2000) + b"\x6A\x07\x6A\x0C\x68" + u32(0x78A))
    a.raw(b"\xEB" + bytes([(R16_DATE_BACK - (a.here + 2)) & 0xFF]))
    return bytes(a.code)


def build(data: bytes):
    from .exe_patches import Swap

    swaps = list(section_swaps(data))
    for base, code in ((BRACKET_STUB, _bracket_stub()), (BRACKET_TABLE, _bracket_table()),
                       (FINAL_STUB, _final_stub())):
        swaps.append(Swap(sec_off(base), bytes(len(code)), code))
    swaps += [Swap(off(va), bytes.fromhex(old), bytes.fromhex(new)) for va, old, new in CHANGES]
    r16 = _r16_date()
    swaps.append(Swap(off(R16_DATE), data[off(R16_DATE):off(R16_DATE) + len(r16)], r16))
    for hook, stub in ((BRACKET_HOOK, BRACKET_STUB), (FINAL_HOOK, FINAL_STUB)):
        swaps.append(Swap(off(hook), data[off(hook):off(hook) + 5], b"\xE9" + u32(stub - (hook + 5))))
    return tuple(swaps)
