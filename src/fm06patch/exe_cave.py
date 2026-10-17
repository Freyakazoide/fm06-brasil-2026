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
- Antiga C: nível 2 -> 3 no construtor; acesso passa a sair da fase final e
  ir para a nova C.
- Série B: rebaixamento passa a ir para a nova C.
- Virada da temporada: nova C e D juntam acesso e rebaixamento de todas as
  fases e informam a variação de tamanho (ver "Acesso e rebaixamento").
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
    # 1ª fase: ninguém sobe direto (zona 1 = 0); os 8 primeiros vão para a fase
    # de grupos pela zona 2 (gravada no desvio C_QUALIFY), o padrão das fases
    # de liga com playoff (Championship, Série B italiana).
    _replace(code, 0xCA, b"\xC6\x46\x11\x02", b"\xC6\x46\x11\x00")
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
    _replace(code, 0x2D, b"\x6A\x01", b"\x6A\x03")                                # 3 fases
    return bytes(code)


def _new_vtable(data: bytes) -> bytes:
    raw = bytearray(data[off(B_VTABLE) - 4:off(B_VTABLE) + 4 * VTABLE_SLOTS])
    struct.pack_into("<I", raw, 4 + 4 * STAGE_SLOT, C_DISPATCH)
    struct.pack_into("<I", raw, 4 + 4 * NEXT_STAGE_SLOT, C_FINAL_NEXT)
    struct.pack_into("<I", raw, 4 + MOVES_OFFSET, MOVES_COLLECT)
    struct.pack_into("<I", raw, 4 + SIZE_CHANGE_OFFSET, C_SIZE_CHANGE)
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

    # bra_get_minimum_division_teams: nova C com pelo menos 20 (cresce para
    # 24 e 28, sem máximo).
    entry["minimum"] = asm.here
    asm.push(0).push(-2).push(20).push(0).push(SERIE_A_ID).mov_ecx_esi().call(MIN_TEAMS)
    asm.push(0).push(-1).push(20).push(0).push(NEW_C_ID).mov_ecx_esi().call(MIN_TEAMS)
    asm.jmp(0x00BB2859)
    return bytes(asm.code), entry


def _jmp(at: int, target: int, length: int) -> bytes:
    return b"\xE9" + u32(target - (at + 5)) + b"\x90" * (length - 5)


# O jogo conta os times de cada divisão (TEAM+0x54, em 0x00AA7B4D) e só deixa
# o país jogável se a contagem estiver entre o mínimo e o máximo registrados
# em bra_get_minimum_division_teams (0x00AA7BF0; máximo -2 = igual ao mínimo,
# -1 = sem máximo). A nova C exige pelo menos 20.
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
C_FINAL_NEXT = SECTION_VA + 0x5000   # método 72: grupos terminaram -> final
GROUP_ORDER = SECTION_VA + 0x5100    # classificados na ordem 1,4,5,8 | 2,3,6,7
GROUP_STAGE_VTABLE = 0x011228C4
GROUPS_QUALIFIED = 0x00B577B0     # (NEXT_STAGE_INFO*, lista*, -1): classificados de cada grupo
KNOCKOUT_NEW = 0x00B44060         # mata-mata(índice, lista*, cabeças*, 0), objeto de 0x30 bytes
QUALIFY_OFFSET = 0x00B0FF70       # ação "o n-ésimo da zona classifica" (marca, NSI*, n)
FINAL_CODE = 0x14                 # rodada "Final"

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
    # Trava (como a Série B italiana): sem exatamente 8 classificados, fecha a
    # competição com uma fase vazia em vez de criar grupos com vagas sem time.
    a.raw(b"\x66\x83\x7C\x24\x08" + bytes([QUALIFIED]))   # cmp word ptr [esp+8], 8
    jne3 = len(a.code); a.raw(b"\x75\x00")
    a.call(GROUP_ORDER)                         # grupos pela posição (sem sorteio)
    a.push(0x34).call(STAGE_ALLOC).raw(b"\x83\xC4\x04")
    a.raw(b"\x85\xC0")                          # test eax, eax
    je1 = len(a.code); a.raw(b"\x74\x00")
    a.raw(b"\x8B\xC8")                          # mov ecx, eax
    a.push(0).raw(b"\x8D\x54\x24\x04\x52").push(1).call(GROUP_STAGE_NEW)   # (1, lista, 0)
    a.push(1).raw(b"\x50\x8B\xCE").call(ADD_STAGE)                         # acrescenta(fase, 1)
    jmp_free = len(a.code); a.raw(b"\xEB\x00")
    empty = len(a.code)
    a.push(1).push(0).raw(b"\x8B\xCE").call(ADD_STAGE)                      # acrescenta(nada, 1)
    free = len(a.code)
    a.raw(b"\x8D\x0C\x24").call(TEAM_LIST_FREE)  # lea ecx, [esp] ; libera a lista
    a.raw(b"\x83\xC4\x20\x5E")                  # add esp, 0x20 ; pop esi
    ret = len(a.code)
    a.raw(b"\xC2\x04\x00")                      # ret 4
    code = bytearray(a.code)
    struct.pack_into("<i", code, jne1 + 2, ret - (jne1 + 6))
    struct.pack_into("<i", code, jne2 + 2, ret - (jne2 + 6))
    code[je1 + 1] = free - (je1 + 2)
    code[jne3 + 1] = empty - (jne3 + 2)
    code[jmp_free + 1] = free - (jmp_free + 2)
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
def _group_order() -> bytes:
    """Reordena os 8 classificados (em ordem de classificação) para os grupos
    sem sorteio: grupo 1 = 1º, 4º, 5º, 8º; grupo 2 = 2º, 3º, 6º, 7º (2026)."""
    g = Asm(GROUP_ORDER)
    g.raw(b"\x56\x8B\x74\x24\x0C")                   # push esi ; mov esi, [esp+0xC] (itens da lista)
    g.raw(b"\x8B\x46\x04\x8B\x4E\x08\x8B\x56\x0C")   # eax = 2º ; ecx = 3º ; edx = 4º
    g.raw(b"\x89\x56\x04\x8B\x56\x10\x89\x56\x08")   # [1] = 4º ; [2] = 5º
    g.raw(b"\x8B\x56\x1C\x89\x56\x0C\x89\x46\x10")   # [3] = 8º ; [4] = 2º
    g.raw(b"\x8B\x56\x14\x8B\x46\x18")               # edx = 6º ; eax = 7º
    g.raw(b"\x89\x4E\x14\x89\x56\x18\x89\x46\x1C")   # [5] = 3º ; [6] = 6º ; [7] = 7º
    g.raw(b"\x5E\xC3")
    return bytes(g.code)


def _c_final_next() -> bytes:
    """Método 72 da nova C. Fase 1 (grupos) terminou -> final em ida e volta com o
    1º de cada grupo; sem 2 classificados, fecha com uma fase vazia. Outras fases
    -> C_NEXT."""
    a = Asm(C_FINAL_NEXT)
    a.raw(b"\x8B\x44\x24\x04\x80\x78\x08\x01")       # mov eax, [esp+4] ; cmp byte [eax+8], 1
    a.raw(b"\x0F\x85" + u32(C_NEXT - (a.here + 6)))  # jne C_NEXT
    a.raw(b"\x80\xB9\x98\x00\x00\x00\x02")           # cmp byte [ecx+0x98], 2
    jne_ret = len(a.code); a.raw(b"\x0F\x85" + u32(0))
    a.raw(b"\x56\x8B\xF1\x83\xEC\x20")               # push esi ; mov esi, ecx ; sub esp, 0x20
    a.raw(b"\xC7\x04\x24" + u32(TEAM_LIST_VTABLE))
    for o, v in ((4, 0), (8, 0), (0xC, 0), (0x10, FATE_VTABLES[0]), (0x14, FATE_VTABLES[1]),
                 (0x18, FINAL_CODE), (0x1C, -1)):
        a.raw(b"\xC7\x44\x24" + bytes([o]) + u32(v))
    a.raw(b"\x8B\x4C\x24\x28")                       # mov ecx, [esp+0x28] (fase que terminou)
    a.raw(b"\x81\x39" + u32(GROUP_STAGE_VTABLE))     # cmp dword [ecx], GROUP_STAGE
    jne_e1 = len(a.code); a.raw(b"\x75\x00")
    a.push(-1).raw(b"\x8D\x54\x24\x04\x52\x8D\x54\x24\x18\x52").call(GROUPS_QUALIFIED)
    a.raw(b"\x66\x83\x7C\x24\x08\x02")               # cmp word [esp+8], 2
    jne_e2 = len(a.code); a.raw(b"\x75\x00")
    a.push(0x30).call(STAGE_ALLOC).raw(b"\x83\xC4\x04\x85\xC0")
    je_free = len(a.code); a.raw(b"\x74\x00")
    a.raw(b"\x8B\xC8").push(0).push(0)               # mov ecx, eax ; 0 ; cabeças = NULL
    a.raw(b"\x8D\x54\x24\x08\x52").push(2).call(KNOCKOUT_NEW)   # mata-mata(2, lista, 0, 0)
    a.push(1).raw(b"\x50\x8B\xCE").call(ADD_STAGE)
    jmp_free = len(a.code); a.raw(b"\xEB\x00")
    empty = len(a.code)
    a.push(1).push(0).raw(b"\x8B\xCE").call(ADD_STAGE)
    free = len(a.code)
    a.raw(b"\x8D\x0C\x24").call(TEAM_LIST_FREE)
    a.raw(b"\x83\xC4\x20\x5E")
    ret = len(a.code)
    a.raw(b"\xC2\x04\x00")
    code = bytearray(a.code)
    struct.pack_into("<i", code, jne_ret + 2, ret - (jne_ret + 6))
    for at, target in ((jne_e1, empty), (jne_e2, empty), (je_free, free), (jmp_free, free)):
        code[at + 1] = (target - (at + 2)) & 0xFF
    return bytes(code)


QUALIFY_ZONE = 2                  # zona 2 da fase de liga classifica para a fase seguinte
QUALIFIED = 8                     # quantos vão para a fase de grupos


def _c_phase_code(data: bytes) -> list[tuple[int, bytes]]:
    # fase 0 -> 1ª fase (cópia da B); 1 -> grupos (fase 0 da cópia da antiga C);
    # 2 -> final (mata-mata, fase 1 da cópia); 3+ -> cópia da B (devolve 0)
    disp = Asm(C_DISPATCH)
    disp.raw(b"\x8A\x44\x24\x04\x3C\x01")                      # mov al, [esp+4] ; cmp al, 1
    disp.raw(b"\x0F\x82" + u32(NEW_BUILDER - (disp.here + 6)))   # jb 1ª fase
    disp.raw(b"\x3C\x02")                                     # cmp al, 2
    disp.raw(b"\x0F\x87" + u32(NEW_BUILDER - (disp.here + 6)))   # ja
    disp.raw(b"\xFE\xC8\x88\x44\x24\x04")                      # dec al ; mov [esp+4], al
    disp.jmp(OLD_C_COPY)

    qual = Asm(C_QUALIFY)
    qual.raw(b"\x66\xC7\x46\x0C\x00\x00")             # +0x0C = 0: o líder da 1ª fase não é campeão
    qual.raw(b"\xC6\x46\x12" + bytes([QUALIFIED]))   # mov byte ptr [esi+0x12], 8 (zona 2)
    # Com 28 clubes (tamanho final) caem 6, para a Série D poder subir 6.
    qual.raw(b"\x80\x7E\x0B" + bytes([C_FINAL_SIZE]))  # cmp byte ptr [esi+0xB], 28 (clubes)
    qual.raw(b"\x72\x04")                                # jb +4
    qual.raw(b"\xC6\x46\x14\x06")                      # mov byte ptr [esi+0x14], 6
    qual.raw(b"\x83\xEC\x10")
    qual.raw(b"\xC7\x04\x24" + u32(FATE_VTABLES[0]))
    qual.raw(b"\xC7\x44\x24\x04" + u32(FATE_VTABLES[1]))
    qual.raw(b"\xC7\x44\x24\x08" + u32(GROUP_STAGE_NAME))
    qual.raw(b"\xC7\x44\x24\x0C" + u32(-1))
    qual.raw(b"\x8B\xC4\x50")
    qual.push(QUALIFY_ZONE).mov_ecx_esi().call(STAGE_ACTION)
    qual.raw(b"\x83\xC4\x10")
    qual.raw(b"\x8D\x4C\x24\x10").push(0x640).jmp(NEW_BUILDER + 0x11F)

    code = bytearray(data[off(OLD_C_BUILDER):off(OLD_C_BUILDER) + OLD_C_BUILDER_SIZE])
    _relocate(code, OLD_C_BUILDER, OLD_C_COPY, OLD_C_BUILDER_CALLS)
    _replace(code, 0xF9, bytes.fromhex("c6460810"), bytes.fromhex("c6460802"))    # 2 grupos
    _replace(code, 0x19D, bytes.fromhex("c6460b08"), bytes.fromhex("c6460b04"))   # de 4
    _replace(code, 0x1D5, bytes.fromhex("c6461402"), bytes.fromhex("c6461400"))   # ninguém cai aqui
    # Regra de acesso para a Série B fica (os 2 primeiros de cada grupo sobem);
    # a de rebaixamento sai (quem cai sai da 1ª fase).
    _replace(code, 0x207, b"\x6a\xff", b"\xEB\x0E")
    _replace(code, 0x109, bytes.fromhex("66c7460a0020"), bytes.fromhex("66c7460a0000"))   # sem sorteio
    # No lugar da ação 5: o 1º de cada grupo (marca 1, posição 0) vai para a
    # final (rodada 0x14). A zona 1 continua sendo o acesso (2 por grupo).
    final = Asm(OLD_C_COPY + 0x21C)
    final.raw(b"\xC7\x44\x24\x30" + u32(FATE_VTABLES[0]) + b"\xC7\x44\x24\x34" + u32(FATE_VTABLES[1]))
    final.raw(b"\xC7\x44\x24\x38" + u32(FINAL_CODE) + b"\xC7\x44\x24\x3C" + u32(-1))
    final.push(0).raw(b"\x8D\x44\x24\x34\x50").push(1).raw(b"\x8B\xCE").call(QUALIFY_OFFSET)
    final.raw(b"\x66\x90")
    assert len(final.code) == 0x32
    code[0x21C:0x24E] = final.code
    # Tipo da zona 1 (+0x0C, lido em 0x00B17836): 4 marca "Q" (classificado,
    # marca 5), 2 marca "P" (acesso, marca 1). Só a marca 1 entra no acesso.
    _replace(code, 0x1EC, bytes.fromhex("66c7460c0400"), bytes.fromhex("66c7460c0200"))
    for at, old, new in (
        (0x253, 5, 8), (0x25C, 0x19, 6),      # início: 6/9
        (0x290, 8, 9), (0x292, 0x14, 18),     # fim: 18/10
    ):
        _replace(code, at, bytes([0x6A, old]), bytes([0x6A, new]))
    # Fase 1 da cópia (mata-mata da antiga C) vira a final: 2 clubes, ida e volta,
    # empate direto nos pênaltis (+0x2E = 2), sorteio 21/10, jogos 25/10 e 1/11,
    # vencedor = campeão (posição final 0), perdedor = 2º; termina na final.
    for at, old, new in (
        (0x3ED, "bd20000000", "bd02000000"),                         # 2 clubes
        (0x469, "66c78424820000000e00", "66c78424820000000200"),     # só pênaltis
        (0x49C, "6a07", "6a14"),                                     # nome "Final"
        (0x4AE, "6a08", "6a09"),                                     # sorteio: outubro
        (0x4C8, "6a08", "6a09"), (0x4CA, "6a18", "6a19"),            # 1º jogo 25/10
        (0x502, "66c78424880000001000", "66c78424880000000100"),     # 1 vencedor
        (0x52D, "6a05", "6aff"),                                     # vencedor: posição 0
        (0x53F, "6a06", "6a01"),                                     # perdedor: posição 1
        (0x555, "6a088d4c244c", "e93002000090"),                     # pula as rodadas seguintes
    ):
        _replace(code, at, bytes.fromhex(old), bytes.fromhex(new))
    return [(C_DISPATCH, bytes(disp.code)), (C_QUALIFY, bytes(qual.code)), (OLD_C_COPY, bytes(code)),
            (C_NEXT, _c_next_stage()), (C_FINAL_NEXT, _c_final_next()),
            (GROUP_ORDER, _group_order())] + _moves_code()


# ---------------------------------------------------------------------------
# Acesso e rebaixamento na virada da temporada
#
# 0x00AFAF30 junta os movimentos de todas as competições do país (método
# 0x228 de cada uma) e processa um par de divisões por vez (de cima, de baixo).
# O par só anda se `sobem == caem + tamanho_de_cima.método_0x140()`; se não
# bater, ninguém do par se mexe. O método 0x140 é a variação de tamanho da
# divisão de cima na temporada seguinte (padrão 0x0084E950 = 0).
#
# O método 0x228 padrão (0x00AC58B0) só olha a PRIMEIRA fase de liga ou de
# grupos. Na nova C quem sobe sai da fase de grupos (2ª fase) e na D sai da
# fase final (3ª fase): o jogo não via ninguém subindo, os pares B/C e C/D não
# batiam e nada andava. MOVES_COLLECT olha todas as fases.
#
# Tamanhos: a nova C cresce 4 por temporada até 28 (20 - 4 - 2 + 4 + 6 = 24;
# 24 -> 28) e depois rebaixa 6. A D fica em 96: perde 6 para a C, ganha os
# que caem da C e completa com clubes de baixo (estaduais) a diferença.
# ---------------------------------------------------------------------------
MOVES_COLLECT = SECTION_VA + 0xD00
C_SIZE_CHANGE = SECTION_VA + 0xD80
D_SIZE_CHANGE = SECTION_VA + 0xDC0
D_FINAL_RULE = SECTION_VA + 0xE00
SIZE_CACHE = SECTION_VA + 0xF00   # variação da C calculada na virada (lida pela D)
MOVES_OFFSET = 0x228
SIZE_CHANGE_OFFSET = 0x140
OLD_C_VTABLE = 0x0113B86C
DEFAULT_MOVES = 0x00AC58B0
DEFAULT_SIZE_CHANGE = 0x0084E950
LEAGUE_MOVES = 0x00B0A600         # fase de liga: (lista) -> quantidade
GROUP_MOVES = 0x00B55F50          # fase de grupos: idem para cada grupo
PROMOTION_RULE = 0x00B0FE50       # (destino, x, -1)
C_FINAL_SIZE = 28
C_GROWTH = 4
D_PROMOTED = 6
D_FINAL_HOOK = 0x00BC0652         # fase final da D, antes de registrar a fase
D_FINAL_HOOK_OLD = bytes.fromhex("8d94241401000052")   # lea edx, [esp+0x114] ; push edx


def _moves_collect() -> bytes:
    """Método 0x228: movimentos de todas as fases de liga e de grupos."""
    a = Asm(MOVES_COLLECT)
    a.raw(b"\x53\x56\x57\x55\x8B\xE9\x33\xFF\x33\xDB")  # push ebx/esi/edi/ebp ; ebp = comp ; edi = bl = 0
    loop = len(a.code)
    a.raw(b"\x3A\x9D\x98\x00\x00\x00")                # cmp bl, [ebp+0x98] (fases criadas)
    jge_done = len(a.code); a.raw(b"\x7D\x00")
    a.raw(b"\x8D\x8D\x90\x00\x00\x00\x8B\x01\x53\xFF\x50\x28")  # fase = fases.get(bl)
    a.raw(b"\x85\xC0")
    je_next1 = len(a.code); a.raw(b"\x74\x00")
    a.raw(b"\x8B\xF0\x8B\x16\x8B\xCE\xFF\x52\x58\x84\xC0")   # é liga?
    jne_league = len(a.code); a.raw(b"\x75\x00")
    a.raw(b"\x8B\x16\x8B\xCE\xFF\x52\x5C\x84\xC0")            # é grupos?
    je_next2 = len(a.code); a.raw(b"\x74\x00")
    a.raw(b"\xFF\x74\x24\x14\x8B\xCE").call(GROUP_MOVES)
    jmp_add = len(a.code); a.raw(b"\xEB\x00")
    league = len(a.code)
    a.raw(b"\xFF\x74\x24\x14\x8B\xCE").call(LEAGUE_MOVES)
    add = len(a.code)
    a.raw(b"\x0F\xBF\xC0\x03\xF8")                      # movsx eax, ax ; add edi, eax
    nxt = len(a.code)
    a.raw(b"\xFE\xC3")                                     # inc bl
    jmp_loop = len(a.code); a.raw(b"\xEB\x00")
    done = len(a.code)
    a.raw(b"\x8B\xC7\x5D\x5F\x5E\x5B\xC2\x04\x00")
    code = bytearray(a.code)
    for at, target in ((jge_done, done), (je_next1, nxt), (jne_league, league), (je_next2, nxt),
                       (jmp_add, add), (jmp_loop, loop)):
        rel = target - (at + 2)
        if not -128 <= rel <= 127:
            raise ValueError("salto curto fora do alcance")
        code[at + 1] = rel & 0xFF
    return bytes(code)


def _c_size_change() -> bytes:
    """Método 0x140 da nova C: +4 enquanto tiver menos de 28 clubes."""
    a = Asm(C_SIZE_CHANGE)
    a.push(0).push(-1).push(0).call(LEAGUE_STAGE_GET)     # 1ª fase de liga
    a.raw(b"\xB1" + bytes([C_GROWTH]))                    # mov cl, 4
    a.raw(b"\x85\xC0\x74\x0B")                           # test eax, eax ; je guarda
    a.raw(b"\x8B\x40\x24")                                # mov eax, [eax+0x24]
    a.raw(b"\x80\x78\x0B" + bytes([C_FINAL_SIZE]))        # cmp byte [eax+0xB], 28
    a.raw(b"\x72\x02\x32\xC9")                           # jb guarda ; xor cl, cl
    a.raw(b"\x88\x0D" + u32(SIZE_CACHE))                   # guarda: mov [SIZE_CACHE], cl
    a.raw(b"\x8A\xC1\xC3")                                # mov al, cl ; ret
    return bytes(a.code)


def _d_size_change() -> bytes:
    """Método 0x140 da D: completa com clubes de baixo o que a C cresceu."""
    return b"\xA0" + u32(SIZE_CACHE) + b"\xC3"            # mov al, [SIZE_CACHE] ; ret


def _d_final_rule() -> bytes:
    """Fase final da D: regra de acesso para a nova C (os 6 primeiros sobem)."""
    a = Asm(D_FINAL_RULE)
    a.push(-1).push(D_PROMOTED).push(NEW_C_ID).mov_ecx_esi().call(PROMOTION_RULE)
    a.raw(D_FINAL_HOOK_OLD)
    a.jmp(D_FINAL_HOOK + len(D_FINAL_HOOK_OLD))
    return bytes(a.code)


def _moves_code() -> list[tuple[int, bytes]]:
    return [(MOVES_COLLECT, _moves_collect()), (C_SIZE_CHANGE, _c_size_change()),
            (D_SIZE_CHANGE, _d_size_change()), (D_FINAL_RULE, _d_final_rule()),
            (SIZE_CACHE, bytes([C_GROWTH]))]


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
            Swap(off(0x00BBA7AA), b"\x68" + u32(OLD_C_ID), b"\x68" + u32(NEW_C_ID)),      # Série B cai p/ nova C
            # D: quem sobe é a fase final, não os grupos (que só classificam)
            Swap(off(0x00BBFEF7), b"\x6a\xff", b"\xEB\x0E"),                             # grupos sem regra de acesso
            Swap(off(D_FINAL_HOOK), D_FINAL_HOOK_OLD, _jmp(D_FINAL_HOOK, D_FINAL_RULE, len(D_FINAL_HOOK_OLD))),
            Swap(off(OLD_C_VTABLE + MOVES_OFFSET), u32(DEFAULT_MOVES), u32(MOVES_COLLECT)),
            Swap(off(OLD_C_VTABLE + SIZE_CHANGE_OFFSET), u32(DEFAULT_SIZE_CHANGE), u32(D_SIZE_CHANGE)),
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
