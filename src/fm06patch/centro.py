"""Centro de Desenvolvimento: colunas de estrelas da comissão (ficha T1).

Toda lista de jogadores pergunta o valor de cada coluna ao próprio jogador:
ACTUAL_PLAYER::propriedade(código, saída) (0x00A40D20), chamada pela interface em jogador+4
(vtable 0x010F1020, método 1 = 0x00A47530). O desvio troca esse ponteiro e responde os códigos
do mod; os outros seguem para o original:

- "Pest" / "Pesp": estrelas de 0 a 10 da habilidade atual e do potencial, na opinião da comissão
  do clube do jogador humano;
- "PCAB" / "PPAB": o CA e o PA de verdade (as colunas que o jogo deixava vazias);
- "Pmcl": 1 se o jogador é do clube do humano (qualquer time: principal, B, Sub-20), 0 se não.
  É a condição "Meu clube" do filtro da busca: o menu de condições (0x007EF780) ganha o item
  (desvio em 0x7EF8CA) e o rótulo (0x00A228B0, que dava "invalid" a código desconhecido em
  0xA239F9) passa a dizer "Meu clube".

A comissão: o staff (ACTUAL_NON_PLAYER, vtable 0x010F851C na tabela de pessoas) do mesmo time do
humano (HUMAN_NON_PLAYER, vtable 0x010F6F8C; time em pessoa+0x74) com função (propriedade
"Pcjo") 20 (adjunto) ou 14 (olheiro). Vale a maior "Npja" (Avaliação Capacidade Jogador) e a
maior "Npjp" (Avaliação Potencial Jogador). A conta é feita uma vez por dia de jogo.

Estrela: décimos = CA (ou PA) / 2, mais um erro fixo por jogador (sorteado pelo UID) de no máximo
(21 - nota) * 3 / 2 décimos (nota 20: +-0,15 estrela; nota 1: +-3 estrelas); arredonda para a
estrela inteira, entre 0 e 10.
"""

from __future__ import annotations

from .fornada import _Code

PROPERTY_SLOT, PROPERTY = 0x010F1024, 0x00A47530
VALUE_FROM_INT, VALUE_COPY, VALUE_FREE = 0x00C74B10, 0x00C72670, 0x00C72650
PEOPLE = 0x014EAA54
HUMAN_VTABLE, STAFF_VTABLE, PERSON_TEAM = 0x010F6F8C, 0x010F851C, 0x74
TODAY_DAY, TODAY_YEAR = 0x014EAB38, 0x014EAB3A
JOB_ASSISTANT, JOB_SCOUT = 20, 14
DEFAULT_JUDGE = 10                                   # sem humano (ou sem comissão achada)


def code(text: str) -> int:
    return int.from_bytes(text.encode(), "big")


STAR_NOW, STAR_POTENTIAL, CA, PA = code("Pest"), code("Pesp"), code("PCAB"), code("PPAB")
MY_CLUB = code("Pmcl")
PLAYER_TEAM, TEAM_CLUB = 0x70, 0x38                 # time em ecx + 0x70 (jogador + 0x74); clube no TEAM
LABEL_DEFAULT, LABEL_SET_RAW, LABEL_DEFAULT_TEXT = 0x00A239F9, 0x00C52100, 0x0109E01C
MENU_AT, MENU_ITEM, MENU_ADD = 0x007EF8CA, 0x007F16A0, 0x00CBEEE0
MY_CLUB_LABEL = b"Meu clube\0"
JOB, JUDGE_ABILITY, JUDGE_POTENTIAL = code("Pcjo"), code("Npja"), code("Npjp")
CA_AT, PA_AT, UID_AT = -0xBC, -0xBA, 0x10           # a partir de ecx = jogador + 4


def _jmp_to(a: _Code, target: int) -> None:
    a.raw(b"\xE9" + (target - (a.base + len(a.code) + 5)).to_bytes(4, "little", signed=True))


def property_helper(base: int) -> bytes:
    """stdcall(pessoa, código) -> o número da propriedade."""
    a = _Code(base)
    a.raw("83EC08 31C0 890424 89442404")                 # valor vazio em [esp]
    a.raw("54 FF742414")                                 # push &valor; push código
    a.raw("8B4C2414 83C104 8B01 FF5004")                 # ecx = pessoa + 4; call [[ecx]+4]
    a.raw("8B0424 83C408 C20800")
    return a.done()


def judges_code(base: int, helper: int, cache: int) -> bytes:
    """eax = melhor Npja, edx = melhor Npjp da comissão do humano. Cache por dia em ``cache``:
    +0 chave (ano * 416 + dia + 1), +4 Npja, +8 Npjp, +12 time do humano."""
    a = _Code(base)
    a.raw("53 56 57 55")
    a.raw("0FB705").u32(TODAY_YEAR).raw("69C0A0010000 0FB70D").u32(TODAY_DAY).raw("8D440801")
    a.raw("3B05").u32(cache).jump("0F84", "pronto")
    a.raw("A3").u32(cache)
    a.raw("C705").u32(cache + 4).u32(DEFAULT_JUDGE).raw("C705").u32(cache + 8).u32(DEFAULT_JUDGE)
    a.raw("A1").u32(PEOPLE).raw("8B4004 8B6808 8B7804")              # ebp = quantos, edi = itens
    a.raw("31F6")                                                    # o humano e o time dele
    a.label("humano").raw("3BF5").jump("0F8D", "pronto")
    a.raw("8B1CB7 85DB").jump("0F84", "h_prox")
    a.raw("813B").u32(HUMAN_VTABLE).jump("0F84", "achou")
    a.label("h_prox").raw("46").jump("E9", "humano")
    a.label("achou").raw("8B5B").raw(bytes([PERSON_TEAM]))           # ebx = time do humano
    a.raw("891D").u32(cache + 12)
    a.raw("C705").u32(cache + 4).u32(0).raw("C705").u32(cache + 8).u32(0)
    a.raw("31F6")
    a.label("staff").raw("3BF5").jump("0F8D", "pronto")
    a.raw("8B04B7 85C0").jump("0F84", "s_prox")
    a.raw("8138").u32(STAFF_VTABLE).jump("0F85", "s_prox")
    a.raw("3958").raw(bytes([PERSON_TEAM])).jump("0F85", "s_prox")  # mesmo time
    a.raw("50 68").u32(JOB).raw("50").call(helper)                   # pessoa salva em [esp]
    a.raw("83F8").raw(bytes([JOB_ASSISTANT])).jump("0F84", "avaliador")
    a.raw("83F8").raw(bytes([JOB_SCOUT])).jump("0F84", "avaliador")
    a.jump("E9", "s_fim")
    a.label("avaliador").raw("8B0424 68").u32(JUDGE_ABILITY).raw("50").call(helper)
    a.raw("3B05").u32(cache + 4).jump("0F8E", "pot").raw("A3").u32(cache + 4)
    a.label("pot").raw("8B0424 68").u32(JUDGE_POTENTIAL).raw("50").call(helper)
    a.raw("3B05").u32(cache + 8).jump("0F8E", "s_fim").raw("A3").u32(cache + 8)
    a.label("s_fim").raw("83C404")
    a.label("s_prox").raw("46").jump("E9", "staff")
    a.label("pronto").raw("A1").u32(cache + 4).raw("8B15").u32(cache + 8)
    a.raw("5D 5F 5E 5B C3")
    return a.done()


def hook_code(base: int, judges: int, cache: int) -> bytes:
    """O novo método 1 da vtable 0x010F1020 (this = jogador + 4; (código, saída), ret 8)."""
    a = _Code(base)
    a.raw("8B442404")
    a.raw("3D").u32(MY_CLUB).jump("0F84", "meu")
    a.raw("3D").u32(STAR_NOW).jump("0F84", "est_ca")
    a.raw("3D").u32(STAR_POTENTIAL).jump("0F84", "est_pa")
    a.raw("3D").u32(CA).jump("0F84", "ca")
    a.raw("3D").u32(PA).jump("0F84", "pa")
    _jmp_to(a, PROPERTY)                                             # os outros: o original
    a.label("ca").raw("0FB781").u32(CA_AT).jump("E9", "grava")
    a.label("pa").raw("0FB781").u32(PA_AT).jump("E9", "grava")
    for name, value_at, salt, take in (("est_ca", CA_AT, 0x2545F491, "8BD8"),   # ebx = Npja
                                       ("est_pa", PA_AT, 0x9E3779B9, "8BDA")):  # ebx = Npjp
        a.label(name).raw("53 56 57 51").call(judges).raw(take)
        a.raw("8B0C24")                                              # ecx = jogador + 4
        a.raw("83FB01").jump("0F8D", f"{name}_n").raw("BB01000000")
        a.label(f"{name}_n").raw("B815000000 2BC3 8D0440 D1E8 8BD8")  # ebx = (21 - nota) * 3 / 2
        a.raw("8D7C1B01")                                            # edi = 2 * ebx + 1
        a.raw("8B41").raw(bytes([UID_AT])).raw("35").u32(salt).raw("69C0").u32(0x9E3779B1)
        a.raw("C1E808 31D2 F7F7 2BD3")                               # edx = hash % edi - ebx
        a.raw("0FB781").u32(value_at).raw("D1E8 03C2")               # décimos = valor / 2 + erro
        a.raw("85C0").jump("0F8D", f"{name}_0").raw("31C0")
        a.label(f"{name}_0").raw("83F864").jump("0F8E", f"{name}_10").raw("B864000000")
        a.label(f"{name}_10").raw("83C005 31D2 B90A000000 F7F1")     # estrelas = (décimos + 5) / 10
        a.raw("59 5F 5E 5B").jump("E9", "grava")
    # meu clube: clube do time do jogador == clube do time do humano
    a.label("meu").raw("51").call(judges).raw("59")
    a.raw("8B15").u32(cache + 12).raw("85D2").jump("0F84", "nao")
    a.raw("8B4170 85C0").jump("0F84", "nao")
    a.raw("8B4038 3B4238").jump("0F85", "nao")
    a.raw("B801000000").jump("E9", "grava")
    a.label("nao").raw("31C0").jump("E9", "grava")
    a.label("grava").raw("83EC10 50 8D4C2404").call(VALUE_FROM_INT)
    a.raw("8B4C2418 8D0424 50").call(VALUE_COPY)
    a.raw("8D0C24").call(VALUE_FREE)
    a.raw("83C410 B001 C20800")
    return a.done()


def label_code(base: int, text_at: int) -> bytes:
    """No ramo "invalid" de 0xA228B0 (código em [esp+0x24]): Pmcl -> "Meu clube"."""
    a = _Code(base)
    a.raw("817C2424").u32(MY_CLUB).jump("0F85", "outro")
    a.raw("68").u32(text_at)
    _jmp_to(a, LABEL_DEFAULT + 5)
    a.label("outro").raw("68").u32(LABEL_DEFAULT_TEXT)
    _jmp_to(a, LABEL_DEFAULT + 5)
    return a.done()


def menu_code(base: int) -> bytes:
    """Em 0x7EF8CA (lista de condições de jogador): acrescenta Pmcl e refaz o que foi trocado
    (lea ecx, [esp+0x28]; push ecx) antes de seguir com Piap."""
    a = _Code(base)
    a.raw("8D4C2428 51 68").u32(MY_CLUB).call(MENU_ITEM).raw("83C408")
    a.raw("8B4E30 8D542428 52").call(MENU_ADD)
    a.raw("8D4C2428 51")
    _jmp_to(a, MENU_AT + 5)
    return a.done()


def build(hook_at: int, judges_at: int, helper_at: int, cache_at: int) -> list[tuple[int, bytes]]:
    return [(hook_at, hook_code(hook_at, judges_at, cache_at)),
            (judges_at, judges_code(judges_at, helper_at, cache_at)),
            (helper_at, property_helper(helper_at))]


def exe_swaps(data: bytes):
    from .exe_cave import SECTION_VA, off, sec_off, section_swaps
    from .exe_patches import Swap

    hook_at, judges_at, helper_at = SECTION_VA + 0xD200, SECTION_VA + 0xD400, SECTION_VA + 0xD580
    cache_at = SECTION_VA + 0xD5F0                                      # cache: 4 dwords zerados
    label_at, menu_at, text_at = SECTION_VA + 0xD600, SECTION_VA + 0xD640, SECTION_VA + 0xD6C0
    parts = build(hook_at, judges_at, helper_at, cache_at)
    for (start, code_bytes), end in zip(parts, (judges_at, helper_at, cache_at)):
        if start + len(code_bytes) > end:
            raise ValueError(f"centro: código em 0x{start:X} invade 0x{end:X}")
    swaps = list(section_swaps(data))
    swaps += [Swap(sec_off(start), bytes(len(code_bytes)), code_bytes) for start, code_bytes in parts]
    swaps.append(Swap(off(PROPERTY_SLOT), PROPERTY.to_bytes(4, "little"), hook_at.to_bytes(4, "little")))
    label, menu = label_code(label_at, text_at), menu_code(menu_at)
    if label_at + len(label) > menu_at or menu_at + len(menu) > text_at:
        raise ValueError("centro: rótulo ou menu invadem o vizinho")
    swaps += [Swap(sec_off(label_at), bytes(len(label)), label), Swap(sec_off(menu_at), bytes(len(menu)), menu),
              Swap(sec_off(text_at), bytes(len(MY_CLUB_LABEL)), MY_CLUB_LABEL)]
    jump = lambda at, target: bytes([0xE9]) + (target - (at + 5)).to_bytes(4, "little", signed=True)
    swaps.append(Swap(off(LABEL_DEFAULT), bytes([0x68]) + LABEL_DEFAULT_TEXT.to_bytes(4, "little"),
                      jump(LABEL_DEFAULT, label_at)))
    swaps.append(Swap(off(MENU_AT), bytes.fromhex("8D4C242851"), jump(MENU_AT, menu_at)))
    return tuple(swaps)
