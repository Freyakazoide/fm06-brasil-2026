"""Ano exibido + 20 (ver docs/reversing/ano_inicio.md).

O motor continua em 2005/06; só o ano que vai para a tela ganha 20 (temporada
2006 do motor = 2026; nascimento 1980 = 2000). Datas: a instrução que lê o ano
nos formatadores 0x00C665F0 (SI_DATE) e 0x00C56FA0 (SI_SHORT_DATE) passa a
somar 20. Demais textos (nomes de temporada 0x00AE18F0, histórico, prêmios,
notícias, nomes de competição com ano): a chamada que põe o número no texto
(0x00C55DE0, 0x00C53B90, 0x00C53B10) vai para um desvio que soma 20 antes.

Fica de fora: chave de arquivo das competições (0x00AC26B9, comp_<id>_<ano>),
serialização de SI_DATE (0x00C669D0), ids de listas (só o texto muda), dias
da semana (os do motor) e ano de fundação dos clubes.
"""

from __future__ import annotations


from .exe_cave import SECTION_VA, Asm, off, sec_off, section_swaps, u32

SET_NUMBER = 0x00C55DE0           # (índice, valor, contexto): número no texto
TEXT_INT = 0x00C53B90             # TEXT = int
TEXT_FROM_INT = 0x00C53B10        # TEXT(int)
YEAR_STUB = SECTION_VA + 0x4100
INT_STUB = SECTION_VA + 0x4130
INT2_STUB = SECTION_VA + 0x4140

# formatadores de data: (endereço, original, novo) — movsx do ano + add 20
DATE_LOADS = (
    (0x00C6672B, "668B76060FBFC6", "0FBF460683C014"),  # SI_DATE long+time: year #2
    (0x00C57162, "668B41060FBFD0", "0FBF510683C214"),  # short_reversed(+_leading_zero): year #1
    (0x00C571E1, "0FB7C799B964000000F7F9", "8D4714B164F6F10FB6D490"),  # shortest: 2-digit year (yy+20)%100
    (0x00C57366, "668B42060FBFC0", "0FBF420683C014"),  # short_day: year #3
    (0x00C57673, "668B42060FBFC0", "0FBF420683C014"),  # short_month_and_year
    (0x00C57763, "668B42060FBFC0", "0FBF420683C014"),  # month_and_year
    (0x00C578D1, "668B40060FBFC8", "0FBF480683C114"),  # long_no_day
    (0x00C57A56, "668B41060FBFD0", "0FBF510683C214"),  # long
    (0x00C57F9A, "668B42060FBFC0", "0FBF420683C014"),  # month_year
    (0x00C581C6, "668B40060FBFC8", "0FBF480683C114"),  # short (default): year #3
)

# chamadas de 0x00C55DE0 com ano (>= 100: + 20) ou ano de 2 dígitos ((aa + 20) % 100)
YEAR_CALLS = (
    0x00AE1918,  # AE18F0 season name: start year
    0x00AE1932,  # AE18F0 season name: (y+1)%100
    0x0061D2D6,  # 61D270 transfers panel title season #1
    0x0061D2F0,  # 61D270 #2 yy
    0x0061D3ED,  # 61D320 season dropdown item #1
    0x0061D409,  # 61D320 item #2 yy
    0x0075DE4E,  # 75DC80 history award season #1
    0x0075DE69,  # 75DC80 #2 yy
    0x0075DF12,  # 75DC80 named-in-team season #1
    0x0075DF2D,  # 75DC80 #2 yy
    0x0075E047,  # 75DC80 supporters POTY season #1
    0x0075E063,  # 75DC80 #2 yy
    0x0080F8FE,  # FINANCE_HISTORY_PANEL graph label mm/yy (#2 yy)
    0x00502E96,  # player history Year col #1 (split)
    0x00502EDB,  # player history Year col (shared #2 yy / #1 year)
    0x00501422,  # player stats title Y1
    0x00501439,  # player stats title Y2
    0x0050146E,  # player stats title Y
    0x0049E2C2,  # award name suffix Y-1
    0x0049E2D4,  # award name suffix Y
    0x0049F87C,  # AWARD_YEAR_PANEL year
    0x0049F8FE,  # AWARD_YEAR_PANEL year
    0x0049FD32,  # AWARD_YEAR_PANEL year
    0x0049FE57,  # AWARD_YEAR_PANEL year
    0x004A0532,  # AWARD_GOAL_PANEL year
    0x004A0B7C,  # AWARD_TEAM_PANEL year
    0x007FED10,  # COMPETITION_HISTORY_PANEL row year
    0x007FF000,  # comp history heading from
    0x007FF021,  # comp history heading to
    0x00803896,  # competition snapshot: cup winners year
    0x0087C4B5,  # euro coefficient column yy #1
    0x0087C4D0,  # euro coefficient column yy #2
    0x00584BA1,  # news: European qualifiers decided start year
    0x00584BBF,  # same: end yy
    0x0058059D,  # news: qualified for <year> <comp>
    0x00584FF3,  # news: MLS supporters shield year
    0x00B3D137,  # cup draw news: year last won
    0x00B3D17C,  # cup draw news: year last won
    0x00B3D438,  # cup draw news: #2 year last won
    0x00B3D651,  # cup draw news: <year> winners
    0x00B3D683,  # cup draw news: <year> winners
    0x00B3DCBE,  # group draw news: last won in <year>
    0x00B3DCFE,  # group draw news: last won in <year>
    0x005D7E14,  # player bio #4 year joined club
    0x005D8076,  # player bio #20 year drafted
    0x00813767,  # FINANCES_SUMMARY sponsor Ends <year>
    0x008137F2,  # FINANCES_SUMMARY sponsor Ends <year>
    0x00698AB8,  # CLIENT_COMP long name + year
    0x00698B08,  # CLIENT_COMP short name + year
    0x006976D2,  # CLIENT_COMP "<comp> <year> Qualification"
    0x0069EDF4,  # MLS past drafts title year
    0x00CE2A4A,  # DATE_DIALOG year popup item text
    0x00C9B2D7,  # SEASON_SELECTION_LIST item text (widget, see note)
)
# chamadas de 0x00C53B90 (TEXT = ano)
INT_CALLS = (
    0x00AE1944,  # AE18F0 single-year season name
    0x0075DE74,  # 75DC80 single-year
    0x0075DF38,  # 75DC80 single-year
    0x0075E06E,  # 75DC80 single-year
    0x0086FD08,  # team honours list first year
)
INT2_CALLS = (
    0x0086FD68,  # títulos do clube: anos seguintes da lista
)


def _year_stub() -> bytes:
    a = Asm(YEAR_STUB)
    a.raw(bytes.fromhex("8B442408"))                 # mov eax, [esp+8] (valor)
    a.raw(bytes.fromhex("83F8647D11"))               # cmp eax, 100 ; jge ano
    a.raw(bytes.fromhex("85C07814"))                 # test eax, eax ; js fora (negativo fica)
    a.raw(bytes.fromhex("83C01483F8647C08"))         # add eax, 20 ; cmp eax, 100 ; jl grava
    a.raw(bytes.fromhex("83E864EB03"))               # sub eax, 100 ; jmp grava
    a.raw(bytes.fromhex("83C014"))                   # ano: add eax, 20
    a.raw(bytes.fromhex("89442408"))                 # grava: mov [esp+8], eax
    a.jmp(SET_NUMBER)                                # fora
    return bytes(a.code)


def _int_stub(base: int, target: int) -> bytes:
    a = Asm(base)
    a.raw(bytes.fromhex("8344240414"))               # add dword [esp+4], 20
    a.jmp(target)
    return bytes(a.code)


def build(data: bytes):
    from .exe_patches import Swap

    swaps = list(section_swaps(data))
    for base, code in ((YEAR_STUB, _year_stub()), (INT_STUB, _int_stub(INT_STUB, TEXT_INT)),
                       (INT2_STUB, _int_stub(INT2_STUB, TEXT_FROM_INT))):
        swaps.append(Swap(sec_off(base), bytes(len(code)), code))
    for va, old, new in DATE_LOADS:
        swaps.append(Swap(off(va), bytes.fromhex(old), bytes.fromhex(new)))
    for calls, expect, stub in ((YEAR_CALLS, SET_NUMBER, YEAR_STUB), (INT_CALLS, TEXT_INT, INT_STUB),
                                (INT2_CALLS, TEXT_FROM_INT, INT2_STUB)):
        for va in calls:
            old = b"\xE8" + u32(expect - (va + 5))
            swaps.append(Swap(off(va), old, b"\xE8" + u32(stub - (va + 5))))
    return tuple(swaps)
