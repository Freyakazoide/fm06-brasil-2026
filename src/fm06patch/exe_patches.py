"""Patches conhecidos do fm.exe 6.0.2 (SHA-256 3C20470A…5B90).

Cada patch é uma lista de trocas (offset no arquivo, bytes esperados, bytes
novos). O script confere os bytes esperados antes de trocar e nunca altera o
fm.exe original.

Conversão: offset no arquivo = endereço virtual - 0x400000 (seção .text).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


EXE_SHA256 = "3C20470AE0C730D03EB548BC9A80B56E06AB653BBCA89C95F1BD38481FAE5B90"


@dataclass(frozen=True)
class Swap:
    offset: int
    old: bytes
    new: bytes


@dataclass(frozen=True)
class Patch:
    name: str
    description: str
    swaps: tuple[Swap, ...] = ()
    # Patches com código novo: as trocas dependem dos bytes do original.
    build: Optional[Callable[[bytes], tuple[Swap, ...]]] = None

    def swaps_for(self, data: bytes) -> tuple[Swap, ...]:
        return self.build(data) if self.build else self.swaps


def _push_count(offset: int, old: int, new: int, target: bytes) -> Swap:
    """`push imm8` com a quantidade, seguido de `push <id da competição>`."""
    return Swap(offset, bytes([0x6A, old]) + b"\x68" + target, bytes([0x6A, new]) + b"\x68" + target)


SERIE_A = (0x19017).to_bytes(4, "little")
SERIE_B = (0x1A2B7).to_bytes(4, "little")
SERIE_C = (0x1A2B8).to_bytes(4, "little")

def _zone(offset: int, field: int, old: int, new: int) -> Swap:
    """`mov byte ptr [esi+field], imm8` (C6 46 field imm8) na montagem da fase."""
    return Swap(offset, bytes([0xC6, 0x46, field, old]), bytes([0xC6, 0x46, field, new]))


def _imm8(offset: int, opcode: bytes, old: int, new: int) -> Swap:
    """Instrução cujo último byte é um imediato de 8 bits (ex.: `push imm8` = 6A xx)."""
    return Swap(offset, opcode + bytes([old]), opcode + bytes([new]))


# Campos da fase lidos por 0x00B16FE0 para pintar as zonas da tabela e
# decidir quem sobe e quem desce no fim da temporada.
PROMOTION = 0x11
RELEGATION = 0x14

PATCHES = {
    p.name: p
    for p in (
        Patch(
            "serie_a_rebaixa_4",
            "Série A: zona de rebaixamento com 4 clubes (original: 2). Fase em 0x00BBA400, campo +0x14.",
            (_zone(0x7BA4D3, RELEGATION, 2, 4),),
        ),
        Patch(
            "serie_b_sobe_4",
            "Série B: zona de acesso com 4 clubes (original: 2). Fase em 0x00BBA6A0, campo +0x11.",
            (_zone(0x7BA76A, PROMOTION, 2, 4),),
        ),
        Patch(
            "serie_b_rebaixa_4",
            "Série B: zona de rebaixamento com 4 clubes (original: 2). Fase em 0x00BBA6A0, campo +0x14.",
            (_zone(0x7BA774, RELEGATION, 2, 4),),
        ),
        Patch(
            "serie_a_datas_2026",
            "Série A de 28/1 a 2/12 (original: 30/4 a 10/12). Início validado; fim nos dois pares de datas da fase.",
            (
                _imm8(0x7BA573, b"\x6A", 3, 0),     # mês de início: abril -> janeiro
                _imm8(0x7BA575, b"\x6A", 30, 28),   # dia de início
                _imm8(0x7BA54C, b"\x6A", 10, 2),    # dia de fim, 1º par (é o que a tela mostra)
                _imm8(0x7BA589, b"\x6A", 10, 2),    # dia de fim, 2º par
            ),
        ),
        Patch(
            "serie_c_64_clubes",
            "Série C com 64 clubes: 8 grupos de 8 e avançam 4 por grupo (original: 128, 16 grupos, 2 avançam). "
            "Mata-mata continua recebendo 32. Validado: grupos de 8, 4 se classificam. "
            "Exige pelo menos 64 times na Série C, sem máximo (original: exatamente 128).",
            (
                Swap(0x7BFDB7, bytes.fromhex("66c7008000"), bytes.fromhex("66c7004000")),  # total 128 -> 64
                Swap(0x7BFDF9, bytes.fromhex("c6460810"), bytes.fromhex("c6460808")),      # grupos 16 -> 8
                _zone(0x7BFECB, PROMOTION, 2, 4),                                           # avançam 2 -> 4
                # clubes exigidos para o Brasil ser jogável (bra_get_minimum_division_teams):
                # original mínimo 128 e máximo igual (-2); agora mínimo 64 e sem máximo (-1)
                Swap(0x7B286F, bytes.fromhex("6afe6880000000"), bytes.fromhex("6aff6840000000")),
            ),
        ),
        Patch(
            "serie_c_nova",
            "4ª divisão: nova Série C (liga de 20, cópia da B, registro Taça de Prata 319191, índice 376) "
            "entre a B e a antiga C, que vira o 4º nível. B cai para a nova C; antiga C sobe para a nova C. "
            "Times entram pela ferramenta server_db_teams (índice 376).",
            build=lambda data: _cave_swaps(data),
        ),
        Patch(
            "exp_cave_settings",
            "TESTE: só o sistema de ligas com 4 níveis (nova C no nível 2, antiga C no 3).",
            build=lambda data: _cave_swaps(data, ("settings",)),
        ),
        Patch(
            "exp_cave_comps",
            "TESTE: só a criação da competição nova em bra_setup_comps.",
            build=lambda data: _cave_swaps(data, ("comps",)),
        ),
        Patch(
            "exp_cave_minimo",
            "TESTE: só o mínimo de 20 clubes da nova C em bra_get_minimum_division_teams.",
            build=lambda data: _cave_swaps(data, ("minimum",)),
        ),
        Patch(
            "serie_b_datas_2026",
            "Série B de 21/3 a 28/11 (original: 29/4 a 2/12). Fase em 0x00BBA6A0.",
            (
                _imm8(0x7BA825, b"\x6A", 3, 2),       # mês de início: abril -> março
                _imm8(0x7BA827, b"\x6A", 0x1D, 21),   # dia de início
                _imm8(0x7BA7FC, b"\x6A", 0x0B, 10),   # mês de fim, 1º par: dezembro -> novembro
                _imm8(0x7BA7FE, b"\x6A", 2, 28),      # dia de fim, 1º par
                _imm8(0x7BA839, b"\x6A", 0x0B, 10),   # mês de fim, 2º par
                _imm8(0x7BA83B, b"\x6A", 2, 28),      # dia de fim, 2º par
            ),
        ),
        Patch(
            "serie_d_96",
            "Série D (antiga C, 0x00BBFD00) com 96 clubes: 16 grupos de 6, avançam 2 por grupo para o "
            "mata-mata de 32; o quadrangular final dá 4 acessos (original: 2). Datas 5/4 a 13/9. "
            "Exige pelo menos 96 times, sem máximo. Não combina com serie_c_64_clubes.",
            (
                Swap(0x7BFDB7, bytes.fromhex("66c7008000"), bytes.fromhex("66c7006000")),  # total 128 -> 96
                Swap(0x7BFE9D, bytes.fromhex("c6460b08"), bytes.fromhex("c6460b06")),      # 8 -> 6 por grupo
                _zone(0x7C0573, PROMOTION, 2, 4),                                           # quadrangular: 4 sobem
                Swap(0x7B286F, bytes.fromhex("6afe6880000000"), bytes.fromhex("6aff6860000000")),
                # datas (push mês, push dia; mês começa em 0)
                _imm8(0x7BFF53, b"\x6A", 5, 3),       # grupos, início: 25/6 -> 5/4
                _imm8(0x7BFF5C, b"\x6A", 0x19, 5),
                _imm8(0x7BFF90, b"\x6A", 8, 5),       # grupos, fim: 20/9 -> 28/6
                _imm8(0x7BFF92, b"\x6A", 0x14, 28),
                _imm8(0x7C01AE, b"\x6A", 8, 6),       # mata-mata: 21/9 -> 5/7
                _imm8(0x7C01B0, b"\x6A", 0x15, 5),
                _imm8(0x7C01C8, b"\x6A", 8, 6),       # 1ª rodada: 24/9 -> 8/7
                _imm8(0x7C01CA, b"\x6A", 0x18, 8),
                _imm8(0x7C027A, b"\x6A", 9, 6),       # 2ª rodada: 4/10 -> 19/7
                _imm8(0x7C027C, b"\x6A", 4, 19),
                _imm8(0x7C03A1, b"\x6A", 9, 6),       # 3ª rodada: 15/10 -> 30/7
                _imm8(0x7C03A3, b"\x6A", 0x0F, 30),
                _imm8(0x7C05BA, b"\x6A", 9, 7),       # quadrangular, início: 25/10 -> 9/8
                _imm8(0x7C05BC, b"\x6A", 0x19, 9),
                _imm8(0x7C05DF, b"\x6A", 0x0A, 8),    # quadrangular, fim: 26/11 -> 13/9
                _imm8(0x7C05E1, b"\x6A", 0x1A, 13),
            ),
        ),
        Patch(
            "exp_regra_rebaixa_a",
            "EXPERIMENTAL, sem efeito visível: 2º argumento da regra de movimento Série A -> B.",
            (_push_count(0x7BA4F3, 2, 4, SERIE_B),),
        ),
        Patch(
            "exp_regra_sobe_b",
            "EXPERIMENTAL, sem efeito visível: 2º argumento da regra de movimento Série B -> A.",
            (_push_count(0x7BA795, 2, 4, SERIE_A),),
        ),
    )
}


def _cave_swaps(data: bytes, parts: tuple[str, ...] | None = None) -> tuple[Swap, ...]:
    from .exe_cave import PARTS, build_swaps

    return build_swaps(data, parts or PARTS)


def apply(data: bytes, names: list[str]) -> bytes:
    out = bytearray(data)
    for name in names:
        if name not in PATCHES:
            raise KeyError(f"Patch desconhecido: {name}. Disponíveis: {', '.join(PATCHES)}")
        for swap in PATCHES[name].swaps_for(data):
            current = bytes(out[swap.offset:swap.offset + len(swap.old)])
            if current != swap.old:
                raise ValueError(
                    f"{name}: em 0x{swap.offset:08X} esperava {swap.old.hex(' ')}, achei {current.hex(' ')}"
                )
            out[swap.offset:swap.offset + len(swap.new)] = swap.new
    return bytes(out)
