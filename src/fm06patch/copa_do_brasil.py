"""Copa do Brasil de 2026 em duas fases (a Série A entra na 5ª fase).

FM06 original (BRA_CUP, vtable 0x0113BB24): uma fase, mata-mata de 64
(montagem 0x00BBAD30, rodadas 6, 7, 8, quartas 0x11, semifinal 0x12, final
0x14). Participantes (0x00BB9430): classificados da temporada anterior, clubes
dos estaduais e, para completar 64, Séries A, B e antiga C.

Em 2026: 3ª fase com 48 clubes (44 + 4 campeões), 4ª com 24, 5ª com 32 (12 +
os 20 da Série A), oitavas, quartas, semifinal e final. O patch reproduz da
3ª fase em diante:

- fase 1 (cópia da montagem, 48 clubes): rodadas 6 (48 → 24, 11/3) e 7
  (24 → 12, 18/3); os vencedores da rodada 7 vão para a fase seguinte;
- fase 2 (cópia da montagem, 32 clubes): sorteio em 18/4 (a fase nasce no
  meio da temporada; sem data de sorteio ninguém sorteia os confrontos, teste
  3), 5ª fase (rodada 7, 26/4), oitavas
  (rodada 8, 1/8), quartas (26/8), semifinal (1/11) e final (29/11 e 6/12);
- método 72: quando a fase 1 termina, junta os 12 vencedores e os 20 clubes
  da Série A e cria a fase 2;
- participantes da fase 1: os mesmos critérios, sem a Série A, até 48,
  completando com Série B, nova Série C e Série D.
"""

from __future__ import annotations

import struct

from .exe_cave import (ADD_STAGE, FATE_VTABLES, SECTION_VA, STAGE_ALLOC, TEAM_LIST_FREE,
                       TEAM_LIST_VTABLE, Asm, NEW_C_ID, OLD_C_ID, SERIE_A_ID, SERIE_B_ID,
                       _relocate, _replace, off, sec_off, section_swaps, u32)

CUP_VTABLE = 0x0113BB24
BUILDER = 0x00BBAD30
BUILDER_SIZE = 0x3C4
BUILDER_CALLS = (
    0x4A, 0x66, 0x8E, 0xCD, 0xD8, 0xF3, 0x103, 0x137, 0x14A, 0x153, 0x162, 0x178, 0x188,
    0x1B2, 0x1C5, 0x1CE, 0x1D9, 0x1EF, 0x1FF, 0x22C, 0x23F, 0x248, 0x253, 0x269, 0x279,
    0x2A3, 0x2B1, 0x2BC, 0x2D2, 0x2E2, 0x30A, 0x313, 0x31E, 0x330, 0x346, 0x372, 0x37B, 0x3A2,
)
SELECTION = 0x00BB9430
SEASON_SETUP_STAGES = 0x00BBA921   # push 1 (número de fases) em 0x00BBA920
DEFAULT_NEXT_STAGE = 0x007560A0
REGISTER_TEAMS = 0x00ACD4B0         # competição.inscreve(lista*, -1, -1, -1)
KNOCKOUT_TO_NEXT = 0x00B45500      # (rodada, 0 = vencedores, NEXT_STAGE_INFO*)
KNOCKOUT_GET = 0x00AC73D0          # competição.mata_mata(índice, 0)
KNOCKOUT_QUALIFIED = 0x00B3E6E0    # mata_mata.classificados(NEXT_STAGE_INFO*, lista*)
ADD_COMP_TEAMS = 0x00ACD160        # cdecl (ID, lista*, máximo, -1, 1, -1, 1)
SEEDING = 0x00B3EF00               # cdecl (lista*, cabeças de chave*)
KNOCKOUT_NEW = 0x00B44060          # KNOCKOUT(índice, lista*, cabeças*, 0), 0x30 bytes
ROUND_NAME = 0x00B43720            # rodada.nome(código)
ROUND_DRAW = 0x00B3B550            # rodada.sorteio(hora, dia, mês, 2000, tipo), ret 0x14
COMP_BY_ID = 0x00582440            # this = [0x014EAA34]
COMPS = 0x014EAA34

S0 = SECTION_VA + 0x3000           # cópia da montagem: fase 1 (48)
S1 = SECTION_VA + 0x3400           # cópia da montagem: fase 2 (32)
STUBS = SECTION_VA + 0x3800        # despachante, fim da fase 1, método 72, filtro
POSITIONS = SECTION_VA + 0x3C00    # posições finais de quem cai na fase 1
ROUND_ADD = 0x00B482E0             # fase.adiciona_rodada(modelo em ecx)
ROUND_POSITIONS = 0x00B3BAD0       # modelo.posições(0 vencedor / 1 perdedor, pos, pos, pos)
# Cada fase calcula a posição final a partir da própria última rodada: com a Copa em duas
# fases, quem caía na 4ª fase virava "vice" (posição 1) e quem caía na 3ª, "3º" (2). Com 13
# vices 0x00AB7E00 não acha o vice e o campeão não vai para o histórico (probe de 7/12/2026:
# Santos campeão, 13 com posição 1, 26 com posição 2). Como a Libertadores faz na
# Pré-Libertadores (0x00C07AD9), a fase 1 grava posições abaixo das da fase 2 (5ª fase = 5).
STAGE1_POSITIONS = ((0x14F, 7), (0x1CA, 6))   # (lea ecx,[esp+0x10]; call 0x00B482E0), posição
NEXT_CODE = 0xA7                   # nome da fase 2 (o mesmo da fase final da antiga C)

STAGE1_TEAMS, STAGE2_TEAMS = 48, 32
SERIE_A_TEAMS = 20

# Deslocamentos dentro da montagem copiada (a partir de 0x00BBAD30)
TEAMS_AT = 0x3E                    # mov ebp, 0x40
R1_CODE_AT = 0xD2                  # push 6
R1_DATE = (0xE7, 0xE5)             # push dia, push mês (6A xx)
R1_LEG2_AT = 0xF8                  # push 4 (0x00B3B640)
R1_FLAGS_AT = 0x113                # mov word [esp+0x3C], 0x8403
R1_OUT_AT = 0x12B                  # mov word [esp+0x44], 0x20
R1_EXTRA_AT = 0x132                # mov word [esp+0x46], bp
R2_SKIP_AT = 0x15D                 # push ebp ; lea ecx, [esp+0x14] (depois de mov ebp, 7)
R2_DATE = (0x171, 0x16F)
R2_IN_AT = 0x194                   # mov word [esp+0x36], 0x20
R2_OUT_AT = 0x19B                  # mov word [esp+0x38], 0x10
R3_AT = 0x1D3                      # push 8 (início da 3ª rodada)
R3_DATE = (0x1E8, 0x1E6)
QF_DATE = (0x262, 0x260)
SF_DATE = (0x2CB, 0x2C9)
F_DATE = (0x33F, 0x33D)
FINISH_AT = 0x380                  # fim da montagem (0x00BBB0B0)

ORIGINAL_DATES = {R1_DATE: (2, 1), R2_DATE: (2, 2), R3_DATE: (30, 2), QF_DATE: (20, 3),
                  SF_DATE: (25, 4), F_DATE: (15, 5)}


def _word(at_value: int) -> bytes:
    return struct.pack("<H", at_value)


def _date(code: bytearray, where: tuple[int, int], day: int, month: int) -> None:
    day_at, month_at = where
    old_day, old_month = ORIGINAL_DATES[where]
    _replace(code, day_at, bytes([0x6A, old_day]), bytes([0x6A, day]))
    _replace(code, month_at, bytes([0x6A, old_month]), bytes([0x6A, month]))


def _builder_copy(data: bytes, dest: int) -> bytearray:
    code = bytearray(data[off(BUILDER):off(BUILDER) + BUILDER_SIZE])
    _relocate(code, BUILDER, dest, BUILDER_CALLS)
    return code


def _stage1(data: bytes, tail: int) -> bytes:
    code = _builder_copy(data, S0)
    _replace(code, TEAMS_AT, b"\xBD" + u32(0x40), b"\xBD" + u32(STAGE1_TEAMS))
    _replace(code, R1_OUT_AT, b"\x66\xC7\x44\x24\x44" + _word(0x20), b"\x66\xC7\x44\x24\x44" + _word(24))
    _date(code, R1_DATE, 11, 2)                                   # 3ª fase: 11/3
    _replace(code, R2_IN_AT, b"\x66\xC7\x44\x24\x36" + _word(0x20), b"\x66\xC7\x44\x24\x36" + _word(24))
    _replace(code, R2_OUT_AT, b"\x66\xC7\x44\x24\x38" + _word(0x10), b"\x66\xC7\x44\x24\x38" + _word(12))
    _date(code, R2_DATE, 18, 2)                                   # 4ª fase: 18/3
    _replace(code, R3_AT, code[R3_AT:R3_AT + 5], b"\xE9" + u32(tail - (S0 + R3_AT + 5)))
    for (at, _), stub in zip(STAGE1_POSITIONS, _position_stubs()[1]):
        if code[at:at + 5] != b"\x8D\x4C\x24\x10\xE8":
            raise ValueError(f"copa do brasil: esperava lea ecx,[esp+0x10]; call em +0x{at:X}")
        code[at:at + 9] = b"\xE9" + u32(stub - (S0 + at + 5)) + b"\x90" * 4
    return bytes(code)


def _position_stubs() -> tuple[bytes, list[int]]:
    """Para cada rodada da fase 1: posições do perdedor e depois a chamada original."""
    a = Asm(POSITIONS)
    entries = []
    for at, position in STAGE1_POSITIONS:
        entries.append(a.here)
        a.push(position).push(position).push(position).push(1)
        a.raw(b"\x8D\x4C\x24\x20").call(ROUND_POSITIONS)        # modelo em [esp+0x10] (+4 push)
        a.raw(b"\x8D\x4C\x24\x10").call(ROUND_ADD)               # instrução original
        a.jmp(S0 + at + 9)
    return bytes(a.code), entries


def _stage2(data: bytes, draw: int) -> bytes:
    code = _builder_copy(data, S1)
    _replace(code, TEAMS_AT, b"\xBD" + u32(0x40), b"\xBD" + u32(STAGE2_TEAMS))
    # 1ª rodada da cópia vira a 5ª fase (32 -> 16). Mantém a configuração de 1ª
    # rodada (flags 0x8403, +0x46 = clubes da fase): a da 2ª rodada (0x401,
    # +0x46 = 0) pega os clubes dos vencedores da rodada anterior, que não
    # existe na fase 2, e a rodada nunca era sorteada (teste 3).
    _replace(code, R1_CODE_AT, b"\x6A\x06", b"\x6A\x07")
    _replace(code, R1_OUT_AT, b"\x66\xC7\x44\x24\x44" + _word(0x20), b"\x66\xC7\x44\x24\x44" + _word(0x10))
    _date(code, R1_DATE, 26, 3)                                   # 5ª fase: 26/4 (quarta em 2006)
    # nome da rodada + sorteio (desvio): push 7 ; lea ecx,[esp+0x14] ; call 0x00B43720
    _replace(code, R1_CODE_AT + 2, b"\x8D\x4C\x24\x14\xE8", b"\x8D\x4C\x24\x14\xE8")
    code[R1_CODE_AT:R1_CODE_AT + 11] = (b"\xE9" + u32(draw - (S1 + R1_CODE_AT + 5))) + b"\x90" * 6
    # pula a 2ª rodada original (mantém o mov ebp, 7 que as seguintes usam)
    _replace(code, R2_SKIP_AT, code[R2_SKIP_AT:R2_SKIP_AT + 5],
             b"\xE9" + u32((S1 + R3_AT) - (S1 + R2_SKIP_AT + 5)))
    _date(code, R3_DATE, 1, 7)                                    # oitavas: 1/8
    _date(code, QF_DATE, 26, 7)                                   # quartas: 26/8
    _date(code, SF_DATE, 1, 10)                                   # semifinal: 1/11
    _date(code, F_DATE, 29, 10)                                   # final: 29/11 e 6/12
    return bytes(code)


def _nsi(a: Asm) -> None:
    """NEXT_STAGE_INFO em [esp] (16 bytes, já reservados)."""
    a.raw(b"\xC7\x04\x24" + u32(FATE_VTABLES[0]))
    a.raw(b"\xC7\x44\x24\x04" + u32(FATE_VTABLES[1]))
    a.raw(b"\xC7\x44\x24\x08" + u32(NEXT_CODE))
    a.raw(b"\xC7\x44\x24\x0C" + u32(-1))


def _stubs() -> tuple[bytes, dict[str, int]]:
    a = Asm(STUBS)
    entry = {}

    # método 71: fase 0 -> cópia de 48; fase 1 -> cópia de 32 (chamada como fase 0)
    entry["dispatch"] = a.here
    a.raw(b"\x80\x7C\x24\x04\x00")                         # cmp byte [esp+4], 0
    a.raw(b"\x0F\x84" + u32(S0 - (a.here + 6)))            # je fase 1
    a.raw(b"\x80\x7C\x24\x04\x01")                         # cmp byte [esp+4], 1
    a.raw(b"\x0F\x85" + u32(BUILDER - (a.here + 6)))       # jne original (devolve 0)
    a.raw(b"\xC6\x44\x24\x04\x00").jmp(S1)

    # fim da fase 1: vencedores da rodada 7 -> fase seguinte (esi = mata-mata)
    entry["tail"] = a.here
    a.raw(b"\x83\xEC\x10")
    _nsi(a)
    a.raw(b"\x8B\xC4\x50").push(0).push(7).raw(b"\x8B\xCE").call(KNOCKOUT_TO_NEXT)
    a.raw(b"\x83\xC4\x10").jmp(S0 + FINISH_AT)

    # método 72: terminou a fase 0 -> 12 vencedores + 20 da Série A -> fase 2
    entry["next"] = a.here
    a.raw(b"\x8B\x44\x24\x04\x80\x78\x08\x00")              # mov eax,[esp+4] ; cmp byte [eax+8], 0
    jne1 = len(a.code); a.raw(b"\x0F\x85" + u32(0))
    a.raw(b"\x80\xB9\x98\x00\x00\x00\x01")                  # cmp byte [ecx+0x98], 1
    jne2 = len(a.code); a.raw(b"\x0F\x85" + u32(0))
    a.raw(b"\x56\x57\x8B\xF1")                              # push esi ; push edi ; mov esi, ecx
    a.raw(b"\x81\xEC" + u32(0xA0))                          # lista [esp], NSI [esp+0x10], cabeças [esp+0x20]
    a.raw(b"\xC7\x04\x24" + u32(TEAM_LIST_VTABLE))
    a.raw(b"\x31\xC0\x89\x44\x24\x04\x89\x44\x24\x08\x89\x44\x24\x0C")
    a.raw(b"\x8D\x7C\x24\x20\xB9\x20\x00\x00\x00\xF3\xAB")  # zera as cabeças de chave
    a.raw(b"\x83\xEC\x10")                                  # NSI temporário em [esp]
    _nsi(a)
    a.raw(b"\x8B\x04\x24\x89\x44\x24\x20\x8B\x44\x24\x04\x89\x44\x24\x24")
    a.raw(b"\x8B\x44\x24\x08\x89\x44\x24\x28\x8B\x44\x24\x0C\x89\x44\x24\x2C")
    a.raw(b"\x83\xC4\x10")
    a.push(0).push(0).raw(b"\x8B\xCE").call(KNOCKOUT_GET)   # mata-mata da fase 0
    a.raw(b"\x85\xC0")
    je_none = len(a.code); a.raw(b"\x74\x00")
    a.raw(b"\x8D\x14\x24\x52\x8D\x54\x24\x14\x52\x8B\xC8").call(KNOCKOUT_QUALIFIED)
    none = len(a.code)
    a.push(1).push(-1).push(1).push(-1).push(SERIE_A_TEAMS)
    a.raw(b"\x8D\x44\x24\x14\x50").push(SERIE_A_ID).call(ADD_COMP_TEAMS)
    a.raw(b"\x83\xC4\x1C")
    a.raw(b"\x8D\x44\x24\x20\x50\x8D\x44\x24\x04\x50").call(SEEDING)
    a.raw(b"\x83\xC4\x08")
    # inscreve os 32 na tabela de posições da competição (+0xA4), como a Libertadores faz
    # a cada fase: sem isso a posição final dos 20 da Série A não é gravada e o campeão
    # não entra no histórico (0x00AB7E00 exige campeão e vice; teste: final Santos x Grêmio)
    a.push(-1).push(-1).push(-1).raw(b"\x8D\x44\x24\x0C\x50\x8B\xCE").call(REGISTER_TEAMS)
    a.push(0x30).call(STAGE_ALLOC).raw(b"\x83\xC4\x04\x85\xC0")
    je_free = len(a.code); a.raw(b"\x74\x00")
    a.raw(b"\x8B\xC8").push(0)
    a.raw(b"\x8D\x54\x24\x24\x52\x8D\x54\x24\x08\x52").push(1).call(KNOCKOUT_NEW)
    a.push(1).raw(b"\x50\x8B\xCE").call(ADD_STAGE)
    free = len(a.code)
    a.raw(b"\x8D\x0C\x24").call(TEAM_LIST_FREE)
    a.raw(b"\x81\xC4" + u32(0xA0) + b"\x5F\x5E")
    ret = len(a.code)
    a.raw(b"\xC2\x04\x00")

    # 1ª rodada da fase 2: nome (7) e sorteio em 18/4, depois volta à cópia
    entry["draw"] = a.here
    a.push(7).raw(b"\x8D\x4C\x24\x14").call(ROUND_NAME)
    a.push(4).push(0x7D0).push(3).push(18).push(0x4B0).raw(b"\x8D\x4C\x24\x24").call(ROUND_DRAW)
    a.jmp(S1 + R1_CODE_AT + 11)

    # participantes da fase 1: tira os clubes da Série A da lista (lista em [esp+8])
    entry["filter"] = a.here
    a.raw(b"\x60")                                          # pushad (lista passa a [esp+0x28])
    a.raw(b"\x8B\x0D" + u32(COMPS)).push(SERIE_A_ID).call(COMP_BY_ID)
    a.raw(b"\x8B\x74\x24\x2C\x0F\xB7\x4C\x24\x30\x31\xFF\x31\xD2")
    loop = len(a.code)
    a.raw(b"\x39\xCA")                                      # cmp edx, ecx
    jge_done = len(a.code); a.raw(b"\x7D\x00")
    a.raw(b"\x8B\x1C\x96\x85\xDB")                          # mov ebx, [esi+edx*4] ; test ebx, ebx
    je_skip = len(a.code); a.raw(b"\x74\x00")
    a.raw(b"\x39\x43\x54")                                  # cmp [ebx+0x54], eax (divisão)
    je_skip2 = len(a.code); a.raw(b"\x74\x00")
    a.raw(b"\x89\x1C\xBE\x47")                              # mov [esi+edi*4], ebx ; inc edi
    skip = len(a.code)
    a.raw(b"\x42")                                          # inc edx
    jmp_loop = len(a.code); a.raw(b"\xEB\x00")
    done = len(a.code)
    a.raw(b"\x66\x89\x7C\x24\x30\x61")                      # mov [esp+0x30], di ; popad
    a.push(1).push(-1).push(1).jmp(SELECTION + 0x151)        # instruções originais, volta em 0x00BB9581

    code = bytearray(a.code)        # posições acima já são relativas ao início de STUBS
    for at in (jne1, jne2):
        struct.pack_into("<i", code, at + 2, ret - (at + 6))
    for at, target in ((je_none, none), (je_free, free), (jge_done, done), (je_skip, skip),
                       (je_skip2, skip), (jmp_loop, loop)):
        rel = target - (at + 2)
        if not -128 <= rel <= 127:
            raise ValueError("copa do brasil: salto curto fora do alcance")
        code[at + 1] = rel & 0xFF
    return bytes(code), entry


def build(data: bytes):
    from .exe_patches import Swap

    stubs, entry = _stubs()
    s0, s1 = _stage1(data, entry["tail"]), _stage2(data, entry["draw"])
    if S0 + len(s0) > S1 or S1 + len(s1) > STUBS or len(stubs) > 0x400:
        raise ValueError("copa do brasil: código não cabe")

    def at(va: int) -> int:
        return off(va)

    swaps = list(section_swaps(data)) + [
        Swap(sec_off(S0), bytes(len(s0)), s0),
        Swap(sec_off(S1), bytes(len(s1)), s1),
        Swap(sec_off(STUBS), bytes(len(stubs)), stubs),
        Swap(sec_off(POSITIONS), bytes(len(_position_stubs()[0])), _position_stubs()[0]),
        Swap(off(CUP_VTABLE + 4 * 71), u32(BUILDER), u32(entry["dispatch"])),
        Swap(off(CUP_VTABLE + 4 * 72), u32(DEFAULT_NEXT_STAGE), u32(entry["next"])),
        Swap(at(SEASON_SETUP_STAGES), b"\x6A\x01", b"\x6A\x02"),              # 2 fases
        # temporada de janeiro a dezembro (construtor 0x00BB3100, +0x87 mês do fim; original
        # junho): com a final em dezembro e o fim em junho, o campeão de 2026 não entrou no
        # histórico (teste)
        Swap(at(0x00BB315F), bytes.fromhex("c68687000000" "05"), bytes.fromhex("c68687000000" "0b")),
        # participantes: 48, sem a Série A (filtro), completando com B, nova C e D
        Swap(at(0x00BB957B), data[at(0x00BB957B):at(0x00BB957B) + 5],
             b"\xE9" + u32(entry["filter"] - (0x00BB957B + 5))),
        Swap(at(0x00BB9504), bytes.fromhex("6683fa40"), bytes.fromhex("6683fa30")),
        Swap(at(0x00BB9581), b"\xB9" + u32(0x40), b"\xB9" + u32(STAGE1_TEAMS)),
        Swap(at(0x00BB95A2), b"\xB8" + u32(0x40), b"\xB8" + u32(STAGE1_TEAMS)),
        Swap(at(0x00BB95C3), b"\xBA" + u32(0x40), b"\xBA" + u32(STAGE1_TEAMS)),
        Swap(at(0x00BB95E1), bytes.fromhex("66837c241040"), bytes.fromhex("66837c241030")),
        Swap(at(0x00BB95F0), b"\xB9" + u32(0x40), b"\xB9" + u32(STAGE1_TEAMS)),
        Swap(at(0x00BB95FC), b"\xB8" + u32(0x40), b"\xB8" + u32(STAGE1_TEAMS)),
        Swap(at(0x00BB9592), b"\x68" + u32(SERIE_A_ID), b"\x68" + u32(SERIE_B_ID)),
        Swap(at(0x00BB95B3), b"\x68" + u32(SERIE_B_ID), b"\x68" + u32(NEW_C_ID)),
    ]
    assert data[at(0x00BB95D4):at(0x00BB95D4) + 5] == b"\x68" + u32(OLD_C_ID)
    return tuple(swaps)
