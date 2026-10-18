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

from .exe_cave import SECTION_VA, Asm, _relocate, _replace, off, sec_off, section_swaps, u32

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


# Datas de 2026. A tabela do calendário internacional (0x00C047D0, Libertadores) guarda
# cada rodada como data de 2000 com dia da semana (quarta, 21h); o jogo mantém a semana
# e o dia da semana em cada ano. Mata-mata e final ficam em 0x00C07980.
# (endereço do byte, original, novo) — imediatos de push imm8.
DATES_2026 = (
    # preliminar: 2/2 e 9/2 -> 23/2 e 1/3 (2006: qua 22/2 e qua 1/3)
    (0xC047EF, 0x02, 0x17), (0xC0480E, 0x01, 0x02), (0xC04810, 0x09, 0x01),
    # grupos, 10 datas (A–D usam 0, 2, 4, 5, 7, 9; E–H usam 1, 3, 4, 6, 8, 9):
    # abril e maio, 6 rodadas: 5, 12, 19/4, 3, 10, 24/5 (E–H na quinta: 6, 13/4, 4, 11/5)
    (0xC0482F, 0x01, 0x03), (0xC04831, 0x17, 0x05),
    (0xC04850, 0x02, 0x03), (0xC04852, 0x01, 0x06), (0xC04854, 0x04, 0x05),
    (0xC04871, 0x02, 0x03), (0xC04873, 0x08, 0x0C),
    (0xC04892, 0x02, 0x03), (0xC04894, 0x0F, 0x0D), (0xC04896, 0x04, 0x05),
    (0xC048B3, 0x02, 0x03), (0xC048B5, 0x16, 0x13),
    (0xC048D4, 0x02, 0x04), (0xC048D6, 0x1D, 0x03),
    (0xC048F5, 0x03, 0x04), (0xC048F7, 0x05, 0x04), (0xC048F9, 0x04, 0x05),
    (0xC04916, 0x03, 0x04), (0xC04918, 0x0C, 0x0A),
    (0xC04937, 0x03, 0x04), (0xC04939, 0x13, 0x0B), (0xC0493B, 0x04, 0x05),
    (0xC04958, 0x03, 0x04), (0xC0495A, 0x1A, 0x18),
    # oitavas: 3/5 e 10/5 -> 9/8 e 16/8; sorteio 18/3 -> 3/6
    (0xC04979, 0x04, 0x07), (0xC0497B, 0x03, 0x09), (0xC0499A, 0x04, 0x07), (0xC0499C, 0x0A, 0x10),
    (0xC07EFE, 0x02, 0x05), (0xC07F00, 0x12, 0x03),
    # quartas: 17/5 e 24/5 -> 13/9 e 20/9
    (0xC049BB, 0x04, 0x08), (0xC049BD, 0x11, 0x0D), (0xC049DC, 0x04, 0x08), (0xC049DE, 0x18, 0x14),
    # semifinal (ano de Copa: 5/7; outros: 7/6) -> 18/10 e 25/10 nos dois casos
    (0xC08036, 0x06, 0x09), (0xC08038, 0x05, 0x12), (0xC0803C, 0x05, 0x09), (0xC0803E, 0x07, 0x12),
    # final (ano de Copa: 19/7; outros: 21/6) -> 28/11 nos dois casos, sem ajuste de dia
    (0xC080CE, 0x06, 0x0A), (0xC080D0, 0x13, 0x1C), (0xC080D4, 0x05, 0x0A), (0xC080D6, 0x15, 0x1C),
)
FINAL_WEEKDAY = (0xC080C1, b"\x57", b"\x53")      # push edi (quarta) -> push ebx (0: data exata)
# final em jogo único: a conta do ano de Copa (já sem efeito) vira legs = 1 na rodada (+0x34),
# desempate prorrogação + pênaltis (+0x2E = 3) e sem jogo extra (+0x30 = 0; texto das regras em
# 0x006A1EA2). Com o desempate da semifinal (0xE) e o jogo extra ligado, a final empatada foi
# repetida 7 dias depois (teste 2).
FINAL_LEGS = (0xC080A6,
              bytes.fromhex("0FB7959C00000081EACE07000081E20300008079054A83CAFC42"),
              b"\xC6\x44\x24\x6C\x01"            # mov byte [esp+0x6C], 1
              + b"\x66\xC7\x44\x24\x66\x03\x00"   # mov word [esp+0x66], 3
              + b"\xC6\x44\x24\x68\x00"            # mov byte [esp+0x68], 0
              + b"\x90" * 9)
FINAL_BRANCH = (0xC080CB, b"\x75\x06", b"\xEB\x06")
# temporada da competição (construtor 0x00C062F0): +0x85 mês do início, +0x86 ano do início
# (somado ao ano da temporada), +0x87 mês do fim, +0x88 ano do fim; meses base 0, o dia
# vem de cada função que usa (ex.: 0x00AC2140 usa o dia 15). Original: janeiro a agosto do
# mesmo ano; com a final em 28/11 a Libertadores não virava (teste 1). As tentativas
# seguintes gravaram um "dia" em +0x88, que é o ano: fim 30 anos (teste 2) e 19 anos
# (teste 3) depois, e ela nunca virou. Agora: fim em dezembro do mesmo ano, como a
# Sul-Americana (0x00C05F84: +0x87 = 11, +0x88 = 0).
SEASON_END = (0xC06383, bytes.fromhex("c686870000" "0007"), bytes.fromhex("c686870000" "000b"))


# Virada da temporada. A Libertadores está no sistema da América do Sul (sam_get_settings,
# 0x00ACFFF0(19, 8)): em 19/9 o jogo vira só as competições já terminadas (0x00AD41F3). Com a
# final em 28/11 ela ainda estava nas quartas, ficava para trás e a de 2027 nunca era montada
# (testes 1 a 4). A Sul-Americana tem virada própria no método diário (vtable +0x1BC,
# 0x00C04CC0: no dia 180 do ano, se terminou, 0x00AD0C60). A Libertadores ganha uma cópia desse
# método com o dia 348 (15/12; 14/12 em ano bissexto); o ano passa a ser o seguinte e a
# montagem continua em 21/1.
DAILY_SOURCE = 0x00C04CC0
DAILY_SIZE = 0x4E                      # até o ret 4
DAILY_CALLS = (0x09, 0x44)             # 0x00AC5AA0 e 0x00AD0C60
DAILY_DAY_AT = 0x12                    # cmp word [0x014EAB38], 0xB4
DAILY_STUB = SECTION_VA + 0x5200
LIBERTADORES_DAILY_SLOT = 0x01154CF4 + 0x1BC
ROLLOVER_DAY = 348


def _daily_stub(data: bytes) -> bytes:
    code = bytearray(data[off(DAILY_SOURCE):off(DAILY_SOURCE) + DAILY_SIZE])
    _relocate(code, DAILY_SOURCE, DAILY_STUB, DAILY_CALLS)
    _replace(code, DAILY_DAY_AT, bytes.fromhex("66813D38AB4E01B400"),
             bytes.fromhex("66813D38AB4E01") + ROLLOVER_DAY.to_bytes(2, "little"))
    return bytes(code)


def build_dates(data: bytes):
    from .exe_patches import Swap

    swaps = list(section_swaps(data))
    stub = _daily_stub(data)
    swaps.append(Swap(sec_off(DAILY_STUB), bytes(len(stub)), stub))
    swaps.append(Swap(off(LIBERTADORES_DAILY_SLOT), u32(0x00AC5AA0), u32(DAILY_STUB)))
    swaps += [Swap(off(va), bytes([old]), bytes([new])) for va, old, new in DATES_2026]
    swaps += [Swap(off(va), old, new) for va, old, new in (FINAL_WEEKDAY, FINAL_LEGS, FINAL_BRANCH,
                                                             SEASON_END)]
    return tuple(swaps)
