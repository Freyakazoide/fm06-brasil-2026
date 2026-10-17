"""Estaduais de 2026 no estadual genérico do FM06 (ver docs/reversing/estaduais.md).

1. O contêiner BRA_STATE (0x00BB96E0) passa a criar todos os estados com o
   construtor genérico 0x00BB50B0 (BRA_STATE_LEAGUE): RJ, RS, PR, PE, BA, SC,
   PA, TO e os da classe "Paraíba" tinham código próprio.
2. O construtor genérico chama a tabela original de parâmetros (0x00BB3330)
   e, em seguida, um desvio grava o formato de 2026 de cada estado: clubes,
   grupos, turnos, quantos vão ao mata-mata e quantos caem.
3. As datas da fase de liga (0x00BB3DF0) passam a ser: início 7/1; fim
   calculado para a final cair em 8/3 (quartas, semifinal e final são
   marcadas pelo jogo uma ou duas semanas depois do fim da fase de liga) ou,
   se as rodadas não cabem até lá, depois da última rodada (fim por estado,
   na tabela).

Limites do estadual genérico (pequenas liberdades em relação a 2026):
- o mata-mata tem 8, 4 ou 2 classificados (sem 1º e 2º direto à semifinal);
- grupos jogam dentro do grupo (não contra o outro grupo);
- clubes por estado = clubes do estado no banco. Com menos, o jogo pega os N
  primeiros da lista (teste: SP com 16, RS e PR com 12 ficaram sem os
  grandes) ou põe todos na tabela com o calendário de N (BA, PA e MT com 10:
  13 e 14 clubes na tabela, 9 rodadas, a fase de liga nunca terminou e a
  virada dos estaduais travou). Os participantes de 2026 entram com os
  clubes, no banco;
- rebaixados como no original, para o par estadual/divisão de acesso continuar
  equilibrado na virada (sobe = cai).
"""

from __future__ import annotations

import csv
import struct
from collections import Counter
from pathlib import Path
from datetime import date, timedelta

from .exe_cave import SECTION_VA, Asm, off, sec_off, section_swaps, u32

CONTAINER = 0x00BB96E0
GENERIC_CTOR = 0x00BB50B0
SPECIAL_CTORS = (0x00BB5310, 0x00BB5390, 0x00BB5410, 0x00BB5510, 0x00BB5610, 0x00BB5690,
                 0x00BB5720, 0x00BB7350, 0x00BB7870)
CONTAINER_SIZE = 0x7D0
PARAMS_CALL = 0x00BB510C          # call 0x00BB3330 no construtor genérico
PARAMS_ORIGINAL = 0x00BB3330
DATES = 0x00BB3DF0                # (início dia*, início mês*, fim dia*, fim mês*), ret 0x10

MINIMUM_TEAMS = 0x00BB2840       # bra_get_minimum_division_teams
MINIMUM_TEAMS_SIZE = 0x600
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
    "MT": (14, 1, 1, 4, 3),   # M2 (10 clubes e 6 classificados no real; banco tem 14)
    "MS": (8, 1, 1, 4, 2),    # M2 (10 clubes no real; banco do FM06 tem 8)
    "BA": (13, 1, 1, 4, 2),   # M1 (10 no real; banco tem 13)
    "PE": (8, 1, 1, 4, 2),    # M2
    "CE": (10, 1, 1, 4, 2),   # M6 (grupos + 2ª fase no real)
    "RN": (8, 1, 1, 4, 2),    # M2
    "PB": (10, 1, 1, 4, 1),   # M1
    "AL": (8, 1, 1, 4, 1),    # M1
    "SE": (10, 1, 1, 4, 2),   # M2 (7 classificados no real)
    "MA": (8, 1, 1, 4, 2),    # M1
    "PI": (8, 1, 1, 4, 2),    # M1
    "PA": (14, 1, 1, 4, 2),   # M5 (12 clubes no real; banco tem 14)
    "AM": (8, 1, 1, 4, 1),    # M6 (dois turnos no real)
    "TO": (10, 1, 1, 4, 1),   # M1 (8 no real)
    "AC": (8, 1, 1, 4, 1),    # M1
    "RO": (7, 1, 2, 4, 2),    # M6 (ida e volta)
    "RR": (8, 1, 1, 4, 1),    # M1 (9 clubes no real)
    "AP": (8, 1, 1, 4, 1),    # M1
}
SEM_SEGUNDA_FASE = 7              # +0x18 da tabela: 7 = sem 2ª fase, 0 = mata-mata, 1 = liga final
MATA_MATA = 0

START = (7, 0)                    # 7/1 (1ª rodada no domingo seguinte)
# fim da fase de liga conforme os classificados, para a final cair em 8/3
END_8 = (8, 1)                    # 8/2: quartas 15/2, semi 22/2, final 8/3
END_4 = (15, 1)                   # 15/2: semi 22/2, final 8/3
END_2 = (1, 2)                    # 1/3: final 8/3
END_0 = (8, 2)                    # 8/3: só a fase de liga
END_DEFAULT = (8, 2)              # estado fora da tabela
# O jogo só marca as rodadas que cabem até o fim da fase de liga (duas por semana,
# domingo e quarta); as que não cabem nunca acontecem e a fase não termina (teste:
# Baiano com 13 clubes, 13 rodadas e só 11 marcadas até 12/2). Se as rodadas não
# cabem, o fim vai para depois da última, com folga; o mata-mata vem em seguida.
FIRST_ROUND = date(2006, 1, 8)
MARGIN_DAYS = 7


def rounds(teams: int, groups: int, legs: int) -> int:
    per_group = -(-teams // groups)
    return (per_group + per_group % 2 - 1) * legs


def league_end(teams: int, groups: int, legs: int, qualified: int) -> tuple[int, int]:
    """(dia, mês 0-based) do fim da fase de liga."""
    target = END_0 if qualified == 0 else END_2 if qualified <= 2 else END_4 if qualified <= 4 else END_8
    wanted = date(2006, target[1] + 1, target[0])
    needed = FIRST_ROUND + timedelta(days=-(-7 * (rounds(teams, groups, legs) - 1) // 2) + MARGIN_DAYS)
    end = max(wanted, needed)
    return end.day, end.month - 1


CLUBS_CSV = Path(__file__).resolve().parents[2] / "data" / "brasil" / "estaduais" / "clubes_2026_modelo.csv"


def club_counts() -> dict[str, int]:
    """Clubes de cada estadual na lista de 2026 (o jogo põe na tabela todos os
    clubes do estado; o calendário tem de ser feito para esse mesmo número)."""
    if not CLUBS_CSV.exists():
        return {}
    rows = csv.DictReader(CLUBS_CSV.open(encoding="utf-8-sig"))
    return dict(Counter(r["uf"].strip().upper() for r in rows))


def table_bytes() -> bytes:
    out = bytearray()
    counts = club_counts()
    for uf, (teams, groups, legs, qualified, relegated) in FORMATO_2026.items():
        teams = counts.get(uf, teams)
        stage2 = MATA_MATA if qualified else SEM_SEGUNDA_FASE
        day, month = league_end(teams, groups, legs, qualified)
        out += struct.pack("<I8B", ID[uf], teams, groups, legs, qualified, relegated, stage2, day, month)
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
    a.raw(b"\x8B\x44\x24\x04\x66\xC7\x00" + struct.pack("<H", START[0]))   # *início dia
    a.raw(b"\x8B\x44\x24\x08\xC6\x00" + bytes([START[1]]))                 # *início mês
    a.raw(b"\x8B\x11")                                                    # mov edx, [ecx] (ID)
    a.raw(b"\xB8" + u32(TABLE))                                            # mov eax, TABLE
    loop = len(a.code)
    a.raw(b"\x8B\x08\x85\xC9")                                            # mov ecx, [eax] ; test ecx, ecx
    je_missing = len(a.code); a.raw(b"\x74\x00")
    a.raw(b"\x3B\xCA")                                                    # cmp ecx, edx
    je_hit = len(a.code); a.raw(b"\x74\x00")
    a.raw(b"\x83\xC0\x0C")                                                # add eax, 12
    jmp_loop = len(a.code); a.raw(b"\xEB\x00")
    missing = len(a.code)
    a.raw(b"\xB1" + bytes([END_DEFAULT[0]]) + b"\xB5" + bytes([END_DEFAULT[1]]))   # mov cl, dia ; mov ch, mês
    jmp_write = len(a.code); a.raw(b"\xEB\x00")
    hit = len(a.code)
    a.raw(b"\x8A\x48\x0A\x8A\x68\x0B")                                    # mov cl, [eax+10] ; mov ch, [eax+11]
    write = len(a.code)
    a.raw(b"\x8B\x44\x24\x0C\x0F\xB6\xD1\x66\x89\x10")                      # *fim dia = cl
    a.raw(b"\x8B\x44\x24\x10\x88\x28")                                      # *fim mês = ch
    a.raw(b"\xC2\x10\x00")
    code = bytearray(a.code)
    for at, target in ((je_missing, missing), (je_hit, hit), (jmp_loop, loop), (jmp_write, write)):
        code[at + 1] = (target - (at + 2)) & 0xFF
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
    # bra_get_minimum_division_teams (0x00BB2840): o jogo só deixa o Brasil
    # jogável se cada estadual tiver exatamente o número registrado (máximo -2 =
    # igual ao mínimo); passa a ser o da lista de 2026.
    counts = club_counts()
    base = off(MINIMUM_TEAMS)
    for uf, cid in ID.items():
        pattern = b"\x6A\xFE\x6A"
        at = data.find(pattern, base, base + MINIMUM_TEAMS_SIZE)
        while at >= 0 and data[at + 4:at + 7] + data[at + 7:at + 11] != b"\x6A\x00\x68" + u32(cid):
            at = data.find(pattern, at + 1, base + MINIMUM_TEAMS_SIZE)
        if at < 0:
            raise ValueError(f"estaduais: mínimo de clubes de {uf} não encontrado")
        if uf in counts:
            swaps.append(Swap(at + 3, data[at + 3:at + 4], bytes([counts[uf]])))
    # 2ª divisões estaduais (não são disputadas; recebem os rebaixados): mínimo 0,
    # porque completar a lista de 2026 tira clubes delas (ex.: Acre 4 -> 2, Roraima 1 -> 0)
    from .estaduais_clubes import LOWER_ID
    for uf, cid in LOWER_ID.items():
        needle = b"\x6A\x00\x68" + u32(cid)
        at = data.find(needle, base, base + MINIMUM_TEAMS_SIZE)
        if at < 4 or data[at - 4:at - 2] != b"\x6A\xFF" or data[at - 2] != 0x6A:
            raise ValueError(f"estaduais: mínimo da 2ª divisão de {uf} não encontrado")
        swaps.append(Swap(at - 1, data[at - 1:at], b"\x00"))
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
