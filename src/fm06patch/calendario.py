"""Calendário da Série A com pausa da Copa do Mundo só nos anos de Copa.

A montagem da fase da Série A (0x00BBA400) registra duas janelas de datas
(0x00BBA531..0x00BBA596):

- janela final: início, fim e quantas rodadas ficam nela (word em +0x20 do
  modelo de datas, 26 no original): é o returno;
- janela da temporada: as demais rodadas (o turno) ficam entre o início e o
  fim dela.

O desvio troca esse trecho por duas cópias, uma com as datas de ano de Copa e
outra com as dos outros anos, e escolhe pelo ano da temporada (competição
+0x9C, lida pelo modelo de datas como em 0x00B08360). O FM06 tem Copa do
Mundo em 2006, 2010…, os mesmos anos módulo 4 de 2026, 2030…

Validado no jogo (teste exp_a_copa_2): turno até 28/5, nada durante a Copa,
returno a partir de 23/7.
"""

from __future__ import annotations

import struct

from .exe_cave import SECTION_VA, Asm, _relocate, _replace, off, sec_off, section_swaps, u32

REGION = 0x00BBA531                  # push 0x7D0 da 1ª data da janela final
REGION_END = 0x00BBA596              # depois da última data da janela da temporada
REGION_CALLS = (0x0F, 0x23, 0x38, 0x4C, 0x60)
SERIE_A_COPA = SECTION_VA + 0x1000   # desvio + as duas cópias

# Posição do push imm8 (6A xx) de cada data dentro do trecho copiado: (dia, mês)
FIELDS = {
    "final_inicio": (0x07, 0x05),
    "final_fim": (0x1B, 0x19),
    "temporada_inicio": (0x44, 0x42),
    "temporada_fim": (0x58, 0x56),
}
ROUNDS_AT = 0x36                     # word das rodadas da janela final
ORIGINAL = {"final_inicio": (6, 7), "final_fim": (10, 11), "temporada_inicio": (30, 3),
            "temporada_fim": (10, 11)}
ROUNDS_ORIGINAL = 26

# (dia, mês com janeiro = 0)
ANO_DE_COPA = {
    "final_inicio": (22, 6),         # returno a partir de 22/7
    "final_fim": (2, 11),            # 2/12
    "temporada_inicio": (28, 0),     # 28/1
    "temporada_fim": (31, 4),        # turno até 31/5
}
ANO_SEM_COPA = {
    "final_inicio": (21, 5),         # returno a partir de 21/6
    "final_fim": (2, 11),
    "temporada_inicio": (28, 0),
    "temporada_fim": (14, 5),        # turno até 14/6
}
RETURNO = 19                         # rodadas do returno (38 / 2)


def _region_copy(data: bytes, dest: int, dates: dict[str, tuple[int, int]]) -> bytes:
    code = bytearray(data[off(REGION):off(REGION_END)])
    _relocate(code, REGION, dest, REGION_CALLS)
    for name, (day_at, month_at) in FIELDS.items():
        old_day, old_month = ORIGINAL[name]
        day, month = dates[name]
        _replace(code, day_at, bytes([0x6A, old_day]), bytes([0x6A, day]))
        _replace(code, month_at, bytes([0x6A, old_month]), bytes([0x6A, month]))
    _replace(code, ROUNDS_AT, struct.pack("<H", ROUNDS_ORIGINAL), struct.pack("<H", RETURNO))
    return bytes(code)


def build(data: bytes):
    from .exe_patches import Swap

    a = Asm(SERIE_A_COPA)
    a.raw(b"\x8B\x44\x24\x3C")                 # mov eax, [esp+0x3C] (modelo de datas)
    a.raw(b"\x8B\x40\x14")                     # mov eax, [eax+0x14] (competição)
    a.raw(b"\x0F\xB7\x80\x9C\x00\x00\x00")     # movzx eax, word [eax+0x9C] (ano)
    a.raw(b"\x83\xE0\x03\x83\xF8\x02")         # and eax, 3 ; cmp eax, 2
    jne = len(a.code)
    a.raw(b"\x0F\x85" + u32(0))                # jne sem Copa
    copa = _region_copy(data, a.here, ANO_DE_COPA)
    a.raw(copa).jmp(REGION_END)
    sem_copa_at = a.here
    a.raw(_region_copy(data, sem_copa_at, ANO_SEM_COPA)).jmp(REGION_END)
    code = bytearray(a.code)
    struct.pack_into("<i", code, jne + 2, (sem_copa_at - SERIE_A_COPA) - (jne + 6))

    hook = b"\xE9" + u32(SERIE_A_COPA - (REGION + 5))
    return tuple(section_swaps(data)) + (
        Swap(sec_off(SERIE_A_COPA), bytes(len(code)), bytes(code)),
        Swap(off(REGION), data[off(REGION):off(REGION) + 5], hook),
    )
