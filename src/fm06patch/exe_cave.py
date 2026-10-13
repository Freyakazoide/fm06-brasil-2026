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
    # 1ª fase: os 8 primeiros vão para a fase de grupos (zona 1 + ação 5, como
    # nos grupos da antiga C); quem sobe sai da 2ª fase.
    _replace(code, 0xCA, b"\xC6\x46\x11\x02", b"\xC6\x46\x11\x08")
    # rebaixamento continua para a antiga C (0x1A2B8, em +0x10A); 2 caem (+0x14)
    _replace(code, 0xAB, b"\xC6\x46\x0A\x02", b"\xC6\x46\x0A\x01")             # turno único
    # Datas da 1ª fase: 5/4 a 23/8 (push mês, push dia; mês começa em 0). Com
    # folga: os estaduais empurram rodadas para depois da data de fim, e se a
    # fase não terminou na data de fim, ninguém passa para a fase seguinte.
    for at, old, new in (
        (0x148, 7, 6),        # 1º par, início: agosto -> julho (dia 5)
        (0x15C, 0x0B, 7),     # 1º par, fim: mês dezembro -> agosto
        (0x15E, 2, 23),       #          dia 23
        (0x185, 3, 3),        # 2º par, início: abril
        (0x187, 0x1D, 5),     #          dia 29 -> 5
        (0x199, 0x0B, 7),     # 2º par, fim: agosto
        (0x19B, 2, 23),       #          dia 23
    ):
        _replace(code, at, bytes([0x6A, old]), bytes([0x6A, new]))
    # Ação "classifica para a fase de grupos" (desvio para a seção nova).
    _replace(code, 0x116, bytes.fromhex("8d4c24106840060000"),
             b"\xE9" + u32(C_QUALIFY - (NEW_BUILDER + 0x116 + 5)) + b"\x90" * 4)
    return bytes(code)


def _new_ctor(data: bytes) -> bytes:
    code = bytearray(data[off(B_CTOR):off(B_CTOR) + B_CTOR_SIZE])
    _relocate(code, B_CTOR, NEW_CTOR, B_CTOR_CALLS)
    _replace(code, 0x17, b"\x6A\x01\x6A\x01\x8B\xF1\x68" + u32(SERIE_B_ID),
             b"\x6A\x02\x6A\x01\x8B\xF1\x68" + u32(NEW_C_ID))                    # nível 2, ID novo
    _replace(code, 0x35, b"\xC7\x06" + u32(B_VTABLE), b"\xC7\x06" + u32(NEW_VTABLE))
    _replace(code, 0x2D, b"\x6A\x01", b"\x6A\x02")                                # 2 fases
    return bytes(code)


def _new_vtable(data: bytes) -> bytes:
    raw = bytearray(data[off(B_VTABLE) - 4:off(B_VTABLE) + 4 * VTABLE_SLOTS])
    struct.pack_into("<I", raw, 4 + 4 * STAGE_SLOT, C_DISPATCH)
    struct.pack_into("<I", raw, 4 + 4 * NEXT_STAGE_SLOT, C_NEXT)
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

# ---------------------------------------------------------------------------
# Seção nova no fim do executável (".fm26", 64 KB, código), para o que não
# cabe nas sobras de .text.
# ---------------------------------------------------------------------------
SECTION_RVA = 0x011B4000
SECTION_VA = IMAGE_BASE + SECTION_RVA
SECTION_RAW = 0x00F2B000          # fim do arquivo original
SECTION_SIZE = 0x10000
NSECTIONS_AT = 0x10E
SIZE_OF_IMAGE_AT = 0x158
SECTION_HEADER_AT = 0x2A0
SIZE_OF_IMAGE = (0x011B379E, SECTION_RVA + SECTION_SIZE)


def sec_off(va: int) -> int:
    return va - SECTION_VA + SECTION_RAW


def section_swaps(data: bytes):
    from .exe_patches import Swap

    header = (b".fm26\0\0\0" + struct.pack("<IIII", SECTION_SIZE, SECTION_RVA, SECTION_SIZE, SECTION_RAW)
              + bytes(12) + struct.pack("<I", 0xE0000020))
    return [
        Swap(NSECTIONS_AT, b"\x04\x00", b"\x05\x00", shared=True),
        Swap(SIZE_OF_IMAGE_AT, u32(SIZE_OF_IMAGE[0]), u32(SIZE_OF_IMAGE[1]), shared=True),
        Swap(SECTION_HEADER_AT, data[SECTION_HEADER_AT:SECTION_HEADER_AT + 40], header, shared=True),
        Swap(SECTION_RAW + SECTION_SIZE - 1, b"\x00", b"\x00", shared=True),   # tamanho do arquivo
    ]


# ---------------------------------------------------------------------------
# Série C em fases: 1ª fase (cópia da B, liga de 20 em turno único, 8
# avançam, 2 caem) e 2ª fase com 2 grupos de 4, ida e volta, os 2 primeiros de
# cada grupo sobem. A 2ª fase é uma cópia da 1ª fase da antiga C
# (0x00BBFD00, grupos), que o despachante chama com o índice de fase 0.
# ---------------------------------------------------------------------------
C_DISPATCH = SECTION_VA + 0x000
C_QUALIFY = SECTION_VA + 0x020
OLD_C_COPY = SECTION_VA + 0x100
OLD_C_BUILDER = 0x00BBFD00
OLD_C_BUILDER_SIZE = 0x9C8
OLD_C_BUILDER_CALLS = (
    0xBE, 0xD7, 0x101, 0x12B, 0x140, 0x15A, 0x17B, 0x1F2, 0x202, 0x212, 0x249, 0x286,
    0x29D, 0x2AD, 0x2C5, 0x2D5, 0x2F3, 0x308, 0x31C, 0x331, 0x348, 0x359, 0x37B,
    0x38E, 0x3A2, 0x3F9, 0x416, 0x43E, 0x497, 0x4A2, 0x4BB, 0x4D6, 0x514, 0x527,
    0x535, 0x547, 0x550, 0x55B, 0x56D, 0x587, 0x5C0, 0x5CF, 0x5DC, 0x5EB, 0x5FA,
    0x609, 0x618, 0x627, 0x636, 0x645, 0x65B, 0x66E, 0x677, 0x682, 0x694, 0x6AA,
    0x6DB, 0x6EA, 0x6F7, 0x706, 0x715, 0x724, 0x736, 0x749, 0x752, 0x785, 0x7A8,
    0x7C3, 0x7EA, 0x804, 0x825, 0x839, 0x8B0, 0x8D5, 0x8EC, 0x8FC, 0x913, 0x923,
    0x938, 0x94D, 0x964, 0x98B, 0x9A2,
)
GROUP_STAGE_NAME = 0x49           # nome usado pela fase de grupos (0x00B4BE40)
C_NEXT = SECTION_VA + 0xB00
B_NEXT = SECTION_VA + 0xC00

# Método 72 da competição: chamado pelo motor (0x00AC5BD9) quando uma fase
# termina; é ele que cria a fase seguinte. A e B usam o padrão (0x007560A0,
# não faz nada); a antiga C tem o próprio (0x00BBA900). Sem ele a fase 2 nunca
# é criada, a competição nunca termina e a temporada do país não vira.
NEXT_STAGE_SLOT = 72
DEFAULT_NEXT_STAGE = 0x007560A0
LEAGUE_STAGE_GET = 0x00AC7320     # fase de liga pelo índice (this = competição)
LEAGUE_QUALIFIED = 0x00B18D50     # (NEXT_STAGE_INFO*, lista*, -1): classificados da fase
GROUP_STAGE_NEW = 0x00B5ADC0      # GROUP_STAGE(índice, lista*, 0), objeto de 0x34 bytes
ADD_STAGE = 0x00AC5150            # competição.acrescenta(fase, 1)
TEAM_LIST_VTABLE = 0x00EB4ECC
TEAM_LIST_FREE = 0x00558550       # destrutor da lista (this = lista)
ITA_PLAYOFF_NEW = 0x00C0A810      # Série B italiana: playoff com os 4 de código 0x75
STAGE_ALLOC = 0x00C4E070          # alocador usado na criação das fases


def _c_next_stage() -> bytes:
    """Método 72 da nova C: terminou a fase 0 -> cria a fase de grupos com os
    classificados (código GROUP_STAGE_NAME) da fase de liga."""
    a = Asm(C_NEXT)
    a.raw(b"\x8B\x44\x24\x04")                  # mov eax, [esp+4]   (fase que terminou)
    a.raw(b"\x80\x78\x08\x00")                  # cmp byte [eax+8], 0
    jne1 = len(a.code); a.raw(b"\x0F\x85" + u32(0))   # jne fim (salto longo)
    a.raw(b"\x80\xB9\x98\x00\x00\x00\x01")      # cmp byte [ecx+0x98], 1 (só a fase 0 criada)
    jne2 = len(a.code); a.raw(b"\x0F\x85" + u32(0))
    a.raw(b"\x56\x8B\xF1")                      # push esi ; mov esi, ecx
    a.raw(b"\x83\xEC\x20")                      # sub esp, 0x20: lista em [esp], NEXT_STAGE_INFO em [esp+0x10]
    a.raw(b"\xC7\x04\x24" + u32(TEAM_LIST_VTABLE))
    for off_, val in ((4, 0), (8, 0), (0xC, 0), (0x10, FATE_VTABLES[0]), (0x14, FATE_VTABLES[1]),
                      (0x18, GROUP_STAGE_NAME), (0x1C, -1)):
        a.raw(b"\xC7\x44\x24" + bytes([off_]) + u32(val))
    a.push(0).push(-1).push(0).raw(b"\x8B\xCE").call(LEAGUE_STAGE_GET)
    a.raw(b"\x8B\xC8")                          # mov ecx, eax (fase de liga)
    a.push(-1)
    a.raw(b"\x8D\x54\x24\x04\x52")              # lea edx, [esp+4] (lista) ; push edx
    a.raw(b"\x8D\x54\x24\x18\x52")              # lea edx, [esp+0x18] (NEXT_STAGE_INFO) ; push edx
    a.call(LEAGUE_QUALIFIED)
    a.push(0x34).call(STAGE_ALLOC).raw(b"\x83\xC4\x04")
    a.raw(b"\x85\xC0")                          # test eax, eax
    je1 = len(a.code); a.raw(b"\x74\x00")
    a.raw(b"\x8B\xC8")                          # mov ecx, eax
    a.push(0).raw(b"\x8D\x54\x24\x04\x52").push(1).call(GROUP_STAGE_NEW)   # (1, lista, 0)
    a.push(1).raw(b"\x50\x8B\xCE").call(ADD_STAGE)                         # acrescenta(fase, 1)
    free = len(a.code)
    a.raw(b"\x8D\x0C\x24").call(TEAM_LIST_FREE)  # lea ecx, [esp] ; libera a lista
    a.raw(b"\x83\xC4\x20\x5E")                  # add esp, 0x20 ; pop esi
    ret = len(a.code)
    a.raw(b"\xC2\x04\x00")                      # ret 4
    code = bytearray(a.code)
    struct.pack_into("<i", code, jne1 + 2, ret - (jne1 + 6))
    struct.pack_into("<i", code, jne2 + 2, ret - (jne2 + 6))
    code[je1 + 1] = free - (je1 + 2)
    return bytes(code)


def _b_next_stage() -> bytes:
    """Método 72 da Série B: terminou a fase 0 -> playoff (função da Série B italiana)."""
    a = Asm(B_NEXT)
    a.raw(b"\x8B\x44\x24\x04\x80\x78\x08\x00")    # mov eax,[esp+4] ; cmp byte [eax+8], 0
    jne1 = len(a.code); a.raw(b"\x75\x00")
    a.raw(b"\x80\xB9\x98\x00\x00\x00\x01")       # cmp byte [ecx+0x98], 1
    jne2 = len(a.code); a.raw(b"\x75\x00")
    a.call(ITA_PLAYOFF_NEW)
    ret = len(a.code)
    a.raw(b"\xC2\x04\x00")
    code = bytearray(a.code)
    code[jne1 + 1] = ret - (jne1 + 2)
    code[jne2 + 1] = ret - (jne2 + 2)
    return bytes(code)
QUALIFY_ACTION = 5                # zona 1 classifica para a fase seguinte


def _c_phase_code(data: bytes) -> list[tuple[int, bytes]]:
    disp = Asm(C_DISPATCH)
    disp.raw(b"\x80\x7C\x24\x04\x01")                         # cmp byte ptr [esp+4], 1
    disp.raw(b"\x0F\x85" + u32(NEW_BUILDER - (disp.here + 6)))   # jne 1ª fase
    disp.raw(b"\xC6\x44\x24\x04\x00")                         # fase 0 na cópia da antiga C
    disp.jmp(OLD_C_COPY)

    qual = Asm(C_QUALIFY)
    qual.raw(b"\x83\xEC\x10")
    qual.raw(b"\xC7\x04\x24" + u32(FATE_VTABLES[0]))
    qual.raw(b"\xC7\x44\x24\x04" + u32(FATE_VTABLES[1]))
    qual.raw(b"\xC7\x44\x24\x08" + u32(GROUP_STAGE_NAME))
    qual.raw(b"\xC7\x44\x24\x0C" + u32(-1))
    qual.raw(b"\x8B\xC4\x50")
    qual.push(QUALIFY_ACTION).mov_ecx_esi().call(STAGE_ACTION)
    qual.raw(b"\x83\xC4\x10")
    qual.raw(b"\x8D\x4C\x24\x10").push(0x640).jmp(NEW_BUILDER + 0x11F)

    code = bytearray(data[off(OLD_C_BUILDER):off(OLD_C_BUILDER) + OLD_C_BUILDER_SIZE])
    _relocate(code, OLD_C_BUILDER, OLD_C_COPY, OLD_C_BUILDER_CALLS)
    _replace(code, 0xF9, bytes.fromhex("c6460810"), bytes.fromhex("c6460802"))    # 2 grupos
    _replace(code, 0x19D, bytes.fromhex("c6460b08"), bytes.fromhex("c6460b04"))   # de 4
    _replace(code, 0x1D5, bytes.fromhex("c6461402"), bytes.fromhex("c6461400"))   # ninguém cai aqui
    _replace(code, 0x1F7, b"\x6a\xff", b"\xEB\x1E")    # regras de acesso/rebaixamento já estão na 1ª fase
    _replace(code, 0x21C, b"\xc7\x44", b"\xEB\x30")    # sem ação 5: zona 1 desta fase = sobe
    for at, old, new in (
        (0x253, 5, 8), (0x25C, 0x19, 6),      # início: 6/9
        (0x290, 8, 10), (0x292, 0x14, 1),     # fim: 1/11
    ):
        _replace(code, at, bytes([0x6A, old]), bytes([0x6A, new]))
    return [(C_DISPATCH, bytes(disp.code)), (C_QUALIFY, bytes(qual.code)), (OLD_C_COPY, bytes(code)),
            (C_NEXT, _c_next_stage())]


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
    swaps = section_swaps(data) + [
        Swap(sec_off(va), bytes(len(blob)), blob) for va, blob in _c_phase_code(data)
    ] + [
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
PLAYOFF_STAGE_CODE = 0x75        # código usado pela Série B italiana (zona 2 -> playoff)


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
    _replace(code, at(0x00C0FF47), bytes.fromhex("68d10700006a056a0a"), bytes.fromhex("68d00700006a0a6a16"))
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
    # Sorteio 20/11 e 1º jogo 22/11: depois do fim da fase de liga (15/11),
    # com folga para rodadas empurradas pelos estaduais. Se a fase de liga não
    # tiver terminado, o playoff fica sem times e a temporada do Brasil não fecha.
    asm.push(2).push(0x7D0).push(10).push(20).push(0x4B0)
    asm.jmp(PLAYOFF_COPY + (0x00C0FF3B - ITA_BUILDER))
    return bytes(asm.code), entry


def build_playoff_swaps(data: bytes):
    from .exe_patches import Swap

    stubs, entry = _playoff_stubs()
    copy = _playoff_copy(data, entry["date"])
    if PLAYOFF_COPY + len(copy) > PLAYOFF_STUBS or PLAYOFF_STUBS + len(stubs) > TEXT_FREE[1]:
        raise ValueError("playoffs não cabem na área livre")

    slot = off(B_VTABLE + 4 * STAGE_SLOT)
    next_slot = off(B_VTABLE + 4 * NEXT_STAGE_SLOT)
    b_next = _b_next_stage()
    return tuple(section_swaps(data)) + (
        Swap(sec_off(B_NEXT), bytes(len(b_next)), b_next),
        Swap(next_slot, u32(DEFAULT_NEXT_STAGE), u32(B_NEXT)),                 # método 72 da Série B
        Swap(TEXT_VSIZE[0], u32(TEXT_VSIZE[1]), u32(TEXT_VSIZE[2]), shared=True),
        Swap(off(PLAYOFF_COPY), bytes(len(copy)), copy),
        Swap(off(PLAYOFF_STUBS), bytes(len(stubs)), stubs),
        Swap(slot, u32(B_BUILDER), u32(entry["dispatch"])),                      # método 71 da Série B
        Swap(off(0x00BB2E1D), b"\x6a\x01", b"\x6a\x02"),                         # Série B: 2 fases
        Swap(off(0x00BBA7B6), bytes.fromhex("8d4c24106840060000"),
             _jmp(0x00BBA7B6, entry["zone"], 9)),                                # zona de playoff
    )
