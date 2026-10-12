"""Patches conhecidos do fm.exe 6.0.2 (SHA-256 3C20470A…5B90).

Cada patch é uma lista de trocas (offset no arquivo, bytes esperados, bytes
novos). O script confere os bytes esperados antes de trocar e nunca altera o
fm.exe original.

Conversão: offset no arquivo = endereço virtual - 0x400000 (seção .text).
"""

from __future__ import annotations

from dataclasses import dataclass


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
    swaps: tuple[Swap, ...]


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
            "Mata-mata continua recebendo 32. Validado: grupos de 8, 4 se classificam.",
            (
                Swap(0x7BFDB7, bytes.fromhex("66c7008000"), bytes.fromhex("66c7004000")),  # total 128 -> 64
                Swap(0x7BFDF9, bytes.fromhex("c6460810"), bytes.fromhex("c6460808")),      # grupos 16 -> 8
                _zone(0x7BFECB, PROMOTION, 2, 4),                                           # avançam 2 -> 4
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


def apply(data: bytes, names: list[str]) -> bytes:
    out = bytearray(data)
    for name in names:
        if name not in PATCHES:
            raise KeyError(f"Patch desconhecido: {name}. Disponíveis: {', '.join(PATCHES)}")
        for swap in PATCHES[name].swaps:
            current = bytes(out[swap.offset:swap.offset + len(swap.old)])
            if current != swap.old:
                raise ValueError(
                    f"{name}: em 0x{swap.offset:08X} esperava {swap.old.hex(' ')}, achei {current.hex(' ')}"
                )
            out[swap.offset:swap.offset + len(swap.new)] = swap.new
    return bytes(out)
