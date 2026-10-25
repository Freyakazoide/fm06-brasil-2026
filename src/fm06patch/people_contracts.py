"""Contrato dos jogadores no people_db.dat (clube atual) e índice dos clubes no server_db.

people_db (FM06 6.0.2):
- T3 (0x0480F422..0x05AFA48A, 89 bytes): u32 índice, u32 UID de cada jogador;
- o registro de cada pessoa termina com u16 ano (1900..2016), 00 00 00, u32
  índice, u32 UID;
- o contrato fica no fim do registro: 00, u32 índice do clube, u32, u16 dia do
  ano e u16 ano do fim do contrato, 02 00 00 00. Conferido: Rogério Ceni no 213
  (São Paulo) até 31/7/2008, Fred no 590 (Lyon) até 30/6/2009.

server_db: o clube é citado pelo índice; cada registro de clube termina com o
próprio (índice, UID verdadeiro), que é o começo do registro seguinte.
"""

from __future__ import annotations

import bisect
import re
import struct
from collections import Counter
from dataclasses import dataclass

from .server_teams import club_pairs

T3_START, T3_END, T3_SIZE = 0x0480F422, 0x05AFA48A, 89
PEOPLE_END = 0x043902BA                     # fim da tabela A (pessoas)
MAX_CLUB_INDEX = 30000                      # o maior clube do banco tem índice 19164
MAX_UID = 100_000_000
# fim do registro: u16 ano, 3 bytes, u32 índice, u32 UID (busca sobreposta: um falso fim logo
# antes não esconde o verdadeiro)
_TAIL = re.compile(rb"(?=[\x6c-\xe0]\x07...(....)(....))", re.S)
_TAIL_STRICT = re.compile(rb"[\x6c-\xe0]\x07\x00\x00\x00(....)(....)", re.S)    # nationalities()
# fim do contrato: 2005..2014, ou 1900 = sem data de fim (2.353 jogadores brasileiros do banco,
# quase todos das séries de baixo; no jogo aparecem com contrato normal)
_CONTRACT = re.compile(rb"(?=\x00(....)(....)(..)([\xd5-\xde]\x07|\x6c\x07)\x02\x00\x00\x00)", re.S)
_MAX_RECORD = 8000


@dataclass
class Contract:
    uid: int
    at: int          # posição do u32 índice do clube
    club: int        # índice do clube
    until: int       # ano do fim do contrato
    others: tuple[int, ...] = ()   # outros blocos do mesmo registro (empréstimo), com multi=True
    index: int = 0   # índice da pessoa (o do fim do registro; elenco_times)


def player_uids(people: bytes) -> set[int]:
    return {struct.unpack_from("<I", people, at + 4)[0] for at in range(T3_START, T3_END, T3_SIZE)}


def contracts(people: bytes, multi: bool = False) -> dict[int, Contract]:
    """UID -> contrato, só de quem tem exatamente um bloco de contrato no registro
    (multi=True: também quem tem vários; o primeiro vale, os outros vão em others).

    O bloco começa com 64, u32 índice da pessoa, 00 (antes do u32 do clube): ele é da pessoa
    desse índice, cujo registro termina no 1º fim (índice, UID) com esse índice depois do
    bloco. Até 25/10 o bloco ia para o registro entre dois "fins de registro", mas o padrão do
    fim aparece por acaso dentro dos registros (docs/reversing/rea-atributos.md): 2.682
    contratos de um bloco eram de outra pessoa, e o reforço trocava o clube de jogadores
    (Ribeiro na lista do Bragantino com contrato no Central e vice-versa)."""
    players = player_uids(people)
    ends: dict[int, list[tuple[int, int]]] = {}
    for match in _TAIL.finditer(people, 0, PEOPLE_END):
        index, uid = struct.unpack("<II", match.group(1) + match.group(2))
        if uid in players:
            ends.setdefault(index, []).append((match.start() + 13, uid))
    blocks: dict[int, list[tuple[int, re.Match]]] = {}
    for block in _CONTRACT.finditer(people, 0, PEOPLE_END):
        at = block.start() + 1
        if struct.unpack("<H", block.group(3))[0] > 365 or people[at - 6] != 0x64:
            continue
        owner = struct.unpack_from("<I", people, at - 5)[0]
        candidates = ends.get(owner, [])
        i = bisect.bisect_left(candidates, (at,))
        if i < len(candidates) and candidates[i][0] - at < _MAX_RECORD:
            blocks.setdefault(candidates[i][1], []).append((owner, block))
    found: dict[int, Contract] = {}
    for uid, mine in blocks.items():
        if len(mine) == 1 or multi:
            index, block = mine[0]
            found[uid] = Contract(uid, block.start() + 1, struct.unpack("<I", block.group(1))[0],
                                  struct.unpack("<H", block.group(4))[0],
                                  tuple(b.start() + 1 for _, b in mine[1:]), index)
    return found


def brazil_club_indexes(server: bytes) -> dict[int, int]:
    """UID verdadeiro -> índice, dos clubes brasileiros (server_teams.club_pairs).

    Fica de fora o par que não é de clube: UID 0, ou um "00 BD 00 00 00" achado por acaso
    que vira o "registro seguinte" (índice 48128, UID 923074816). Mandar jogador para um
    índice que não é clube deixa o contrato sem clube e o New Game trava (0x006CAFA7)."""
    indexes: dict[int, int] = {}
    for _, index, uid, _ in club_pairs(server):
        if 0 < uid < MAX_UID and 0 < index < MAX_CLUB_INDEX:
            indexes.setdefault(uid, index)
    return indexes


def team_field(people: bytes, contract_at: int, tables) -> int | None:
    """Posição do u32 "time" do registro da pessoa (comissao.py): o jogo põe a pessoa no
    time desse campo, que tem de bater com o clube do contrato (mudar só o contrato tira o
    jogador do clube antigo sem pô-lo no novo)."""
    from .comissao import _names_before

    names_at = _names_before(people, contract_at, tables)
    if names_at is None:
        return None
    size = struct.unpack_from("<I", people, names_at + 12)[0]
    return names_at + 16 + 2 * size + (2 if size else 0) + 26


def caps(people: bytes, contract_at: int, tables) -> int | None:
    """Jogos pela seleção (u32 depois de nação e seleção, 13 bytes depois do nascimento)."""
    at = team_field(people, contract_at, tables)
    return None if at is None else struct.unpack_from("<I", people, at - 26 + 13)[0]


def club_teams(server: bytes) -> dict[int, int]:
    """Índice do clube brasileiro -> valor do campo "time" do time dele (o registro do time
    no server_db cita o clube pelo UID do repositório: historico.team_index)."""
    indexes = set(brazil_club_indexes(server).values())
    out: dict[int, int] = {}
    for repo, index, _, _ in club_pairs(server):
        if index not in indexes or index in out:
            continue
        needle = struct.pack("<I", repo) + b"\x0a\x00"
        at = server.find(needle, 0xE00000, 0x1300000)
        if at >= 0:
            out[index] = struct.unpack_from("<I", server, at - 4)[0] + 1
    return out


def wrong_teams(people: bytes, found: dict[int, Contract], teams: dict[int, int], tables
                ) -> list[tuple[int, int, int]]:
    """(UID, posição do campo "time", time do clube do contrato) de quem tem contrato com um
    clube brasileiro e está no time de outro (nem do clube nem do empréstimo). O jogo lista o
    jogador no time do campo e mostra o clube do contrato: era o que uma versão antiga do
    reforço deixava (só o contrato mudava). No banco da SI são 0."""
    out = []
    for uid, contract in found.items():
        club = struct.unpack_from("<I", people, contract.at)[0]
        if club not in teams:
            continue
        at = team_field(people, contract.at, tables)
        if at is None:
            continue
        team = struct.unpack_from("<I", people, at)[0]
        loans = {teams.get(struct.unpack_from("<I", people, other)[0]) for other in contract.others}
        if team != teams[club] and team not in loans:
            out.append((uid, at, teams[club]))
    return out


def club_team_values(people: bytes, found: dict[int, Contract], clubs: set[int], tables,
                     sample: int = 5) -> dict[int, int]:
    """Índice do clube -> valor do campo "time" que os jogadores dele têm."""
    values: dict[int, Counter] = {}
    for contract in found.values():
        if contract.club not in clubs or sum(values.get(contract.club, Counter()).values()) >= sample:
            continue
        at = team_field(people, contract.at, tables)
        if at is not None:
            values.setdefault(contract.club, Counter())[struct.unpack_from("<I", people, at)[0]] += 1
    return {club: counter.most_common(1)[0][0] for club, counter in values.items()}


def move(people: bytes, moves: dict[int, int], found: dict[int, Contract], server: bytes | None = None,
         teams: dict[int, int] | None = None) -> tuple[bytes, list[int]]:
    """moves: UID do jogador -> índice do clube novo. Com server, grava também o campo "time"
    (teams: índice do clube -> valor; sem valor conhecido o jogador não muda). Devolve o
    arquivo e os UIDs que ficaram onde estavam."""
    out = bytearray(people)
    tables = None
    if server is not None:
        from .comissao import name_tables
        tables = name_tables(server)
    skipped = []
    for uid, club in moves.items():
        if tables is not None:
            at = team_field(people, found[uid].at, tables)
            if at is None or club not in (teams or {}):
                skipped.append(uid)
                continue
            struct.pack_into("<I", out, at, teams[club])
        for at in (found[uid].at,) + found[uid].others:
            struct.pack_into("<I", out, at, club)
    return bytes(out), skipped


# Código da nação no people_db (byte depois do ano de nascimento, após o nome completo).
NATION_CODES = {
    "Argentina": 0xBB, "Bolívia": 0xBC, "Brasil": 0xBD, "Chile": 0xBE, "Colômbia": 0xBF, "Equador": 0xC0,
    "Paraguai": 0xC1, "Peru": 0xC2, "Uruguai": 0xC3, "Venezuela": 0xC4, "Portugal": 0xA2, "Espanha": 0xAA,
    "França": 0x8F, "Inglaterra": 0x8B, "Holanda": 0x9E, "Suécia": 0xAB, "Dinamarca": 0x8A, "Croácia": 0x87,
    "Bulgária": 0x86, "Camarões": 0x06, "Nigéria": 0x21, "Gana": 0x10, "Senegal": 0x24,
    "Costa do Marfim": 0x13, "Marrocos": 0x1D, "Angola": 0x01, "Guiné": 0x11, "RD Congo": 0x30,
    "México": 0x6D, "Panamá": 0x70, "Estados Unidos": 0x78, "Moçambique": 0x1E, "Mali": 0x1A,
    # conferidos pelos sobrenomes de cada nação na tabela de nomes do server_db (Rossi, Kim, Al-Harbi...)
    "Itália": 0x96, "Cabo Verde": 0x07, "Serbia": 0xB0, "South Africa": 0x28, "Coreia do Sul": 0x50,
    "Guatemala": 0x68, "Guiné-Bissau": 0x12, "Japão": 0x3D, "Arábia Saudita": 0x4E, "Palestine": 0xC5,
    "Haiti": 0x6A, "Fiji": 0xB3, "Azerbaijão": 0x82, "Anguila": 0xCC,
}
_NAME = re.compile(rb"[\x03-\x28]\x00\x00\x00")


def nationalities(people: bytes) -> dict[int, list[tuple[int, int]]]:
    """Código da nação -> [(UID, ano de nascimento)] das pessoas com nome completo no registro
    (u32 tamanho, nome, 00 00, u16, u16 ano, u8, u32 nação; o registro termina em (índice, UID))."""
    found: dict[int, list[tuple[int, int]]] = {}
    for match in _NAME.finditer(people, 0, PEOPLE_END):
        start = match.start()
        end = start + 4 + 2 * people[start]
        if people[end:end + 2] != b"\0\0":
            continue
        try:
            name = people[start + 4:end].decode("utf-16-le")
        except UnicodeDecodeError:
            continue
        if not name.replace(" ", "").replace("-", "").replace("'", "").replace(".", "").isalpha():
            continue
        end += 2
        year = struct.unpack_from("<H", people, end + 2)[0]
        nation = struct.unpack_from("<I", people, end + 5)[0]
        if not (1940 <= year <= 1995 and nation < 400):
            continue
        for tail in _TAIL_STRICT.finditer(people, end, end + 0x400):
            index, uid = struct.unpack("<II", tail.group(1) + tail.group(2))
            if people.find(struct.pack("<I", index), end, tail.start()) >= 0:
                found.setdefault(nation, []).append((uid, year))
                break
    return found
