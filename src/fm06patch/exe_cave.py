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
    rebaixamento para a antiga C, 4 sobem e 2 caem, turno único, 5/4 a 25/10;
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
    _replace(code, 0xAB, b"\xC6\x46\x0A\x02", b"\xC6\x46\x0A\x01")             # turno único
    # Datas 2026: 5/4 a 25/10 (push mês, push dia; mês começa em 0).
    for at, old, new in (
        (0x148, 7, 6),        # 1º par, início: agosto -> julho (dia 5)
        (0x15C, 0x0B, 9),     # 1º par, fim: mês dezembro -> outubro
        (0x15E, 2, 25),       #          dia 2 -> 25
        (0x185, 3, 3),        # 2º par, início: abril
        (0x187, 0x1D, 5),     #          dia 29 -> 5
        (0x199, 0x0B, 9),     # 2º par, fim: outubro
        (0x19B, 2, 25),       #          dia 25
    ):
        _replace(code, at, bytes([0x6A, old]), bytes([0x6A, new]))
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

    # bra_setup_comps: cria a nova C logo antes da antiga C (a ordem de criação
    # é a ordem em que as divisões aparecem nas listas do jogo).
    entry["comps"] = asm.here
    asm.push(0x190).call(ALLOC).raw(b"\x83\xC4\x04")       # add esp, 4
    asm.raw(b"\x85\xC0\x74\x09\x8B\xC8")                   # test eax,eax ; je +9 ; mov ecx,eax
    asm.call(NEW_CTOR).raw(b"\xEB\x02\x31\xC0")            # jmp +2 ; xor eax,eax
    asm.raw(b"\x8B\x16\x50\x8B\xCE\xFF\x12")               # mov edx,[esi]; push eax; mov ecx,esi; call [edx]
    asm.push(0x190).jmp(0x00BBA310)

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
        return Swap(at, u32(old), u32(new), shared=True)

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
        swaps.append(Swap(off(0x00BBA30B), b"\x68\x90\x01\x00\x00", _jmp(0x00BBA30B, entry["comps"], 5)))
    if "minimum" in parts:
        swaps.append(Swap(off(0x00BB2845), min_hook, _jmp(0x00BB2845, entry["minimum"], len(min_hook))))
    if "moves" in parts:
        swaps += [
            Swap(off(0x00BBFEFB), b"\x68" + u32(SERIE_B_ID), b"\x68" + u32(NEW_C_ID)),    # antiga C sobe p/ nova C
            Swap(off(0x00BBA7AA), b"\x68" + u32(OLD_C_ID), b"\x68" + u32(NEW_C_ID)),      # Série B cai p/ nova C
        ]
    return tuple(swaps)


# ---------------------------------------------------------------------------
# Playoffs da Série B (3º×6º e 4º×5º, ida e volta, empate: melhor campanha)
#
# - Fase 1 (liga, 0x00BBA6A0): zona de playoff do 3º ao 6º (+0x12 = 4) ligada
#   à fase seguinte (ação 0x00B0FF00 com o código 0x15), como na Championship
#   inglesa (0x00C15480). Os 2 primeiros sobem direto (+0x11 = 2).
# - Fase 2: cópia da montagem da Série B italiana (0x00C0FAC0), cujo playoff
#   já usa o desempate pela posição na liga (bit 0x100 no 2º jogo). Na cópia:
#   sem final (os 2 vencedores das semifinais sobem), datas 21/11 e 28/11.
# - Construtor da Série B: 2 fases (0x00BB2E1D); método 71 da vtable da Série
#   B aponta para um despachante (fase 1 -> cópia italiana, senão original).
# ---------------------------------------------------------------------------

ITA_BUILDER = 0x00C0FAC0
ITA_BUILDER_SIZE = 0x7EC
ITA_BUILDER_CALLS = (
    0x48, 0x61, 0x7E, 0xEE, 0xFD, 0x130, 0x15E, 0x17A, 0x18E, 0x1A2, 0x1B6, 0x1C2,
    0x1EC, 0x203, 0x213, 0x22E, 0x23D, 0x25E, 0x279, 0x294, 0x2AF, 0x2CA, 0x2E4,
    0x2FF, 0x310, 0x325, 0x33A, 0x34F, 0x364, 0x37C, 0x399, 0x3C4, 0x3E1, 0x3FB,
    0x40F, 0x467, 0x47F, 0x499, 0x4DC, 0x4EC, 0x4F5, 0x500, 0x518, 0x532, 0x574,
    0x584, 0x58D, 0x5A3, 0x5BA, 0x5D1, 0x5F8, 0x623, 0x640, 0x66B, 0x6D6, 0x6F1,
    0x70E, 0x74F, 0x763, 0x76F, 0x785, 0x79C, 0x7C6,
)
PLAYOFF_COPY = 0x00E30760
PLAYOFF_STUBS = 0x00E30F50
STAGE_ACTION = 0x00B0FF00
FATE_VTABLES = (0x01117604, 0x011175F8)
PLAYOFF_STAGE_CODE = 0x15


def _playoff_copy(data: bytes, date_stub: int) -> bytes:
    code = bytearray(data[off(ITA_BUILDER):off(ITA_BUILDER) + ITA_BUILDER_SIZE])
    _relocate(code, ITA_BUILDER, PLAYOFF_COPY, ITA_BUILDER_CALLS)

    def at(va: int) -> int:
        return va - ITA_BUILDER

    # Semifinal: data do sorteio (push 2; push ano; push mês; push ebp(dia); push hora)
    # vai para um trecho próprio, porque o dia vinha de um registrador.
    old = bytes.fromhex("6a0268d10700006a055568b0040000")
    jump = b"\xE9" + u32(date_stub - (PLAYOFF_COPY + at(0x00C0FF2C) + 5))
    _replace(code, at(0x00C0FF2C), old, jump + b"\x90" * (len(old) - 5))
    # 1º jogo: 21/11 (push ano; push mês; push dia)
    _replace(code, at(0x00C0FF47), bytes.fromhex("68d10700006a056a0a"), bytes.fromhex("68d00700006a0a6a15"))
    # Sem final: salta a montagem da 2ª rodada (0x14) até as ações de destino.
    target = PLAYOFF_COPY + at(0x00C10052)
    _replace(code, at(0x00C0FFBA), bytes.fromhex("6a148d4c2454"),
             b"\xE9" + u32(target - (PLAYOFF_COPY + at(0x00C0FFBA) + 5)) + b"\x90")
    # Vencedores da semifinal (rodada 0x12) sobem; perdedores ficam.
    _replace(code, at(0x00C1005F), b"\x6a\x14", b"\x6a\x12")
    _replace(code, at(0x00C10068), b"\x8b\x07", b"\xEB\x15")   # pula o destino do perdedor da final
    return bytes(code)


def _playoff_stubs() -> tuple[bytes, dict[str, int]]:
    asm = Asm(PLAYOFF_STUBS)
    entry = {}

    entry["dispatch"] = asm.here
    asm.raw(b"\x80\x7C\x24\x04\x01")                       # cmp byte ptr [esp+4], 1
    asm.raw(b"\x0F\x84" + u32(PLAYOFF_COPY - (asm.here + 6)))  # je cópia italiana
    asm.jmp(B_BUILDER)

    entry["zone"] = asm.here
    asm.raw(b"\xC6\x46\x12\x04")                            # mov byte ptr [esi+0x12], 4
    asm.raw(b"\x83\xEC\x10")                                 # sub esp, 16
    asm.raw(b"\xC7\x04\x24" + u32(FATE_VTABLES[0]))
    asm.raw(b"\xC7\x44\x24\x04" + u32(FATE_VTABLES[1]))
    asm.raw(b"\xC7\x44\x24\x08" + u32(PLAYOFF_STAGE_CODE))
    asm.raw(b"\xC7\x44\x24\x0C" + u32(-1))
    asm.raw(b"\x8B\xC4\x50")                                 # mov eax, esp ; push eax
    asm.push(2).mov_ecx_esi().call(STAGE_ACTION)
    asm.raw(b"\x83\xC4\x10")                                 # add esp, 16
    asm.raw(b"\x8D\x4C\x24\x10").push(0x640).jmp(0x00BBA7BF)  # instruções originais

    entry["date"] = asm.here
    asm.push(2).push(0x7D0).push(10).push(16).push(0x4B0)   # sorteio: 16/11, 12:00
    asm.jmp(PLAYOFF_COPY + (0x00C0FF3B - ITA_BUILDER))
    return bytes(asm.code), entry


def build_playoff_swaps(data: bytes):
    from .exe_patches import Swap

    stubs, entry = _playoff_stubs()
    copy = _playoff_copy(data, entry["date"])
    if PLAYOFF_COPY + len(copy) > PLAYOFF_STUBS or PLAYOFF_STUBS + len(stubs) > TEXT_FREE[1]:
        raise ValueError("playoffs não cabem na área livre")

    slot = off(B_VTABLE + 4 * STAGE_SLOT)
    return (
        Swap(TEXT_VSIZE[0], u32(TEXT_VSIZE[1]), u32(TEXT_VSIZE[2]), shared=True),
        Swap(off(PLAYOFF_COPY), bytes(len(copy)), copy),
        Swap(off(PLAYOFF_STUBS), bytes(len(stubs)), stubs),
        Swap(slot, u32(B_BUILDER), u32(entry["dispatch"])),                      # método 71 da Série B
        Swap(off(0x00BB2E1D), b"\x6a\x01", b"\x6a\x02"),                         # Série B: 2 fases
        Swap(off(0x00BBA7B6), bytes.fromhex("8d4c24106840060000"),
             _jmp(0x00BBA7B6, entry["zone"], 9)),                                # zona de playoff
    )
