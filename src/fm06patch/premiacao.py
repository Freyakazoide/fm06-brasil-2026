"""Premiação da Copa do Brasil de 2026 (ficha C9b).

A montagem da Copa (0x00BBAD30) grava o prêmio de cada rodada com 0x00B3BA80(+0x40, +0x44,
+0x48), sempre por `push imm32`. Depois de cada confronto, 0x00B485D0 paga +0x48 aos dois
clubes e +0x40/+0x44 a um e ao outro (vencedor e perdedor, hipótese) pelas finanças do clube
("Prêmios em Dinheiro"). O patch copa_do_brasil_2026 copia a montagem para a .fm26 em duas
fases (S0: 3ª e 4ª fases; S1: 5ª fase à final); este patch troca os imediatos nas cópias.

Valores de data/modelos/premiacao_2026.xlsx (CBF). O jogo tem um valor por rodada: da 3ª à
4ª fase vale o do Grupo II (a fase 1 do mod junta Série B, C, D e estaduais).
"""

from __future__ import annotations

import struct

from .copa_do_brasil import S0, S1
from .exe_cave import sec_off
from .financas import BRL_PER_GBP

# Posição do `push imm32` dentro da montagem copiada (a partir de 0x00BBAD30)
R1_SHARE_AT = 0x108      # 0x00BBAE38, 1ª rodada: +0x48 (£8.000)
R2_SHARE_AT = 0x1A7      # 0x00BBAED7, 2ª rodada: +0x48 (£8.000)
R3_SHARE_AT = 0x204      # 0x00BBAF34, 3ª rodada: +0x48 (£26.000)
QF_SHARE_AT = 0x27E      # 0x00BBAFAE, quartas: +0x48 (£33.000)
SF_SHARE_AT = 0x2E7      # 0x00BBB017, semifinal: +0x48 (£44.000)
F_LOSER_AT = 0x34C       # 0x00BBB07C, final: +0x44 (£100.000)
F_WINNER_AT = 0x351      # 0x00BBB081, final: +0x40 (£200.000)

# (cópia, posição, £ original, R$ de 2026, linha da planilha)
COPA_2026 = (
    (S0, R1_SHARE_AT, 8_000, 1_530_000, "3ª fase — Grupo II"),
    (S0, R2_SHARE_AT, 8_000, 1_680_000, "4ª fase — Grupo II"),
    (S1, R1_SHARE_AT, 8_000, 2_000_000, "5ª fase"),
    (S1, R3_SHARE_AT, 26_000, 3_000_000, "Oitavas de final"),
    (S1, QF_SHARE_AT, 33_000, 4_000_000, "Quartas de final"),
    (S1, SF_SHARE_AT, 44_000, 9_000_000, "Semifinal"),
    (S1, F_LOSER_AT, 100_000, 34_000_000, "Vice-campeão"),
    (S1, F_WINNER_AT, 200_000, 78_000_000, "Campeão"),
)


def _push(value: int) -> bytes:
    return b"\x68" + struct.pack("<I", value)


def copa_swaps(data: bytes):
    from .exe_patches import Swap

    return tuple(Swap(sec_off(copy + at), _push(old), _push(round(brl / BRL_PER_GBP)))
                 for copy, at, old, brl, _ in COPA_2026)
