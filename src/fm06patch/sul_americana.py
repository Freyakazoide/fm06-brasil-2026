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
A competição continua montada em 1/8 (temporada de julho a dezembro): com
25/1 e temporada de janeiro, o New Game (1/7/2005) montava na hora a edição
de 2005 com datas de abril já passadas e a de 2006 nunca era montada. Datas
de agosto a novembro (1ª fase 9/8, 2ª 23/8, oitavas 13/9, quartas 4/10,
semifinal 25/10, final 21/11). O chaveamento da 1ª fase (0x00C05FD0) vira
uma tabela fixa.
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
IN_COMP = 0x00A1E830               # TEAM.na_competição(comp): só vê quem ainda está vivo nela
IN_LIBERTADORES_CALL = 0x00C06C85  # 0x00C068C0: exclusão de quem está na Libertadores
LIBERTADORES_STUB = SECTION_VA + 0x4300
COMP_BY_ID = 0x00582440            # ([0x014EAA34]).competição(ID)
COMPS = 0x014EAA34
SERIE_A_ID, COPA_DO_BRASIL_ID = 0x19017, 0x1901B
LIBERTADORES_TOP = 7               # 1º a 7º da Série A anterior vão à Libertadores

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
    # datas (push mês, push dia; mês começa em 0). A competição é montada em
    # 1/8 (construtor 0x00C05F10, temporada de julho a dezembro): tudo depois
    # disso. 1ª fase 9/8 e 2ª fase 23/8 ficam como no original.
    (0xC0744B, "6a06", "6a07"), (0xC0744D, "6a13", "6a03"),   # sorteio 19/7 -> 3/8
    (0xC077F6, "6a12", "6a04"),                               # quartas 18/10 -> 4/10
    (0xC0788D, "6a0a", "6a09"), (0xC0788F, "6a16", "6a19"),   # semifinal 22/11 -> 25/10
    (0xC078F5, "6a0b", "6a0a"), (0xC078F7, "6a06", "6a15"),   # final 6/12 -> 21/11
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
    a.raw(b"\x66\xC7\x44\x24\x4A\x03\x00")           # +0x2E: prorrogação e pênaltis
    a.raw(b"\xC6\x44\x24\x4C\x00")                   # +0x30: sem jogo extra
    a.jmp(FINAL_BACK)
    return bytes(a.code)


def _r16_date() -> bytes:
    a = Asm(R16_DATE)
    # (hora 19:30, dia 13, setembro, 2000, quinta, 0) -> 0x00B3B760 em 0x00C076C5
    a.raw(b"\x53\x6A" + bytes([THURSDAY]) + b"\x68" + u32(2000) + b"\x6A\x08\x6A\x0D\x68" + u32(0x78A))
    a.raw(b"\xEB" + bytes([(R16_DATE_BACK - (a.here + 2)) & 0xFF]))
    return bytes(a.code)


def _libertadores_stub() -> bytes:
    """No lugar de 0x00A1E830 na exclusão: também conta como "está na Libertadores" o
    brasileiro do 1º ao 7º da Série A anterior (TEAM+0x5C, +0x60) e o campeão da Copa do
    Brasil. Quem caiu nos grupos da Libertadores (maio) já saiu da lista de competições do
    time quando a Sul-Americana é montada (agosto) e entrava nela (teste: Flamengo e
    Fluminense nas duas)."""
    a = Asm(LIBERTADORES_STUB)
    a.raw(b"\x56\x8B\xF1\xFF\x74\x24\x08\x8B\xCE")     # push esi ; mov esi, ecx ; push [esp+8] ; mov ecx, esi
    a.call(IN_COMP)
    a.raw(b"\x85\xC0")
    jne_done = len(a.code); a.raw(b"\x75\x00")
    a.raw(b"\x8B\x46\x5C\x85\xC0")                      # mov eax, [esi+0x5C] ; test eax, eax
    je_cup = len(a.code); a.raw(b"\x74\x00")
    a.raw(b"\x0F\xB6\x56\x60\x4A\x83\xFA" + bytes([LIBERTADORES_TOP - 1]))  # posição - 1 ; cmp edx, 6
    ja_cup = len(a.code); a.raw(b"\x77\x00")
    a.raw(b"\x8B\xC8\x8B\x10\xFF\x52\x10")              # divisão.ID()
    a.raw(b"\x3D" + u32(SERIE_A_ID))
    je_yes = len(a.code); a.raw(b"\x74\x00")
    cup = len(a.code)
    a.raw(b"\x8B\x0D" + u32(COMPS)).push(COPA_DO_BRASIL_ID).call(COMP_BY_ID)
    a.raw(b"\x85\xC0")
    je_no = len(a.code); a.raw(b"\x74\x00")
    a.raw(b"\x8B\x40\x1C\x85\xC0")                      # campeão anterior (COMP_HISTORY)
    je_no2 = len(a.code); a.raw(b"\x74\x00")
    a.raw(b"\x3B\x70\x24")                              # cmp esi, [eax+0x24]
    jne_no = len(a.code); a.raw(b"\x75\x00")
    yes = len(a.code)
    a.raw(b"\xB8\x01\x00\x00\x00")
    jmp_done = len(a.code); a.raw(b"\xEB\x00")
    no = len(a.code)
    a.raw(b"\x33\xC0")
    done = len(a.code)
    a.raw(b"\x5E\xC2\x04\x00")
    code = bytearray(a.code)
    for at, target in ((jne_done, done), (je_cup, cup), (ja_cup, cup), (je_yes, yes), (je_no, no),
                       (je_no2, no), (jne_no, no), (jmp_done, done)):
        code[at + 1] = target - (at + 2)
    return bytes(code)


def build(data: bytes):
    from .exe_patches import Swap

    swaps = list(section_swaps(data))
    for base, code in ((BRACKET_STUB, _bracket_stub()), (BRACKET_TABLE, _bracket_table()),
                       (FINAL_STUB, _final_stub()), (LIBERTADORES_STUB, _libertadores_stub())):
        swaps.append(Swap(sec_off(base), bytes(len(code)), code))
    swaps += [Swap(off(va), bytes.fromhex(old), bytes.fromhex(new)) for va, old, new in CHANGES]
    r16 = _r16_date()
    swaps.append(Swap(off(R16_DATE), data[off(R16_DATE):off(R16_DATE) + len(r16)], r16))
    swaps.append(Swap(off(IN_LIBERTADORES_CALL), b"\xE8" + u32(IN_COMP - (IN_LIBERTADORES_CALL + 5)),
                      b"\xE8" + u32(LIBERTADORES_STUB - (IN_LIBERTADORES_CALL + 5))))
    for hook, stub in ((BRACKET_HOOK, BRACKET_STUB), (FINAL_HOOK, FINAL_STUB)):
        swaps.append(Swap(off(hook), data[off(hook):off(hook) + 5], b"\xE9" + u32(stub - (hook + 5))))
    return tuple(swaps)
