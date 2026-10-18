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
um desvio refaz os potes com 8 clubes cada (ver _pots_stub).
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
    """Potes da fase de grupos: 4 potes de exatamente 8 clubes.

    Pote original pelo país (0x00C05595): Argentina e Brasil 1; Colômbia, Uruguai e
    Paraguai 2; Bolívia, Chile, Equador e Peru 3; Venezuela 4; o campeão 1; quem vem da
    Pré-Libertadores leva o pote do país. Com o Brasil com 6 diretos e brasileiros e
    argentinos vindos da Pré, o pote 1 pode chegar a 14 e o pote 2 a 12. No teste de
    1/3/2026 o jogo caiu ao montar os jogos de um grupo com um clube faltando
    (0x00B07E4A, ordenação dos 4 clubes do grupo em 0x00B0D800).

    Lista dos grupos: 0–3 argentinos, 4–9 brasileiros do pior para o melhor, depois os
    demais países, os vindos da Pré e a Venezuela. Os clubes são ordenados pelo pote
    original e, dentro dele, pela ordem 0–3, 9 a 4, 10 em diante; os 8 primeiros vão
    para o pote 1, os 8 seguintes para o 2... Potes: bytes em [esp+0x38+i]; quantidade:
    word em [esp+0x30] (no desvio, depois de 4 push: +0x48 e +0x40).
    """
    code = bytearray()
    labels: dict[str, int] = {}
    fixups: list[tuple[int, str]] = []

    def emit(raw: bytes) -> None:
        code.extend(raw)

    def jump(opcode: int, label: str) -> None:       # salto curto
        code.extend(bytes([opcode, 0]))
        fixups.append((len(code) - 1, label))

    def mark(label: str) -> None:
        labels[label] = len(code)

    emit(b"\x53\x56\x57\x55")                       # push ebx, esi, edi, ebp
    emit(b"\x0F\xB7\x4C\x24\x40")                   # movzx ecx, word [esp+0x40]
    emit(b"\x33\xD2")                               # xor edx, edx        (posição no ranking)
    emit(b"\xBE\x01\x00\x00\x00")                   # mov esi, 1          (pote original)
    mark("pot")
    emit(b"\x33\xFF")                               # xor edi, edi        (ordem k)
    mark("k")
    emit(b"\x3B\xF9"); jump(0x7D, "k_end")           # cmp edi, ecx ; jge
    emit(b"\x8B\xC7")                               # mov eax, edi        (i = k)
    emit(b"\x83\xFF\x04"); jump(0x7C, "use")         # cmp edi, 4 ; jl
    emit(b"\x83\xFF\x09"); jump(0x7F, "use")         # cmp edi, 9 ; jg
    emit(b"\xB8\x0D\x00\x00\x00\x2B\xC7")           # i = 13 - k (brasileiros, melhor primeiro)
    mark("use")
    emit(b"\x3B\xC1"); jump(0x7D, "next")            # cmp eax, ecx ; jge
    emit(b"\x0F\xB6\x5C\x04\x48")                   # movzx ebx, byte [esp+eax+0x48]
    emit(b"\x3B\xDE"); jump(0x75, "next")            # cmp ebx, esi ; jne
    emit(b"\x8B\xDA\xC1\xEB\x03")                   # ebx = posição / 8
    emit(b"\x83\xFB\x03"); jump(0x7E, "ok")          # cmp ebx, 3 ; jle
    emit(b"\xBB\x03\x00\x00\x00")                   # mov ebx, 3
    mark("ok")
    emit(b"\x83\xC3\x11")                           # pote novo + 0x10 (marca)
    emit(b"\x88\x5C\x04\x48")                       # mov [esp+eax+0x48], bl
    emit(b"\x42")                                   # inc edx
    mark("next")
    emit(b"\x47"); jump(0xEB, "k")                   # inc edi ; jmp
    mark("k_end")
    emit(b"\x46\x83\xFE\x04"); jump(0x7E, "pot")     # inc esi ; cmp esi, 4 ; jle
    emit(b"\x33\xFF")                               # xor edi, edi
    mark("strip")
    emit(b"\x3B\xF9"); jump(0x7D, "done")            # cmp edi, ecx ; jge
    emit(b"\x8A\x5C\x3C\x48")                       # mov bl, [esp+edi+0x48]
    emit(b"\x80\xFB\x10"); jump(0x72, "skip")        # cmp bl, 0x10 ; jb
    emit(b"\x80\xEB\x10\x88\x5C\x3C\x48")           # tira a marca
    mark("skip")
    emit(b"\x47"); jump(0xEB, "strip")               # inc edi ; jmp
    mark("done")
    emit(b"\x5D\x5F\x5E\x5B")                       # pop ebp, edi, esi, ebx
    for at, label in fixups:
        rel = labels[label] - (at + 1)
        if not -128 <= rel <= 127:
            raise ValueError("desvio dos potes: salto longe demais")
        code[at] = rel & 0xFF
    a = Asm(POTS_STUB)
    a.raw(bytes(code))
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
