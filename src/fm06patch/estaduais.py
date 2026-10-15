"""Estaduais de 2026 no estadual genérico do FM06 (ver docs/reversing/estaduais.md).

1. O contêiner BRA_STATE (0x00BB96E0) passa a criar todos os estados com o
   construtor genérico 0x00BB50B0 (BRA_STATE_LEAGUE): RJ, RS, PR, PE, BA, SC,
   PA, TO e os da classe "Paraíba" tinham código próprio.
2. O construtor genérico chama a tabela original de parâmetros (0x00BB3330)
   e, em seguida, um desvio grava o formato de 2026 de cada estado: clubes,
   grupos, turnos, quantos vão ao mata-mata e quantos caem.
3. As datas da fase de liga (0x00BB3DF0) passam a ser: início 11/1; fim
   calculado para a final cair em 8/3 (quartas, semifinal e final são
   marcadas pelo jogo uma ou duas semanas depois do fim da fase de liga).

Limites do estadual genérico (pequenas liberdades em relação a 2026):
- o mata-mata tem 8, 4 ou 2 classificados (sem 1º e 2º direto à semifinal);
- grupos jogam dentro do grupo (não contra o outro grupo);
- clubes por estado nunca acima do original (o banco pode não ter mais clubes)
  e, por enquanto, também não abaixo nos estados em que o corte tirou os
  grandes: o jogo pega os N primeiros da lista do estado (teste: SP com 16,
  RS e PR com 12 ficaram sem os grandes). Os participantes de 2026 entram com
  os clubes, no banco;
- rebaixados como no original, para o par estadual/divisão de acesso continuar
  equilibrado na virada (sobe = cai).
"""

from __future__ import annotations

import struct

from .exe_cave import SECTION_VA, Asm, off, sec_off, section_swaps, u32

CONTAINER = 0x00BB96E0
GENERIC_CTOR = 0x00BB50B0
SPECIAL_CTORS = (0x00BB5310, 0x00BB5390, 0x00BB5410, 0x00BB5510, 0x00BB5610, 0x00BB5690,
                 0x00BB5720, 0x00BB7350, 0x00BB7870)
CONTAINER_SIZE = 0x7D0
PARAMS_CALL = 0x00BB510C          # call 0x00BB3330 no construtor genérico
PARAMS_ORIGINAL = 0x00BB3330
DATES = 0x00BB3DF0                # (início dia*, início mês*, fim dia*, fim mês*), ret 0x10

PARAMS_STUB = SECTION_VA + 0x2000
DATES_STUB = SECTION_VA + 0x2080
TABLE = SECTION_VA + 0x2100

ID = {
    "SP": 0x1901A, "RJ": 0x19018, "AC": 0x1A2B2, "AL": 0x1A2B1, "AM": 0x49C7F, "BA": 0x4B9AE,
    "CE": 0x4C76A, "DF": 0x4C76C, "ES": 0x4C76E, "GO": 0x4B9B0, "MA": 0x4C770, "MT": 0x4C774,
    "MS": 0x4C772, "MG": 0x4B9B2, "PA": 0x4C784, "PB": 0x4C776, "PR": 0x4B9B6, "PE": 0x4B9B4,
    "PI": 0x4C778, "RN": 0x4C77A, "RS": 0x49C7D, "RO": 0x4C77C, "RR": 0x4C77E, "SC": 0x4B9B8,
    "SE": 0x4C780, "TO": 0x4C782, "AP": 0x4C768,
}

# UF: (clubes, grupos, turnos, classificados ao mata-mata, rebaixados)
# Modelo de 2026 entre parênteses (docs/REGRAS_2026_ESTADUAIS_E_COPAS.md).
FORMATO_2026 = {
    "SP": (20, 2, 1, 8, 4),   # M5 (16 no real): 2 grupos de 10, 8 às quartas
    "RJ": (12, 2, 1, 8, 1),   # M4: 2 grupos de 6, quartas
    "MG": (12, 2, 1, 4, 2),   # M5: 3 grupos de 4, semifinal
    "ES": (10, 1, 1, 8, 2),   # M3: turno único, 8 às quartas
    "PR": (16, 2, 1, 8, 2),   # M4 (12 no real): 2 grupos de 8
    "SC": (12, 2, 1, 8, 1),   # M4
    "RS": (18, 2, 1, 8, 2),   # M4 (12 no real): 2 grupos de 9
    "GO": (12, 2, 1, 8, 3),   # M5: 8 às quartas
    "DF": (12, 2, 1, 4, 2),   # M1 (10 no real): 2 grupos de 6
    "MT": (10, 1, 1, 4, 3),   # M2 (6 classificados no real)
    "MS": (8, 1, 1, 4, 2),    # M2 (10 clubes no real; banco do FM06 tem 8)
    "BA": (10, 1, 1, 4, 2),   # M1
    "PE": (8, 1, 1, 4, 2),    # M2
    "CE": (10, 1, 1, 4, 2),   # M6 (grupos + 2ª fase no real)
    "RN": (14, 2, 1, 4, 2),   # M2 (8 no real): 2 grupos de 7
    "PB": (10, 1, 1, 4, 1),   # M1
    "AL": (8, 1, 1, 4, 1),    # M1
    "SE": (10, 1, 1, 4, 2),   # M2 (7 classificados no real)
    "MA": (8, 1, 1, 4, 2),    # M1
    "PI": (8, 1, 1, 4, 2),    # M1
    "PA": (10, 1, 1, 4, 2),   # M5 (12 clubes no real; banco do FM06 tem 10)
    "AM": (8, 1, 1, 4, 1),    # M6 (dois turnos no real)
    "TO": (10, 1, 1, 4, 1),   # M1 (8 no real)
    "AC": (6, 1, 2, 4, 1),    # M1 (8 clubes no real; banco do FM06 tem 6)
    "RO": (8, 1, 1, 4, 2),    # M6 (7 clubes, ida e volta no real)
    "RR": (8, 1, 1, 4, 1),    # M1 (9 clubes no real)
    "AP": (8, 1, 1, 4, 1),    # M1
}
SEM_SEGUNDA_FASE = 7              # +0x18 da tabela: 7 = sem 2ª fase, 0 = mata-mata, 1 = liga final
MATA_MATA = 0

START = (11, 0)                   # 11/1
# fim da fase de liga conforme os classificados, para a final cair em 8/3
END_8 = (8, 1)                    # 8/2: quartas 15/2, semi 22/2, final 8/3
END_4 = (15, 1)                   # 15/2: semi 22/2, final 8/3
END_2 = (1, 2)                    # 1/3: final 8/3
END_0 = (8, 2)                    # 8/3: só a fase de liga


def table_bytes() -> bytes:
    out = bytearray()
    for uf, (teams, groups, legs, qualified, relegated) in FORMATO_2026.items():
        stage2 = MATA_MATA if qualified else SEM_SEGUNDA_FASE
        out += struct.pack("<I6Bxx", ID[uf], teams, groups, legs, qualified, relegated, stage2)
    out += struct.pack("<I", 0)
    return bytes(out)


def _params_stub() -> bytes:
    a = Asm(PARAMS_STUB)
    a.raw(b"\x56\x8B\xF1")                         # push esi ; mov esi, ecx (bloco de parâmetros)
    a.raw(b"\xFF\x74\x24\x08")                     # push [esp+8] (ID)
    a.call(PARAMS_ORIGINAL)                        # tabela original (this = esi)
    a.raw(b"\x8B\x0E")                             # mov ecx, [esi] (ID)
    a.raw(b"\xB8" + u32(TABLE))                    # mov eax, TABLE
    loop = len(a.code)
    a.raw(b"\x8B\x10\x85\xD2")                     # mov edx, [eax] ; test edx, edx
    je_done = len(a.code); a.raw(b"\x74\x00")
    a.raw(b"\x3B\xD1")                             # cmp edx, ecx
    je_hit = len(a.code); a.raw(b"\x74\x00")
    a.raw(b"\x83\xC0\x0C")                         # add eax, 12
    jmp_loop = len(a.code); a.raw(b"\xEB\x00")
    hit = len(a.code)
    for i, field in enumerate((4, 5, 6, 7, 8)):
        a.raw(b"\x8A\x50" + bytes([4 + i]))        # mov dl, [eax+4+i]
        a.raw(b"\x88\x56" + bytes([field]))        # mov [esi+field], dl
    a.raw(b"\x8A\x50\x09\x88\x56\x18")             # +0x18 = tipo da 2ª fase
    done = len(a.code)
    a.raw(b"\x5E\xC2\x04\x00")                     # pop esi ; ret 4
    code = bytearray(a.code)
    for at, target in ((je_done, done), (je_hit, hit), (jmp_loop, loop)):
        code[at + 1] = (target - (at + 2)) & 0xFF
    return bytes(code)


def _dates_stub() -> bytes:
    a = Asm(DATES_STUB)
    a.raw(b"\x8B\x44\x24\x04\x66\xC7\x00" + struct.pack("<H", START[0]))   # *início dia = 11
    a.raw(b"\x8B\x44\x24\x08\xC6\x00" + bytes([START[1]]))                 # *início mês = 0
    a.raw(b"\x8A\x51\x07")                                                  # mov dl, [ecx+7] (classificados)
    ends = []
    for limit, (day, month) in ((0, END_0), (2, END_2), (4, END_4)):
        a.raw(b"\x80\xFA" + bytes([limit]))                                 # cmp dl, limit
        ja = len(a.code); a.raw(b"\x77\x00")                                # ja próximo
        a.raw(b"\xB0" + bytes([day]) + b"\xB4" + bytes([month]))            # mov al, dia ; mov ah, mês
        jmp = len(a.code); a.raw(b"\xEB\x00")
        ends.append((ja, jmp))
    last = len(a.code)
    a.raw(b"\xB0" + bytes([END_8[0]]) + b"\xB4" + bytes([END_8[1]]))
    write = len(a.code)
    a.raw(b"\x8B\x54\x24\x0C\x0F\xB6\xC8\x66\x89\x0A")                      # *fim dia = al
    a.raw(b"\x8B\x54\x24\x10\x88\x22")                                      # *fim mês = ah
    a.raw(b"\xC2\x10\x00")
    code = bytearray(a.code)
    for i, (ja, jmp) in enumerate(ends):
        nxt = ends[i + 1][0] - 3 if i + 1 < len(ends) else last
        code[ja + 1] = (nxt - (ja + 2)) & 0xFF
        code[jmp + 1] = (write - (jmp + 2)) & 0xFF
    return bytes(code)


def build(data: bytes):
    from .exe_patches import Swap

    swaps = list(section_swaps(data))
    params, dates, table = _params_stub(), _dates_stub(), table_bytes()
    if PARAMS_STUB + len(params) > DATES_STUB or DATES_STUB + len(dates) > TABLE:
        raise ValueError("estaduais: código não cabe")
    swaps += [
        Swap(sec_off(PARAMS_STUB), bytes(len(params)), params),
        Swap(sec_off(DATES_STUB), bytes(len(dates)), dates),
        Swap(sec_off(TABLE), bytes(len(table)), table),
        Swap(off(PARAMS_CALL), b"\xE8" + u32(PARAMS_ORIGINAL - (PARAMS_CALL + 5)),
             b"\xE8" + u32(PARAMS_STUB - (PARAMS_CALL + 5))),
        Swap(off(DATES), data[off(DATES):off(DATES) + 5], b"\xE9" + u32(DATES_STUB - (DATES + 5))),
    ]
    # construtores especiais -> genérico
    base = off(CONTAINER)
    for at in range(base, base + CONTAINER_SIZE - 5):
        if data[at] != 0xE8:
            continue
        va = at + 0x400000
        target = va + 5 + struct.unpack_from("<i", data, at + 1)[0]
        if target in SPECIAL_CTORS:
            swaps.append(Swap(at, data[at:at + 5], b"\xE8" + u32(GENERIC_CTOR - (va + 5))))
    return tuple(swaps)
