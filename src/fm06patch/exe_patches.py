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
    # Troca usada por mais de um patch (ex.: ampliar a seção .text): se já
    # estiver aplicada, segue em frente.
    shared: bool = False


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


def _copa_swaps(data: bytes):
    from .copa_do_brasil import build

    return build(data)


def _libertadores_swaps(data: bytes):
    from .libertadores import build

    return build(data)


def _libertadores_datas_swaps(data: bytes):
    from .libertadores import build_dates

    return build_dates(data)


def _patrocinio_swaps(data: bytes):
    from .patrocinio import exe_swaps

    return exe_swaps(data)


def _ano_exibido_swaps(data: bytes):
    from .ano_exibido import build

    return build(data)


def _sul_americana_swaps(data: bytes):
    from .sul_americana import build

    return build(data)


def _estaduais_swaps(data: bytes):
    from .estaduais import build

    return build(data)


def _calendario_swaps(data: bytes):
    from .calendario import build

    return build(data)


def _serie_a_copa(window2_end):
    """Série A com pausa da Copa (teste). Janela 1 (0x00BBA531..0x00BBA569):
    as últimas N rodadas (word em +0x20 do modelo de datas); janela 2
    (0x00BBA56E..0x00BBA591): a temporada."""
    swaps = [
        _imm8(0x7BA536, b"\x6A", 7, 6),       # janela final, início: agosto -> julho
        _imm8(0x7BA538, b"\x6A", 6, 22),      # dia 22
        _imm8(0x7BA54C, b"\x6A", 10, 2),      # janela final, fim: 2/12
        Swap(0x7BA562, bytes.fromhex("66c744245c1a00"), bytes.fromhex("66c744245c1300")),  # 26 -> 19 rodadas
        _imm8(0x7BA573, b"\x6A", 3, 0),       # temporada, início: 28/1
        _imm8(0x7BA575, b"\x6A", 30, 28),
    ]
    if window2_end is None:
        swaps.append(_imm8(0x7BA589, b"\x6A", 10, 2))           # temporada, fim: 2/12
    else:
        day, month = window2_end
        swaps += [_imm8(0x7BA589, b"\x6A", 10, day), _imm8(0x7BA587, b"\x6A", 11, month)]
    return tuple(swaps)


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
            "4ª divisão: nova Série C (registro Taça de Prata 319191, índice 376) entre a B e a antiga C, "
            "que vira o 4º nível. 1ª fase: liga de 20 em turno único (5/4 a 23/8), 8 avançam, 2 caem; "
            "2ª fase: 2 grupos de 4, ida e volta (6/9 a 1/11), os 2 primeiros de cada grupo sobem. "
            "B cai para a nova C; antiga C sobe para a nova C. Acrescenta a seção .fm26 ao executável.",
            build=lambda data: _cave_swaps(data),
        ),
        Patch(
            "serie_b_playoffs",
            "Série B: 1º e 2º sobem direto; playoffs 3º×6º e 4º×5º, ida e volta (21/11 e 28/11), "
            "empate: passa a melhor campanha, sem prorrogação nem pênaltis; vencedores sobem. "
            "Cópia do playoff da Série B italiana (0x00C0FAC0). Não combina com serie_b_sobe_4.",
            build=lambda data: _playoff_swaps(data),
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
            "Série B de 21/3 a 15/11, fase de pontos corridos (original: 29/4 a 2/12), returno a partir de 15/7; "
            "os playoffs (serie_b_playoffs) vão até 28/11. Fase em 0x00BBA6A0.",
            (
                _imm8(0x7BA825, b"\x6A", 3, 2),       # mês de início: abril -> março
                _imm8(0x7BA827, b"\x6A", 0x1D, 21),   # dia de início
                _imm8(0x7BA7FC, b"\x6A", 0x0B, 10),   # mês de fim, 1º par: dezembro -> novembro
                _imm8(0x7BA7FE, b"\x6A", 2, 15),      # dia de fim, 1º par
                _imm8(0x7BA839, b"\x6A", 0x0B, 10),   # mês de fim, 2º par
                _imm8(0x7BA83B, b"\x6A", 2, 15),      # dia de fim, 2º par
                _imm8(0x7BA7E8, b"\x6A", 7, 6),       # início do 1º par (returno): agosto -> julho
                _imm8(0x7BA7EA, b"\x6A", 5, 15),      #          dia 5 -> 15
            ),
        ),
        Patch(
            "sul_americana_2026",
            "Sul-Americana com 28 clubes: Brasil 6 (sem quem está na Libertadores), Argentina 6, "
            "2 de cada outro país, sem México e EUA; montada em 25/1; 1ª fase 15/4 (países "
            "menores), 2ª fase 22/7, oitavas 12/8 (Argentina e Brasil entram), quartas 16/9, "
            "semifinal 21/10, final única 21/11. Ver src/fm06patch/sul_americana.py.",
            build=_sul_americana_swaps,
        ),
        Patch(
            "libertadores_vagas_2026",
            "Libertadores com as vagas de 2026, mantendo os 38 clubes do FM06: Brasil 5 -> 7, "
            "Argentina 5 -> 6, México 3 -> 0. A vaga do México na preliminar vai para a Argentina, "
            "o Brasil leva 6 aos grupos e os 2 brasileiros piores vão do pote 1 ao 2. "
            "Ver src/fm06patch/libertadores.py.",
            build=_libertadores_swaps,
        ),
        Patch(
            "libertadores_datas_2026",
            "Libertadores no calendário de 2026: preliminar 22/2 e 1/3; grupos em 6 rodadas de 5/4 a "
            "24/5; oitavas 9 e 16/8; quartas 13 e 20/9; semifinal 18 e 25/10; final em jogo único "
            "em 28/11 (original: grupos fev–abr, oitavas e quartas em maio, semi e final em "
            "junho/julho, final em dois jogos). Ver src/fm06patch/libertadores.py.",
            build=_libertadores_datas_swaps,
        ),
        Patch(
            "ano_exibido_mais_20",
            "Ano na tela + 20 (motor em 2005/06; temporada 2006 aparece como 2026): datas, nomes de "
            "temporada, históricos, prêmios, notícias e nomes de competição. Chaves de arquivo e "
            "save continuam com o ano do motor. Ver src/fm06patch/ano_exibido.py.",
            build=_ano_exibido_swaps,
        ),
        Patch(
            "copa_do_brasil_2026",
            "Copa do Brasil em duas fases: 48 clubes sem a Série A (11/3 e 18/3); depois os 12 "
            "classificados + os 20 da Série A da 5ª fase à final (22/4, 1/8, 26/8, 1/11, final 29/11 e 6/12; temporada até dezembro). "
            "Ver src/fm06patch/copa_do_brasil.py.",
            build=_copa_swaps,
        ),
        Patch(
            "copa_do_brasil_datas_2026",
            "Copa do Brasil (0x00BBAD30, mata-mata de 64 em 6 rodadas) nas datas de 2026, cada rodada "
            "na fase de 2026 com o mesmo número de clubes: 64 em 18/3 (4ª fase), 32 em 22/4 (5ª), "
            "16 em 1/8 (oitavas), 8 em 26/8 (quartas), 4 em 1/11 (semifinal), final em 29/11 e 6/12. "
            "Original: 2/2, 2/3, 30/3, 20/4, 25/5, 15/6.",
            tuple(
                swap
                for va_month, va_day, old_day, old_month, day, month in (
                    (0xBBAE15, 0xBBAE17, 2, 1, 18, 2),
                    (0xBBAE9F, 0xBBAEA1, 2, 2, 22, 3),
                    (0xBBAF16, 0xBBAF18, 30, 2, 1, 7),
                    (0xBBAF90, 0xBBAF92, 20, 3, 26, 7),
                    (0xBBAFF9, 0xBBAFFB, 25, 4, 1, 10),
                    (0xBBB06D, 0xBBB06F, 15, 5, 6, 11),
                )
                for swap in (
                    _imm8(va_month - 0x400000, b"\x6A", old_month, month),
                    _imm8(va_day - 0x400000, b"\x6A", old_day, day),
                )
            ),
        ),
        Patch(
            "estaduais_2026",
            "Estaduais de 2026: todos no estadual genérico, com o formato de 2026 por estado "
            "(clubes, grupos, turnos, classificados, rebaixados), de 11/1 a 8/3. "
            "Ver src/fm06patch/estaduais.py.",
            build=_estaduais_swaps,
        ),
        Patch(
            "serie_a_calendario_copa",
            "Série A de 28/1 a 2/12 com turno e returno de 19 rodadas. Ano de Copa (ano % 4 == 2): "
            "turno até 31/5, returno a partir de 22/7. Outros anos: turno até 14/6, returno a partir "
            "de 21/6. Substitui serie_a_datas_2026. Ver src/fm06patch/calendario.py.",
            build=_calendario_swaps,
        ),
        Patch(
            "exp_a_copa_1",
            "TESTE (alternativa a serie_a_datas_2026): Série A de 28/1 a 2/12 com a janela final "
            "(returno, 19 rodadas: campo 0x1A -> 0x13) começando em 22/7. Turno espalhado de 28/1 a 22/7.",
            _serie_a_copa(window2_end=None),
        ),
        Patch(
            "exp_a_copa_2",
            "TESTE (alternativa a serie_a_datas_2026): como exp_a_copa_1, e a janela da temporada "
            "termina em 31/5 (para ver se o turno fica antes da Copa).",
            _serie_a_copa(window2_end=(31, 4)),
        ),
        Patch(
            "virada_1_janeiro",
            "Temporada do Brasil vira em 1º/1 (original: 2/1). bra_get_settings chama "
            "0x00ACFFF0(dia, mês) em 0x00BB272F.",
            (_imm8(0x7B272F, b"\x6A", 2, 1),),
        ),
        Patch(
            "serie_d_96",
            "Série D (antiga C, 0x00BBFD00) com 96 clubes: 16 grupos de 6, avançam 2 por grupo; "
            "mata-mata de 32 e de 16; os 8 restantes jogam a fase final em turno único e os 6 primeiros "
            "sobem (original: 4 na fase final, 2 sobem). Grupos aos domingos de 2/4 a 28/5 e 10ª rodada na "
            "quarta 31/5; mata-mata 9/7 e 16/7, 19/7 e 23/7; fase final aos domingos de 30/7 a 10/9. "
            "Exige pelo menos 96 times, sem máximo. Não combina com serie_c_64_clubes.",
            (
                Swap(0x7BFDB7, bytes.fromhex("66c7008000"), bytes.fromhex("66c7006000")),  # total 128 -> 96
                Swap(0x7BFE9D, bytes.fromhex("c6460b08"), bytes.fromhex("c6460b06")),      # 8 -> 6 por grupo
                _zone(0x7C0573, PROMOTION, 2, 6),                                           # fase final: 6 sobem
                Swap(0x7C037C, bytes.fromhex("6a098d4c244c"), bytes.fromhex("e9d600000090")),  # sem a 3ª rodada
                _imm8(0x7C0479, b"\x6A", 9, 8),       # vencedores da 2ª rodada vão para a fase final
                Swap(0x7C04E0, bytes.fromhex("66c7000400"), bytes.fromhex("66c7000800")),  # fase final com 8
                Swap(0x7C054C, bytes.fromhex("c6460a02"), bytes.fromhex("c6460a01")),      # turno único
                Swap(0x7B286F, bytes.fromhex("6afe6880000000"), bytes.fromhex("6aff6860000000")),
                # datas (push mês, push dia; mês começa em 0). A fase de liga (0x00B0EE30) põe
                # primeiro uma rodada no domingo da semana do fim e depois as outras de 21 em 21
                # dias a partir do início (+0, +7, +14): com mais domingos do que rodadas, sobram
                # buracos de 2 e 3 semanas (teste: 2/4, 9/4, 23/4, 14/5...). A janela tem de ter
                # exatamente 9 domingos; a 10ª rodada é a data fixa de 0x00B0F650 (rodada final
                # simultânea, quarta), que continuava em 20/9.
                _imm8(0x7BFF53, b"\x6A", 5, 3),       # grupos, início (domingo): 25/6 -> 2/4
                _imm8(0x7BFF5C, b"\x6A", 0x19, 2),
                _imm8(0x7BFF90, b"\x6A", 8, 4),       # grupos, fim (quarta): 20/9 -> 31/5
                _imm8(0x7BFF92, b"\x6A", 0x14, 31),
                _imm8(0x7BFFE8, b"\x6A", 8, 4),       # 10ª rodada (quarta, 19h30): 20/9 -> 31/5
                _imm8(0x7BFFEA, b"\x6A", 0x14, 31),
                _imm8(0x7C01AE, b"\x6A", 8, 6),       # mata-mata, sorteio (quinta): 21/9 -> 6/7
                _imm8(0x7C01B0, b"\x6A", 0x15, 6),
                _imm8(0x7C01C8, b"\x6A", 8, 6),       # 1ª rodada (domingos): 24/9 -> 9/7 e 16/7
                _imm8(0x7C01CA, b"\x6A", 0x18, 9),
                _imm8(0x7C027A, b"\x6A", 9, 6),       # 2ª rodada (quarta e domingo): 4/10 -> 19/7 e 23/7
                _imm8(0x7C027C, b"\x6A", 4, 19),
                _imm8(0x7C03A1, b"\x6A", 9, 6),       # 3ª rodada (pulada): 15/10 -> 30/7
                _imm8(0x7C03A3, b"\x6A", 0x0F, 30),
                # fase final: 7 domingos de 30/7 a 10/9 (o domingo 23/7, antes do início, não vale)
                _imm8(0x7C05BA, b"\x6A", 9, 6),       # início (quarta): 25/10 -> 26/7
                _imm8(0x7C05BC, b"\x6A", 0x19, 26),
                _imm8(0x7C05DF, b"\x6A", 0x0A, 8),   # fim (domingo): 26/11 -> 10/9
                _imm8(0x7C05E1, b"\x6A", 0x1A, 10),
            ),
        ),
        Patch(
            "shortlist_sem_pessoa",
            "Lista de observados (SHORTLIST_MAN, 0x0078B840) aceita pessoa nula e devolve 0. Uma proposta "
            "com troca de jogadores (0x007E4085) pede a lista para uma pessoa que não foi achada e o jogo "
            "travava em junho (lendo [0+0x18]). Os 62 lugares que chamam já tratam o 0.",
            (
                # test edx,edx; mov eax,[esp+4]; mov eax,[eax+0x18]; jl fim
                # -> mov eax,[esp+4]; test eax,eax; je fim; mov eax,[eax+0x18]
                # (o jl só pegava contagem negativa, que o jge seguinte também recusa)
                Swap(0x38B84E, bytes.fromhex("85d28b4424048b40187c20"), bytes.fromhex("8b44240485c074238b4018")),
            ),
        ),
        Patch(
            "nascimento_lnc_fixo",
            "CHANGE_PLAYER_NAME (.lnc, executor 0x00AAA4B0) não sorteia mais o dia do nascimento: o jogo "
            "trocava o nome e gravava um dia diferente no mesmo ano (proteção para nomes fictícios), e "
            "os jogadores e a comissão de 2026 saíam com dia e mês errados. Fica a data do people_db "
            "(fm06patch.atributos_jogadores, aplicar_comissao.py). docs/reversing/rea-atributos.md.",
            (
                # call [edx+0x1A0] (grava a data; thiscall, desempilha o argumento)
                # -> add esp, 4 (descarta o argumento empilhado) + nop
                Swap(0x6AA645, bytes.fromhex("ff92a0010000"), bytes.fromhex("83c404909090")),
            ),
        ),
        Patch(
            "patrocinio_inicio",
            "Paga o patrocínio da 1ª temporada no New Game: o jogo só paga no fechamento do ano "
            "(método 0xF0 das finanças, 0x008AA580), já para a temporada seguinte. No init das "
            "finanças (0x00A87170) o teste do gerador do contrato (0x00A872E9) vai para um desvio que "
            "gera o contrato se faltar e paga o valor uma vez pelo método 0xA0 (0x00A7C8D0). Ver "
            "src/fm06patch/patrocinio.py e docs/analise/C1b.md.",
            build=_patrocinio_swaps,
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


def _playoff_swaps(data: bytes) -> tuple[Swap, ...]:
    from .exe_cave import build_playoff_swaps

    return build_playoff_swaps(data)


def apply(data: bytes, names: list[str]) -> bytes:
    out = bytearray(data)
    for name in names:
        if name not in PATCHES:
            raise KeyError(f"Patch desconhecido: {name}. Disponíveis: {', '.join(PATCHES)}")
        for swap in PATCHES[name].swaps_for(data):
            if swap.offset + len(swap.old) > len(out):        # seção nova no fim do arquivo
                out.extend(bytes(swap.offset + len(swap.old) - len(out)))
            current = bytes(out[swap.offset:swap.offset + len(swap.old)])
            if swap.shared and current == swap.new:
                continue
            if current != swap.old:
                raise ValueError(
                    f"{name}: em 0x{swap.offset:08X} esperava {swap.old.hex(' ')}, achei {current.hex(' ')}"
                )
            out[swap.offset:swap.offset + len(swap.new)] = swap.new
    return bytes(out)
