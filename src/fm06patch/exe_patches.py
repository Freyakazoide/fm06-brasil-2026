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

PATCHES = {
    p.name: p
    for p in (
        Patch(
            "serie_a_rebaixa_4",
            "Série A rebaixa 4 clubes para a Série B (original: 2). Método de fase em 0x00BBA400.",
            (_push_count(0x7BA4F3, 2, 4, SERIE_B),),
        ),
        Patch(
            "serie_b_sobe_4",
            "Série B sobe 4 clubes para a Série A (original: 2). Método de fase em 0x00BBA6A0.",
            (_push_count(0x7BA795, 2, 4, SERIE_A),),
        ),
        Patch(
            "serie_b_rebaixa_4",
            "Série B rebaixa 4 clubes para a Série C (original: 2). Método de fase em 0x00BBA6A0.",
            (_push_count(0x7BA7A8, 2, 4, SERIE_C),),
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
