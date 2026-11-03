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
# 0xA23A70(código) diz se o código é atributo (1..20 e "No Mínimo/No Máximo" no filtro); código
# desconhecido vira condição de texto, que o filtro não testa. Pmcl passa por atributo.
IS_ATTRIBUTE = 0x00A23A70
IS_ATTRIBUTE_OLD = bytes.fromhex("8B442404 3D63656450")
MY_CLUB_YES, MY_CLUB_NO = 20, 1
# pré-filtro da Central: a busca de jogadores lê os ~18 mil conhecidos em 0xA6B1B0 e entrega cada
# um à tabela, que calcula todas as colunas. FORA DO PATCH: a busca leva ~0,01 s e a demora está na
# interface (suspeita: ndrq="true" no sections.xml; ver T1). Código guardado como referência.
# Um método do painel de busca que roda a cada abertura (0x8451C0; a montagem 0x8439C0 só roda uma vez por sessão) marca se a tela é a Central (id do
# painel em ecx+0x24, conferido na memória); no laço, com a marca, só passa quem é do clube do humano.
PANEL_SETUP, PANEL_SETUP_OLD, PANEL_ID = 0x008451C0, bytes.fromhex("6AFF684032DD00"), 0x24
CENTRO_ID = code("tcdv")
# 0x5247A9: lista de seções que o jogo trata à parte (tcdp, tcip e as da busca: srpl, srst, srsc,
# srsh) e que vão para 0x5247D7 (call 0xC6E3B0). Fora dela, voltar à Central com "Retornar" refazia
# a tela inteira (dezenas de segundos). Desvio: tcdv entra na lista (conferido na memória).
SECTION_LIST_AT, SECTION_LIST_OLD, SECTION_LIST_HIT = 0x005247A9, bytes.fromhex("3D70646374"), 0x005247D7
# Clique na Central abre o relatório (conferido na memória): ao sair de uma tela, 0x51A821 lê a
# seção dela ([tela+0x1AC]) para o histórico; o desvio a anota. Ao abrir qualquer tela, 0x4C3DD1 lê
# a seção já decidida; se for o Perfil (Pply) e a tela anterior era a Central, vira Ptra (Treino >
# Geral, o Relatório de Desenvolvimento). Tentativas sem efeito: 0x6AD649 e 0x500160 (não rodam no
# clique da lista) e uma marca nos eventos do painel (todos os painéis de busca recebem eventos).
LEAVE_AT, LEAVE_OLD = 0x0051A821, bytes.fromhex("8B86AC010000")          # mov eax, [esi+0x1AC]
OPEN_AT, OPEN_OLD = 0x004C3DD1, bytes.fromhex("8BBEAC010000")            # mov edi, [esi+0x1AC]
PROFILE, TRAINING = code("Pply"), code("Ptra")
# Filtro próprio da Central (conferido em 03/11, teste na memória tools/re/filtro_separado.py): a
# Central e Pesquisar > Jogadores usam o mesmo conjunto de busca (tipo 1), cujo filtro é o objeto em
# [conjunto+0x124]. Em 0x786F32 (pedido de busca, esi = conjuntos, [esi+8] = escolhido) o desvio
# troca esse ponteiro conforme a seção atual (tcdv ou outra) e zera [esi+0x41] para a busca ser
# refeita. Na 1ª troca o outro lado recebe um clone feito pelo jogo (nulo trava 0xCC4C40).
FILTER_AT, FILTER_OLD = 0x00786F32, bytes.fromhex("807E08FF7E6B")   # cmp byte [esi+8],-1 ; jle
FILTER_JLE_TO, FILTER_CREATE = 0x00786FA3, 0x00CC47F0
KNOWN_TEST, KNOWN_TEST_OLD = 0x00A6B2C4, bytes.fromhex("F6460C01757F")   # test [esi+0xC],1; jne próximo
KNOWN_KEEP, KNOWN_NEXT = 0x00A6B2CA, 0x00A6B349
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
    a.raw("B8").u32(MY_CLUB_YES).jump("E9", "grava")
    a.label("nao").raw("B8").u32(MY_CLUB_NO).jump("E9", "grava")
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


def attribute_code(base: int) -> bytes:
    """Em 0xA23A70 (é atributo?): Pmcl -> 1; os outros seguem o original."""
    a = _Code(base)
    a.raw("8B442404 3D").u32(MY_CLUB).jump("0F85", "outro").raw("B001 C3")
    a.label("outro").raw("3D63656450")
    _jmp_to(a, IS_ATTRIBUTE + 9)
    return a.done()


def panel_code(base: int, flag: int) -> bytes:
    """Em 0x8439C0: [flag] = 1 se o painel é a Central (tcdv), senão 0; refaz push -1/push e segue."""
    a = _Code(base)
    a.raw("50 31C0 8179").raw(bytes([PANEL_ID])).u32(CENTRO_ID).raw("0F94C0 A3").u32(flag).raw("58")
    a.raw(PANEL_SETUP_OLD)
    _jmp_to(a, PANEL_SETUP + len(PANEL_SETUP_OLD))
    return a.done()


def prefilter_code(base: int, flag: int, judges: int, cache: int) -> bytes:
    """Em 0xA6B2C4 (esi = item da lista de conhecidos, [esi] = pessoa): com a marca da Central,
    pula quem não é do clube do humano (time em pessoa+0x74, clube em time+0x38)."""
    a = _Code(base)
    a.raw("F6460C01").jump("0F85", "proximo")
    a.raw("833D").u32(flag).raw("00").jump("0F84", "fica")
    a.call(judges)                                                   # guarda o time do humano
    a.raw("8B15").u32(cache + 12).raw("85D2").jump("0F84", "fica")
    a.raw("8B06 85C0").jump("0F84", "proximo")
    a.raw("8B40").raw(bytes([PERSON_TEAM])).raw("85C0").jump("0F84", "proximo")
    a.raw("8B4038 3B4238").jump("0F85", "proximo")
    a.label("fica")
    _jmp_to(a, KNOWN_KEEP)
    a.label("proximo")
    _jmp_to(a, KNOWN_NEXT)
    return a.done()


def section_list_code(base: int) -> bytes:
    """Em 0x5247A9 (eax = seção): tcdv vai para o caminho das seções da busca; os outros seguem."""
    a = _Code(base)
    a.raw("3D").u32(CENTRO_ID)
    a.raw(bytes.fromhex("0F84") + (SECTION_LIST_HIT - (base + len(a.code) + 6)).to_bytes(4, "little", signed=True))
    a.raw(SECTION_LIST_OLD)
    _jmp_to(a, SECTION_LIST_AT + len(SECTION_LIST_OLD))
    return a.done()


def leave_code(base: int, last: int) -> bytes:
    """Em 0x51A821: anota a seção da tela que se deixa."""
    a = _Code(base)
    a.raw(LEAVE_OLD).raw("A3").u32(last)
    _jmp_to(a, LEAVE_AT + len(LEAVE_OLD))
    return a.done()


def open_code(base: int, last: int) -> bytes:
    """Em 0x4C3DD1 (edi = seção da tela que abre): Perfil vindo da Central vira Treino > Geral.
    Também anota a seção aberta em [last+4] e conta as aberturas em [last+8]: a Central externa
    (tools/central/servidor.py) lê os dois para abrir a página quando se entra na Central."""
    a = _Code(base)
    a.raw(OPEN_OLD).raw("81FF").u32(PROFILE).jump("0F85", "fim")
    a.raw("813D").u32(last).u32(CENTRO_ID).jump("0F85", "fim")
    a.raw("BF").u32(TRAINING).raw("89BEAC010000 C705").u32(last).u32(0)
    a.label("fim").raw("893D").u32(last + 4).raw("FF05").u32(last + 8)
    _jmp_to(a, OPEN_AT + len(OPEN_OLD))
    return a.done()


def filter_code(base: int, slots: int, section_now: int) -> bytes:
    """Em 0x786F32: filtro da Central separado do Pesquisar. slots: contêiner, filtro guardado,
    lado instalado (1 = Central), trocas, clones (5 dwords zerados). section_now: seção atual
    (gravada pelo desvio de abertura)."""
    def le(v: int) -> bytes:
        return (v & 0xFFFFFFFF).to_bytes(4, "little")
    c = bytearray()
    def rel(target: int, size: int) -> bytes:
        return le(target - (base + len(c) + size))
    c += b"\x60"                                             # pushad
    c += b"\xA1" + le(slots)                                  # mov eax, [CONT]
    c += b"\x39\xF0"                                         # cmp eax, esi
    c += b"\x74\x17"                                         # je mesmo (+23 = 6 + 10 + 7)
    c += b"\x89\x35" + le(slots)                              # mov [CONT], esi
    c += b"\xC7\x05" + le(slots + 4) + le(0)                     # mov [SAVED], 0
    c += b"\xC6\x05" + le(slots + 8) + b"\x01"               # mov byte [INSTALLED], 1 (o do save é da Central)
    c += b"\x0F\xBE\x46\x08"                                 # mesmo: movsx eax, byte [esi+8]
    c += b"\x85\xC0"                                         # test eax, eax
    fim_js = len(c); c += b"\x0F\x88" + le(0)                # js fim
    c += b"\x3A\x46\x14"                                     # cmp al, [esi+0x14]
    fim_jae = len(c); c += b"\x0F\x83" + le(0)               # jae fim
    c += b"\x8B\x4E\x10"                                     # mov ecx, [esi+0x10]  (dados da lista)
    c += b"\x8B\x1C\x81"                                     # mov ebx, [ecx+eax*4] (conjunto)
    c += b"\x85\xDB"                                         # test ebx, ebx
    fim_jz = len(c); c += b"\x0F\x84" + le(0)                # jz fim
    c += b"\x80\x7B\x05\x01"                                 # cmp byte [ebx+5], 1  (tipo jogadores)
    fim_jne = len(c); c += b"\x0F\x85" + le(0)               # jne fim
    c += b"\x31\xD2"                                         # xor edx, edx
    c += b"\x81\x3D" + le(section_now) + le(CENTRO_ID)            # cmp dword [SECTION_NOW], 'tcdv'
    c += b"\x0F\x94\xC2"                                     # sete dl
    c += b"\x3A\x15" + le(slots + 8)                         # cmp dl, [INSTALLED]
    fim_je = len(c); c += b"\x0F\x84" + le(0)                # je fim
    # primeira troca: o outro lado ainda não tem filtro. Nulo trava 0xCC4C40 (dump de 03/11), então
    # clona o atual como o jogo faz em 0xA6AEC4: fábrica = (f+4)->vfunc8; novo = 0xCC47F0(fábrica)-4;
    # novo->vfunc58(f) copia o conteúdo.
    c += b"\x83\x3D" + le(slots + 4) + b"\x00"                   # cmp dword [SAVED], 0
    troca_jne = len(c); c += b"\x0F\x85" + le(0)             # jne troca
    c += b"\x8B\x8B\x24\x01\x00\x00"                         # mov ecx, [ebx+0x124]   (f)
    c += b"\x85\xC9"                                         # test ecx, ecx
    fim_jz2 = len(c); c += b"\x0F\x84" + le(0)               # jz fim
    c += b"\x51"                                             # push ecx               (guarda f)
    c += b"\x83\xC1\x04"                                     # add ecx, 4
    c += b"\x8B\x01"                                         # mov eax, [ecx]
    c += b"\xFF\x50\x08"                                     # call [eax+8]           (fábrica)
    c += b"\x50"                                             # push eax
    c += b"\xE8" + rel(FILTER_CREATE, 5)                            # call 0xCC47F0
    c += b"\x83\xC4\x04"                                     # add esp, 4
    c += b"\x5A"                                             # pop edx                (f)
    c += b"\x85\xC0"                                         # test eax, eax
    fim_jz3 = len(c); c += b"\x0F\x84" + le(0)               # jz fim
    c += b"\x83\xE8\x04"                                     # sub eax, 4             (novo)
    c += b"\xA3" + le(slots + 4)                                 # mov [SAVED], eax
    c += b"\x52"                                             # push edx               (f)
    c += b"\x89\xC1"                                         # mov ecx, eax
    c += b"\x8B\x00"                                         # mov eax, [eax]
    c += b"\xFF\x50\x58"                                     # call [eax+0x58]        (novo.copia(f))
    c += b"\xFF\x05" + le(slots + 16)                            # inc dword [CLONES]
    troca = len(c)
    c += b"\x31\xD2"                                         # xor edx, edx  (dl de novo: as chamadas o perdem)
    c += b"\x81\x3D" + le(section_now) + le(CENTRO_ID)            # cmp dword [SECTION_NOW], 'tcdv'
    c += b"\x0F\x94\xC2"                                     # sete dl
    c[troca_jne + 2:troca_jne + 6] = le(troca - (troca_jne + 6))
    c += b"\x8B\x83\x24\x01\x00\x00"                         # mov eax, [ebx+0x124]
    c += b"\x8B\x0D" + le(slots + 4)                             # mov ecx, [SAVED]
    c += b"\x89\x8B\x24\x01\x00\x00"                         # mov [ebx+0x124], ecx
    c += b"\xA3" + le(slots + 4)                                 # mov [SAVED], eax
    c += b"\x88\x15" + le(slots + 8)                         # mov [INSTALLED], dl
    c += b"\xFF\x05" + le(slots + 12)                             # inc dword [SWAPS]
    # os resultados são do contêiner (lista em +0x2C): zera "resultados válidos" para 0x54B0A0 refazer
    # a busca com o filtro trocado, como o jogo faz ao trocar de conjunto (0x54AE61)
    c += b"\xC6\x46\x41\x00"                                 # mov byte [esi+0x41], 0
    fim = len(c)
    for at in (fim_js, fim_jae, fim_jz, fim_jne, fim_je, fim_jz2, fim_jz3):
        c[at + 2:at + 6] = le(fim - (at + 6))
    c += b"\x61"                                             # popad
    c += b"\x80\x7E\x08\xFF"                                 # cmp byte [esi+8], -1   (original)
    c += b"\x0F\x8E" + rel(FILTER_JLE_TO, 6)                        # jle 0x786FA3           (original)
    c += b"\xE9" + rel(FILTER_AT + len(FILTER_OLD), 5)                              # jmp 0x786F38
    return bytes(c)


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
    attribute_at = SECTION_VA + 0xD6E0
    section_list_at = SECTION_VA + 0xD700
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
    attribute = attribute_code(attribute_at)
    if attribute_at + len(attribute) > SECTION_VA + 0xD700:
        raise ValueError("centro: desvio de atributo passa de 0xD700")
    swaps.append(Swap(sec_off(attribute_at), bytes(len(attribute)), attribute))
    swaps.append(Swap(off(IS_ATTRIBUTE), IS_ATTRIBUTE_OLD, jump(IS_ATTRIBUTE, attribute_at) + bytes([0x90] * 4)))
    section_list = section_list_code(section_list_at)
    if section_list_at + len(section_list) > SECTION_VA + 0xD740:
        raise ValueError("centro: desvio da lista de seções passa de 0xD740")
    swaps.append(Swap(sec_off(section_list_at), bytes(len(section_list)), section_list))
    swaps.append(Swap(off(SECTION_LIST_AT), SECTION_LIST_OLD, jump(SECTION_LIST_AT, section_list_at)))
    leave_at, open_at, last_at = SECTION_VA + 0xD740, SECTION_VA + 0xD760, SECTION_VA + 0xD7F0
    leave, opening = leave_code(leave_at, last_at), open_code(open_at, last_at)
    if leave_at + len(leave) > open_at or open_at + len(opening) > last_at:
        raise ValueError("centro: desvios do clique invadem o vizinho")
    swaps += [Swap(sec_off(leave_at), bytes(len(leave)), leave), Swap(sec_off(open_at), bytes(len(opening)), opening)]
    swaps.append(Swap(off(LEAVE_AT), LEAVE_OLD, jump(LEAVE_AT, leave_at) + bytes([0x90])))
    swaps.append(Swap(off(OPEN_AT), OPEN_OLD, jump(OPEN_AT, open_at) + bytes([0x90])))
    filter_slots, filter_at = SECTION_VA + 0xDCC0, SECTION_VA + 0xDD00
    separate = filter_code(filter_at, filter_slots, last_at + 4)
    if filter_at + len(separate) > SECTION_VA + 0xDE00:
        raise ValueError("centro: desvio do filtro passa de 0xDE00")
    swaps.append(Swap(sec_off(filter_at), bytes(len(separate)), separate))
    swaps.append(Swap(off(FILTER_AT), FILTER_OLD, jump(FILTER_AT, filter_at) + bytes([0x90])))
    return tuple(swaps)
