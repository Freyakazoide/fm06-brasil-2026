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

import csv
import struct
from pathlib import Path

from .copa_do_brasil import S0, S1
from .exe_cave import SECTION_VA, Asm, off, sec_off, section_swaps
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


# Cota da temporada (ficha C9b): no começo de cada temporada 0x00AC5260 paga a cada clube da
# tabela da competição o valor do método 0x128 (slot 74) da vtable principal, se for > 100,
# pelo método 0x98 das finanças ("Receitas Televisivas", conferido no jogo). Série A: 0x00BB2D90 (£1 mi, £2 mi
# ou £4 mi pela reputação do clube). Série B: 0x00B845A0, `mov eax, 250000 ; ret 4`, função
# usada também por outras duas vtables (0x0112AF2C, 0x011518F4): o slot da Série B passa
# para uma cópia na .fm26 com o valor de 2026.
SERIE_B_VTABLE = 0x0113B5B4
SERIE_B_QUOTA_OLD = 0x00B845A0
SERIE_B_QUOTA = SECTION_VA + 0x6100
SERIE_B_2026_BRL = 14_900_000      # aba Cotas_TV: cota igualitária da Série B


def serie_b_swaps(data: bytes):
    from .exe_patches import Swap

    assert data[off(SERIE_B_QUOTA_OLD):off(SERIE_B_QUOTA_OLD) + 8] == bytes.fromhex("b890d00300c20400")
    code = bytes.fromhex("B8") + struct.pack("<I", round(SERIE_B_2026_BRL / BRL_PER_GBP)) + bytes.fromhex("C20400")
    slot = SERIE_B_VTABLE + 0x128
    return (*section_swaps(data),
            Swap(sec_off(SERIE_B_QUOTA), bytes(len(code)), code),
            Swap(off(slot), struct.pack("<I", SERIE_B_QUOTA_OLD), struct.pack("<I", SERIE_B_QUOTA)))


# Cota da 1ª temporada (ficha C9b): na criação do jogo a Série B monta a temporada com o ano
# da nação ainda 2005 e 0x00AC5260 pula; mesmo que pagasse, cairia nas finanças básicas (o
# FINANCE_MANAGER e a troca para as completas vêm depois). Este patch paga no init das
# finanças do New Game, no fim do desvio do patrocinio_inicio (o `ret` vira jmp): clube da
# Série B (UID do jogo em CLUB+0x14, tabela abaixo) recebe a cota pelo método 0x98 ("Receitas
# Televisivas"). O init roda duas vezes por clube: só paga com FINANCE+0x70 (mês do 0x98)
# ainda 0.
IDENTITIES = Path(__file__).resolve().parents[2] / "data" / "brasil" / "clubes" / "identidade_fm06.csv"
FIRST_QUOTA = SECTION_VA + 0x6110
FIRST_QUOTA_TABLE = SECTION_VA + 0x6160


def serie_b_uids(path: Path = IDENTITIES) -> list[int]:
    with path.open(encoding="utf-8-sig") as handle:
        return [int(row["uid_jogo"]) for row in csv.DictReader(handle)
                if row["onde"].split(",")[0].strip() == "Série B"]


def _first_quota_stub(value: int) -> bytes:
    a = Asm(FIRST_QUOTA)                             # esi = finanças
    a.raw(bytes.fromhex("8B4608"))                   # mov eax, [esi+8] (clube)
    a.raw(bytes.fromhex("85C0742C"))                 # test eax, eax ; je fim
    a.raw(bytes.fromhex("837E7000"))                 # cmp dword [esi+0x70], 0
    a.raw(bytes.fromhex("7526"))                     # jne fim (já pago)
    a.raw(bytes.fromhex("8B4014"))                   # mov eax, [eax+0x14] (UID)
    a.raw(bytes.fromhex("BA") + struct.pack("<I", FIRST_QUOTA_TABLE))   # mov edx, tabela
    a.raw(bytes.fromhex("8B0A"))                     # laço: mov ecx, [edx]
    a.raw(bytes.fromhex("85C97418"))                 # test ecx, ecx ; je fim
    a.raw(bytes.fromhex("39C17405"))                 # cmp ecx, eax ; je paga
    a.raw(bytes.fromhex("83C204"))                   # add edx, 4
    a.raw(bytes.fromhex("EBF1"))                     # jmp laço
    a.push(value)                                    # paga: push valor
    a.mov_ecx_esi()
    a.raw(bytes.fromhex("8B06"))                     # mov eax, [esi]
    a.raw(bytes.fromhex("FF9098000000"))             # call [eax+0x98]
    a.raw(bytes.fromhex("C3"))                       # fim: ret
    return bytes(a.code)


def first_quota_swaps(data: bytes):
    from .exe_patches import Swap
    from .patrocinio import PAY_STUB, _pay_stub

    uids = serie_b_uids()
    assert len(uids) == 20, uids
    sponsor = _pay_stub()
    ret_at = PAY_STUB + len(sponsor) - 1
    assert sponsor[-1] == 0xC3
    jmp = Asm(ret_at).jmp(FIRST_QUOTA).code
    code = _first_quota_stub(round(SERIE_B_2026_BRL / BRL_PER_GBP))
    assert FIRST_QUOTA + len(code) <= FIRST_QUOTA_TABLE
    table = b"".join(struct.pack("<I", u) for u in uids) + bytes(4)
    return (Swap(sec_off(ret_at), b"\xC3" + bytes(4), bytes(jmp)),
            Swap(sec_off(FIRST_QUOTA), bytes(len(code)), code),
            Swap(sec_off(FIRST_QUOTA_TABLE), bytes(len(table)), table))


# Libertadores e Sul-Americana (ficha C9b): as montagens 0x00C07980 (Libertadores) e
# 0x00C07380 (Sul-Americana) gravam o prêmio de cada rodada com 0x00B3BA80, por `push imm32`,
# e a entrada nos grupos da Libertadores é paga por 0x00C05430 -> 0x00AC5490 (£300 mil a cada
# clube). Os patches do mod não mexem nesses push: troca no lugar. A preliminar da
# Libertadores (`push ebx` ×3) e os grupos da Sul-Americana (não existem no mod) ficam fora.
# O +0x40/+0x44 da rodada dos grupos (£60 mil/£120 mil) fica como está: no jogo uma vitória
# nos grupos não pagou nada (prêmio por jogo é outro campo, abaixo).
BRL_PER_USD = 5.40

# (endereço do push, £ original, US$ de 2026, linha da planilha)
CONMEBOL_2026 = (
    (0x00C05705, 300_000, 1_000_000, "Libertadores: fase de grupos — participação"),
    (0x00C07F1A, 375_000, 1_250_000, "Libertadores: oitavas de final"),
    (0x00C07FCA, 425_000, 1_700_000, "Libertadores: quartas de final"),
    (0x00C08071, 675_000, 2_300_000, "Libertadores: semifinal"),
    (0x00C080E2, 1_100_000, 7_000_000, "Libertadores: vice-campeão"),
    (0x00C080E7, 1_700_000, 25_000_000, "Libertadores: campeão"),
    (0x00C0747D, 31_000, 250_000, "Sul-Americana: 1ª fase (perdedor)"),
    (0x00C0766E, 31_000, 500_000, "Sul-Americana: playoff (2ª fase)"),
    (0x00C076CE, 50_000, 600_000, "Sul-Americana: oitavas de final"),
    (0x00C07806, 100_000, 700_000, "Sul-Americana: quartas de final"),
    (0x00C0789F, 200_000, 800_000, "Sul-Americana: semifinal"),
    (0x00C07908, 300_000, 2_500_000, "Sul-Americana: vice-campeão"),
    (0x00C0790D, 460_000, 10_000_000, "Sul-Americana: campeão"),
)


def usd_to_gbp(usd: int) -> int:
    return round(usd * BRL_PER_USD / BRL_PER_GBP)


def conmebol_swaps(data: bytes):
    from .exe_patches import Swap

    return tuple(Swap(off(va), _push(old), _push(usd_to_gbp(usd)))
                 for va, old, usd, _ in CONMEBOL_2026)


# Prêmio por vitória na fase de liga (ficha C9b): depois de cada jogo, 0x00B0DE70 paga pelas
# regras da fase ([fase+0x24], construtor 0x00B194A0): +0x30 ao vencedor, +0x34 aos dois no
# empate, +0x38 no outro caso (`0x00B0B400`, "Prêmios em Dinheiro"). Os três começam em 0, a
# montagem da Libertadores não os grava e a leitura do save (0x00B10D10) zera de novo. Então
# o desvio é na leitura do +0x30 (0x00B0E160): se a competição da fase ([fase+0x18]) tem a
# vtable da Libertadores (0x01154CF4, gravada só no construtor 0x00C06322), vale o de 2026.
GROUP_WIN_AT = 0x00B0E160
GROUP_WIN_STUB = SECTION_VA + 0x6200
LIBERTADORES_VTABLE = 0x01154CF4
LIBERTADORES_GROUP_WIN_USD = 340_000     # "Fase de grupos — por vitória"


def _group_win_stub(value: int) -> bytes:
    a = Asm(GROUP_WIN_STUB)                          # ebp = fase
    a.raw(bytes.fromhex("8B4524"))                   # mov eax, [ebp+0x24] (regras)
    a.raw(bytes.fromhex("8B4830"))                   # mov ecx, [eax+0x30] (por vitória)
    a.raw(bytes.fromhex("52"))                       # push edx
    a.raw(bytes.fromhex("8B5518"))                   # mov edx, [ebp+0x18] (competição)
    a.raw(bytes.fromhex("85D2740D"))                 # test edx, edx ; je fim
    a.raw(bytes.fromhex("813A") + struct.pack("<I", LIBERTADORES_VTABLE))   # cmp [edx], vtable
    a.raw(bytes.fromhex("7505"))                     # jne fim
    a.raw(bytes.fromhex("B9") + struct.pack("<I", value))   # mov ecx, valor
    a.raw(bytes.fromhex("5A"))                       # fim: pop edx
    a.raw(bytes.fromhex("C3"))                       # ret
    return bytes(a.code)


def group_win_swaps(data: bytes):
    from .exe_patches import Swap

    code = _group_win_stub(usd_to_gbp(LIBERTADORES_GROUP_WIN_USD))
    site = bytes(Asm(GROUP_WIN_AT).call(GROUP_WIN_STUB).code) + bytes.fromhex("90")
    return (*section_swaps(data),
            Swap(off(GROUP_WIN_AT), bytes.fromhex("8B45248B4830"), site),
            Swap(sec_off(GROUP_WIN_STUB), bytes(len(code)), code))
