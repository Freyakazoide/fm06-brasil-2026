"""Janelas de transferência do Brasil em 2026 (ficha C8b).

As regras do Brasil são montadas por 0x00BB32A0 (método 0 da vtable BRA_TRANSFER_RULES,
0x0113DBF8). A janela é gravada por 0x00ADED50, com 13 argumentos e `ret 0x34`:

    (dia da semana, dia, mês, ano) de abertura, (dia da semana, dia, mês, ano) de
    fechamento, tipo, divisão de, divisão até, 1, 1

com o mês começando em 0, o dia da semana 0 (não usado) e o ano de referência 2000; -1 nas
divisões vale para todas. Exemplos: Inglaterra 1/7–31/8 e 1/1–31/1, Espanha igual. O Brasil
de 2005 tem uma janela só, de 1/1 a 26/9 (push em 0x00BB32CD…0x00BB32EB).

2026 (CBF, janela internacional): 5/1 a 3/3 e 20/7 a 11/9. A 1ª janela troca os imediatos
no lugar; a 2ª precisa de outra chamada: os 13 bytes da chamada seguinte (0x00BB32F4,
`push -1 ; push 3 ; push 4 ; mov ecx, esi ; call 0x00ADC540`) viram `call` para um stub na
.fm26 que grava a 2ª janela e refaz essa chamada. A janela complementar de março (4 a 27/3,
só para quem jogou estadual) fica de fora: o jogo não tem essa restrição.
"""

from __future__ import annotations

from .exe_cave import SECTION_VA, Asm, off, sec_off, section_swaps

WINDOW = 0x00ADED50
RULE = 0x00ADC540
FIRST_START_DAY_AT = 0x00BB32E9      # push 1 (dia de abertura)
FIRST_END_MONTH_AT = 0x00BB32DC      # push 8 (setembro)
FIRST_END_DAY_AT = 0x00BB32DE        # push 26
NEXT_CALL_AT = 0x00BB32F4            # push -1 ; push 3 ; push 4 ; mov ecx, esi ; call RULE
NEXT_CALL = bytes.fromhex("6AFF6A036A048BCE") + b"\xE8"
SECOND_STUB = SECTION_VA + 0x6240

# (dia, mês) de abertura e de fechamento, mês de 1 a 12
WINDOWS_2026 = (((5, 1), (3, 3)), ((20, 7), (11, 9)))


def _window_args(start: tuple[int, int], end: tuple[int, int]) -> list[int]:
    """Na ordem dos push (o último argumento primeiro), como em 0x00BB32CD."""
    (start_day, start_month), (end_day, end_month) = start, end
    return [1, 1, -1, -1, 1, 2000, end_month - 1, end_day, 0, 2000, start_month - 1, start_day, 0]


def _second_stub(start: tuple[int, int], end: tuple[int, int]) -> bytes:
    a = Asm(SECOND_STUB)                             # esi = regras
    for value in _window_args(start, end):
        a.push(value)
    a.mov_ecx_esi().call(WINDOW)                     # 2ª janela
    a.push(-1).push(3).push(4).mov_ecx_esi().call(RULE)   # a chamada que estava no lugar
    a.raw(b"\xC3")
    return bytes(a.code)


def windows_swaps(data: bytes):
    from .exe_patches import Swap

    (first_start, first_end), second = WINDOWS_2026
    assert data[off(NEXT_CALL_AT):off(NEXT_CALL_AT) + 9] == NEXT_CALL
    site = bytes(Asm(NEXT_CALL_AT).call(SECOND_STUB).code) + bytes.fromhex("90" * 8)
    code = _second_stub(*second)
    return (*section_swaps(data),
            Swap(off(FIRST_START_DAY_AT), bytes.fromhex("6A01"), bytes([0x6A, first_start[0]])),
            Swap(off(FIRST_END_MONTH_AT), bytes.fromhex("6A08"), bytes([0x6A, first_end[1] - 1])),
            Swap(off(FIRST_END_DAY_AT), bytes.fromhex("6A1A"), bytes([0x6A, first_end[0]])),
            Swap(off(NEXT_CALL_AT), data[off(NEXT_CALL_AT):off(NEXT_CALL_AT) + 13], site),
            Swap(sec_off(SECOND_STUB), bytes(len(code)), code))


# Estrangeiros (ficha C8b). Por jogo: `bra_setup_fixture_rules` (0x00BBA3B0, registrada pelo
# nome em 0x00AEA970) grava a regra de convocatória código 4 = 3 por 0x00A58C60 (código,
# valor, -1, 0); os códigos 2, 3, 4 e 0x35 são "The match squad must have no more than N
# foreign players" (0x00A57C7E). 2026: 9 relacionados nas Séries A e B (vale para todas as
# competições do Brasil que usam essas regras). No elenco: a regra de transferência tipo 4 =
# 3 ("Clubes só podem ter 3 jogadores estrangeiros no elenco") é a chamada que o stub das
# janelas refaz; a CBF não limita o elenco, então ela sai (o stub vira `ret` depois da 2ª
# janela). Depende do janelas_2026.
MATCH_FOREIGN_AT = 0x00BBA3D0        # push 3
MATCH_FOREIGN_2026 = 9


def foreign_swaps(data: bytes):
    from .exe_patches import Swap

    (_, _), second = WINDOWS_2026
    stub = _second_stub(*second)
    redo = bytes(Asm(0).push(-1).push(3).push(4).mov_ecx_esi().code) + b"\xE8"
    at = stub.index(redo)
    assert stub[at + 13:] == b"\xC3"
    return (Swap(off(MATCH_FOREIGN_AT), bytes.fromhex("6A03"), bytes([0x6A, MATCH_FOREIGN_2026])),
            Swap(sec_off(SECOND_STUB + at), stub[at:at + 13], bytes.fromhex("90" * 13)))


# Substituições (ficha C8b). A partida guarda o máximo de trocas em [partida+0xF78], vindo de
# 0x008E89F0(índice), chamada só de 0x00952A95 com o índice de substituições da competição
# ([[partida+0x64]+0x44]). Tabela por índice (0 a 25): quase todos devolvem 3 pelo mesmo
# `mov al, 3` (0x008E8A08); o 9 (amistoso) devolve 7. O texto da tela de Regras sai de
# 0x00AD4FC0 com o mesmo índice (CLIENT_FIXTURE+0x121): "N suplentes convocados, máximo M
# utilizados", com M = 3 nos `push 3` de 0x00AD500C e 0x00AD513E. 2026: 5 trocas (IFAB, vale no
# mundo todo), então o 3 vira 5 em todos os índices. O banco (N, de 0x00AD5420) fica.
SUBS_USED_AT = 0x008E8A08            # mov al, 3
SUBS_TEXT_AT = (0x00AD500C, 0x00AD513E)   # push 3 (máximo utilizados)
SUBS_2026 = 5


def subs_swaps(data: bytes):
    from .exe_patches import Swap

    return (Swap(off(SUBS_USED_AT), bytes.fromhex("B003"), bytes([0xB0, SUBS_2026])),
            *(Swap(off(at), bytes.fromhex("6A03"), bytes([0x6A, SUBS_2026])) for at in SUBS_TEXT_AT))


# Banco de reservas. Os suplentes convocados vêm de 0x00AD5420(índice); os índices 0, 4, 9, 20 e
# 21 devolvem 7 pelo mesmo `mov al, 7` (0x00AD5441). O texto da tela usa `push 7` (parâmetro 1)
# em 0x00AD4FFC (índices 0 e 4), 0x00AD5021 (20), 0x00AD5039 (21) e 0x00AD5095 (9). 2026: até 12
# reservas no Brasileirão (CBF, regra da FIFA); os índices 8 e 18 já usam 12, então o jogo
# aceita esse número. Vale para todas as competições que usavam 7.
BENCH_AT = 0x00AD5441                # mov al, 7
BENCH_TEXT_AT = (0x00AD4FFC, 0x00AD5021, 0x00AD5039, 0x00AD5095)   # push 7 (convocados)
BENCH_2026 = 12


def bench_swaps(data: bytes):
    from .exe_patches import Swap

    return (Swap(off(BENCH_AT), bytes.fromhex("B007"), bytes([0xB0, BENCH_2026])),
            *(Swap(off(at), bytes.fromhex("6A07"), bytes([0x6A, BENCH_2026])) for at in BENCH_TEXT_AT))


# Banco de 12 em todas as competições (depois do banco_12_2026). Os outros casos de 0x00AD5420
# devolvem 3 (0x00AD5438), 4, 6, 8, 9, 11, 5 ou 9 (0x00AD5450, `lea eax, [eax*4+5]`) e 5 (fora da
# tabela, 0x00AD5463); todos viram 12. Fica o índice 19 (0 reservas, 0 trocas). No texto, os
# `push N` do parâmetro 1 que sobram viram `push 0xC`. As trocas do índice 21 (4, em
# 0x008E8A0B) viram 5, como as outras.
BENCH_ALL_AT = (0x00AD5438, 0x00AD543B, 0x00AD543E, 0x00AD5444, 0x00AD5447, 0x00AD544A,
                0x00AD5463)                                  # mov al, N
BENCH_ALL_LEA_AT = 0x00AD5450        # cmp byte ptr [esp+8], 0 ; sete al ; lea ... ; ret
BENCH_ALL_TEXT_AT = (0x00AD502D, 0x00AD5059, 0x00AD5062, 0x00AD506B, 0x00AD5074, 0x00AD507D,
                     0x00AD50BA, 0x00AD50C6, 0x00AD5110, 0x00AD5119, 0x00AD5155, 0x00AD5165)
SUBS_FOUR_AT = 0x008E8A0B            # mov al, 4


def bench_all_swaps(data: bytes):
    from .exe_patches import Swap

    swaps = []
    for at in BENCH_ALL_AT:
        old = data[off(at):off(at) + 3]
        assert old[0] == 0xB0 and old[2] == 0xC3, hex(at)
        swaps.append(Swap(off(at), old[:2], bytes([0xB0, BENCH_2026])))
    old = data[off(BENCH_ALL_LEA_AT):off(BENCH_ALL_LEA_AT) + 3]
    assert old == bytes.fromhex("807C24")
    swaps.append(Swap(off(BENCH_ALL_LEA_AT), old, bytes([0xB0, BENCH_2026, 0xC3])))
    for at in BENCH_ALL_TEXT_AT:
        old = data[off(at):off(at) + 2]
        assert old[0] == 0x6A, hex(at)
        swaps.append(Swap(off(at), old, bytes([0x6A, BENCH_2026])))
    swaps.append(Swap(off(SUBS_FOUR_AT), bytes.fromhex("B004"), bytes([0xB0, SUBS_2026])))
    return tuple(swaps)
