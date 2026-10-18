"""Campeões anteriores (COMP_HISTORY) no server_db.dat.

Lista do banco (DB+0x88, leitor 0x00A0AE50; registro COMP_HISTORY, leitor 0x00AA6BC0):
u32 quantidade e registros de 39 bytes:
    +0  u8  tipo (0)
    +1  u32 competição (índice da tabela de competições do banco)
    +5  u16 ano
    +7  u32 campeão   (índice do time na lista de times; FFFFFFFF = nenhum)
    +11 u32 vice
    +15 u32 3º
    +19..+30 três referências (FFFFFFFF nas temporadas recentes)
    +31 u32 índice do registro, +35 u32 UID do registro
Todo registro de lista do banco termina com (índice, UID) dele mesmo: o par que
server_teams lê antes do "0A 00" é o fim do registro anterior. Índice do time =
u32 antes desse "UID" + 1.

O campeão anterior de cada competição (competição+0x1C, usado pela Libertadores
para o campeão da Libertadores e o da Copa do Brasil) é o registro de ano mais
alto (0x00AFD370). Os campeões reais de 2025 entram como o ano 2005 do motor
(ano exibido + 20). Sem inserir registros (o arquivo fica do mesmo tamanho):
Libertadores e Copa do Brasil já têm 2005; a Série A reaproveita o registro
mais antigo. A Sul-Americana 2005 é jogada pelo próprio jogo antes do primeiro
dia do jogador (ver CHAMPIONS_2025).

Vaga continental pré-definida: o registro do time tem, 33 bytes depois do
"0A 00", o índice da competição continental em que ele já entra
(FFFFFFFF = nenhuma). A Libertadores (0x00C06440) põe esses clubes antes de
olhar a tabela. No banco original só o Paulista (Copa do Brasil 2005) tem a
vaga; com ela o Paulista jogava a Libertadores de 2026.
"""

from __future__ import annotations

import struct

RECORD = 39
NONE = 0xFFFFFFFF
LIBERTADORES, SUL_AMERICANA, COPA_DO_BRASIL, SERIE_A = 0x1900F, 0x4D87F, 0x1901B, 0x19017
LAST_YEAR = 2005                  # 2025 na tela
CONTINENTAL_FIELD = 33

# competição: (campeão, vice) pelo UID do server_teams (convenção do repositório)
CHAMPIONS_2025 = {
    LIBERTADORES: (321, 328),     # Flamengo x Palmeiras
    # Sul-Americana fica de fora: a de 2005 do motor (agosto a novembro) é jogada entre o
    # início do New Game (julho de 2005) e o primeiro dia do jogador, e o campeão simulado
    # entra no histórico; gravar o Lanús deixava dois campeões de 2025 (teste).
    COPA_DO_BRASIL: (317, 338),   # Corinthians x Vasco
    SERIE_A: (321, 328),          # Flamengo campeão, Palmeiras vice (classificação 2025)
}


def find_list(data: bytes) -> int:
    """Posição do u32 com a quantidade de registros da lista de campeões."""
    at = 0
    one = struct.pack("<I", 1)
    while True:
        at = data.find(one, at)
        if at < 0:
            raise ValueError("lista de campeões não encontrada no banco")
        first = at - 31 - RECORD
        if first > 4 and data[first] == 0 and data[first + RECORD] == 0 \
                and struct.unpack_from("<I", data, first + 31)[0] == 0:
            count = struct.unpack_from("<I", data, first - 4)[0]
            if 1000 < count < 100000 and all(
                    data[first + RECORD * k] == 0
                    and struct.unpack_from("<I", data, first + RECORD * k + 31)[0] == k
                    and 1800 <= struct.unpack_from("<H", data, first + RECORD * k + 5)[0] <= 2100
                    for k in (0, 1, 2, count // 2, count - 1)):
                return first - 4
        at += 1


def records(data: bytes, start: int):
    for k in range(struct.unpack_from("<I", data, start)[0]):
        at = start + 4 + RECORD * k
        yield at, data[at + 1:at + 5], struct.unpack_from("<IHII", data, at + 1)


def team_index(data: bytes, uid: int) -> int:
    needle = struct.pack("<I", uid) + b"\x0a\x00"
    at = data.find(needle, 0xE00000, 0x1300000)
    if at < 0 or data.find(needle, at + 1, 0x1300000) >= 0:
        raise ValueError(f"time do clube {uid} não encontrado (ou repetido) no banco")
    return struct.unpack_from("<I", data, at - 4)[0] + 1


def comp_index(data: bytes, comp_id: int) -> int:
    at = data.find(struct.pack("<I", comp_id), 0x5B85C0, 0x5C0000)
    return struct.unpack_from("<I", data, at - 4)[0]


def apply(data: bytes, champions: dict[int, tuple[int, int]] = CHAMPIONS_2025) -> tuple[bytes, list[str]]:
    out = bytearray(data)
    start = find_list(data)
    notes = []
    for comp_id, (winner_uid, runner_uid) in champions.items():
        comp = comp_index(data, comp_id)
        mine = [(at, year) for at, _, (c, year, _w, _r) in records(data, start) if c == comp]
        same = [at for at, year in mine if year == LAST_YEAR]
        if same:
            at = same[0]
        else:
            at, oldest = min(mine, key=lambda r: r[1])
            struct.pack_into("<H", out, at + 5, LAST_YEAR)
            struct.pack_into("<I", out, at + 15, NONE)          # 3º do ano antigo não vale mais
            notes.append(f"competição {comp_id:#x}: registro de {oldest} vira {LAST_YEAR}")
        struct.pack_into("<II", out, at + 7, team_index(data, winner_uid), team_index(data, runner_uid))
    return bytes(out), notes


def clear_brazil_continental(data: bytes) -> tuple[bytes, list[str]]:
    """Tira dos clubes brasileiros a vaga continental pré-definida do banco."""
    from .estaduais_clubes import state_teams

    out = bytearray(data)
    cleared = []
    for team in state_teams(data):
        at = team.offset + CONTINENTAL_FIELD
        if struct.unpack_from("<I", data, at)[0] != NONE:
            struct.pack_into("<I", out, at, NONE)
            cleared.append(team.short_name or str(team.club_uid))
    return bytes(out), cleared
