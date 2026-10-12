"""Code cave: uma quarta divisão nacional no Brasil (nova Série C).

A Série C de 2005 (128 clubes, ID 107192) passa a ser o 4º nível (Série D) e
uma competição nova entra no 3º nível: uma cópia da classe da Série B (liga de
20 clubes) ligada ao registro "Taça de Prata" do banco (ID 319191, índice 376
na tabela de competições), que o jogo não usa.

O que o patch faz no fm.exe (endereços virtuais; arquivo = endereço - 0x400000):

- `.rdata` livre (0x012BA610): cópia da vtable principal da Série B
  (0x0113B5B4, 150 métodos, com o ponteiro de RTTI antes), com o método 71
  (montagem da fase) trocado pela cópia abaixo.
- `.text` livre (0x00E303D0):
  - cópia da montagem da fase da Série B (0x00BBA6A0): acesso para a Série B,
    rebaixamento para a antiga C, 4 sobem e 2 caem;
  - cópia do construtor da Série B (0x00BB2DF0) com o ID 319191, nível 2 e a
    vtable nova;
  - três desvios: sistema de ligas (`bra_get_settings`), criação das
    competições (`bra_setup_comps`) e mínimo de clubes por divisão
    (`bra_get_minimum_division_teams`).
- Antiga C: nível 2 -> 3 no construtor; acesso passa a ir para a nova C.
- Série B: rebaixamento passa a ir para a nova C.
- Cabeçalho: tamanho virtual de `.text` e `.rdata` cobre as áreas novas.

Os times entram na nova C pelo banco: índice 376 no registro do time
(`scripts/server_db_teams.py`).
"""

from __future__ import annotations

import struct

IMAGE_BASE = 0x400000

NEW_C_ID = 319191          # "Taça de Prata" no banco
NEW_C_INDEX = 376          # índice na tabela de competições do server_db
SERIE_A_ID = 0x19017
SERIE_B_ID = 0x1A2B7
OLD_C_ID = 0x1A2B8

# Código original copiado
B_CTOR = 0x00BB2DF0
B_CTOR_SIZE = 0x95
B_CTOR_CALLS = (0x26, 0x7E)
B_BUILDER = 0x00BBA6A0
B_BUILDER_SIZE = 0x25C
B_BUILDER_CALLS = (
    0x42, 0x53, 0x70, 0x8D, 0x101, 0x111, 0x12E, 0x13E, 0x152, 0x166, 0x17B,
    0x18F, 0x1A3, 0x1B0, 0x1BE, 0x1D0, 0x1E5, 0x1FA, 0x217, 0x22B,
)
B_VTABLE = 0x0113B5B4
VTABLE_SLOTS = 150
STAGE_SLOT = 71

# Funções chamadas pelos desvios
ALLOC = 0x00A3BB00          # operator new usado por bra_setup_comps
ADD_DIVISION = 0x00AD0050   # (id, nível, 0)
MIN_TEAMS = 0x00AA7BF0      # (id, 0, quantidade, -2, 0)

# Áreas livres (preenchidas com zero no original)
TEXT_FREE = (0x00E303C2, 0x00E31000)
RDATA_FREE = (0x012BA60B, 0x012BB000)
NEW_BUILDER = 0x00E303D0
NEW_CTOR = 0x00E30630
HOOKS = 0x00E306D0
NEW_COL = 0x012BA610
NEW_VTABLE = NEW_COL + 4

# Cabeçalhos de seção: campo VirtualSize
TEXT_VSIZE = (0x208, 0x00A2F3C2, 0x00A30000)
RDATA_VSIZE = (0x230, 0x0048960B, 0x0048A000)


def off(va: int) -> int:
    return va - IMAGE_BASE


def u32(value: int) -> bytes:
    return struct.pack("<I", value & 0xFFFFFFFF)


class Asm:
    """Montador mínimo para os desvios (endereço absoluto conhecido)."""

    def __init__(self, base: int):
        self.base = base
        self.code = bytearray()

    @property
    def here(self) -> int:
        return self.base + len(self.code)

    def raw(self, data: bytes) -> "Asm":
        self.code += data
        return self

    def push(self, value: int) -> "Asm":
        if -128 <= value <= 127:
            return self.raw(bytes([0x6A, value & 0xFF]))
        return self.raw(b"\x68" + u32(value))

    def call(self, target: int) -> "Asm":
        return self.raw(b"\xE8" + u32(target - (self.here + 5)))

    def jmp(self, target: int) -> "Asm":
        return self.raw(b"\xE9" + u32(target - (self.here + 5)))

    def mov_ecx_esi(self) -> "Asm":
        return self.raw(b"\x8B\xCE")


def _relocate(code: bytearray, source: int, dest: int, calls: tuple[int, ...]) -> None:
    for at in calls:
        if code[at] != 0xE8:
            raise ValueError(f"esperava call em 0x{source + at:08X}")
        target = source + at + 5 + struct.unpack_from("<i", code, at + 1)[0]
        struct.pack_into("<i", code, at + 1, target - (dest + at + 5))


def _replace(code: bytearray, at: int, old: bytes, new: bytes) -> None:
    if bytes(code[at:at + len(old)]) != old:
        raise ValueError(f"cópia: esperava {old.hex(' ')} em +0x{at:X}")
    code[at:at + len(new)] = new


def _new_builder(data: bytes) -> bytes:
    code = bytearray(data[off(B_BUILDER):off(B_BUILDER) + B_BUILDER_SIZE])
    _relocate(code, B_BUILDER, NEW_BUILDER, B_BUILDER_CALLS)
    _replace(code, 0xF7, b"\x68" + u32(SERIE_A_ID), b"\x68" + u32(SERIE_B_ID))  # acesso -> Série B
    _replace(code, 0xCA, b"\xC6\x46\x11\x02", b"\xC6\x46\x11\x04")             # 4 sobem
    # rebaixamento continua para a antiga C (0x1A2B8, em +0x10A); 2 caem (+0x14)
    return bytes(code)


def _new_ctor(data: bytes) -> bytes:
    code = bytearray(data[off(B_CTOR):off(B_CTOR) + B_CTOR_SIZE])
    _relocate(code, B_CTOR, NEW_CTOR, B_CTOR_CALLS)
    _replace(code, 0x17, b"\x6A\x01\x6A\x01\x8B\xF1\x68" + u32(SERIE_B_ID),
             b"\x6A\x02\x6A\x01\x8B\xF1\x68" + u32(NEW_C_ID))                    # nível 2, ID novo
    _replace(code, 0x35, b"\xC7\x06" + u32(B_VTABLE), b"\xC7\x06" + u32(NEW_VTABLE))
    return bytes(code)


def _new_vtable(data: bytes) -> bytes:
    raw = bytearray(data[off(B_VTABLE) - 4:off(B_VTABLE) + 4 * VTABLE_SLOTS])
    struct.pack_into("<I", raw, 4 + 4 * STAGE_SLOT, NEW_BUILDER)
    return bytes(raw)


def _hooks() -> tuple[bytes, dict[str, int]]:
    asm = Asm(HOOKS)
    entry = {}

    # bra_get_settings: no lugar da 3ª divisão, registra nova C (nível 2) e
    # antiga C (nível 3); finalizar(4).
    entry["settings"] = asm.here
    asm.push(0).push(2).push(NEW_C_ID).mov_ecx_esi().call(ADD_DIVISION)
    asm.push(0).push(3).push(OLD_C_ID).mov_ecx_esi().call(ADD_DIVISION)
    asm.push(4).jmp(0x00BB276E)

    # bra_setup_comps: cria a nova C logo depois da antiga C.
    entry["comps"] = asm.here
    asm.push(0x190).call(ALLOC).raw(b"\x83\xC4\x04")       # add esp, 4
    asm.raw(b"\x85\xC0\x74\x09\x8B\xC8")                   # test eax,eax ; je +9 ; mov ecx,eax
    asm.call(NEW_CTOR).raw(b"\xEB\x02\x31\xC0")            # jmp +2 ; xor eax,eax
    asm.raw(b"\x8B\x16\x50\x8B\xCE\xFF\x12")               # mov edx,[esi]; push eax; mov ecx,esi; call [edx]
    asm.push(0x19C).jmp(0x00BBA333)

    # bra_get_minimum_division_teams: nova C com 20.
    entry["minimum"] = asm.here
    asm.push(0).push(-2).push(20).push(0).push(SERIE_A_ID).mov_ecx_esi().call(MIN_TEAMS)
    asm.push(0).push(-2).push(20).push(0).push(NEW_C_ID).mov_ecx_esi().call(MIN_TEAMS)
    asm.jmp(0x00BB2859)
    return bytes(asm.code), entry


def _jmp(at: int, target: int, length: int) -> bytes:
    return b"\xE9" + u32(target - (at + 5)) + b"\x90" * (length - 5)


# O jogo conta os times de cada divisão (TEAM+0x54, em 0x00AA7B4D) e só deixa
# o país jogável se a contagem estiver entre o mínimo e o máximo registrados
# em bra_get_minimum_division_teams (0x00AA7BF0; máximo -2 = igual ao mínimo,
# -1 = sem máximo). A nova C exige exatamente 20.
PARTS = ("settings", "comps", "minimum", "moves")


def build_swaps(data: bytes, parts: tuple[str, ...] = PARTS):
    """Trocas do patch. `parts` permite testar cada desvio separadamente;
    o código novo nas áreas livres entra sempre."""
    from .exe_patches import Swap

    builder = _new_builder(data)
    ctor = _new_ctor(data)
    vtable = _new_vtable(data)
    hooks, entry = _hooks()
    if HOOKS + len(hooks) > TEXT_FREE[1] or NEW_VTABLE + 4 * VTABLE_SLOTS > RDATA_FREE[1]:
        raise ValueError("code cave não cabe na área livre")

    def fresh(va: int, blob: bytes) -> Swap:
        return Swap(off(va), bytes(len(blob)), blob)

    def header(field: tuple[int, int, int]) -> Swap:
        at, old, new = field
        return Swap(at, u32(old), u32(new))

    settings_hook = bytes.fromhex("6a006a0268b8a20100") + b"\x8b\xce\xe8" + u32(ADD_DIVISION - 0x00BB276C) + b"\x6a\x03"
    min_hook = bytes.fromhex("6a006afe6a146a006817900100") + b"\x8b\xce\xe8" + u32(MIN_TEAMS - 0x00BB2859)
    swaps = [
        header(TEXT_VSIZE),
        header(RDATA_VSIZE),
        fresh(NEW_BUILDER, builder),
        fresh(NEW_CTOR, ctor),
        fresh(HOOKS, hooks),
        fresh(NEW_COL, vtable),
    ]
    if "settings" in parts:
        swaps += [
            Swap(off(0x00BB275C), settings_hook, _jmp(0x00BB275C, entry["settings"], len(settings_hook))),
            Swap(off(0x00BB2ED7), b"\x6a\x02", b"\x6a\x03"),                              # antiga C: nível 3
        ]
    if "comps" in parts:
        swaps.append(Swap(off(0x00BBA32E), b"\x68\x9c\x01\x00\x00", _jmp(0x00BBA32E, entry["comps"], 5)))
    if "minimum" in parts:
        swaps.append(Swap(off(0x00BB2845), min_hook, _jmp(0x00BB2845, entry["minimum"], len(min_hook))))
    if "moves" in parts:
        swaps += [
            Swap(off(0x00BBFEFB), b"\x68" + u32(SERIE_B_ID), b"\x68" + u32(NEW_C_ID)),    # antiga C sobe p/ nova C
            Swap(off(0x00BBA7AA), b"\x68" + u32(OLD_C_ID), b"\x68" + u32(NEW_C_ID)),      # Série B cai p/ nova C
        ]
    return tuple(swaps)
