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

import re
import struct
from dataclasses import dataclass

from .server_teams import _CLUB_TAIL, _DATES

T3_START, T3_END, T3_SIZE = 0x0480F422, 0x05AFA48A, 89
PEOPLE_END = 0x043902BA                     # fim da tabela A (pessoas)
_TAIL = re.compile(rb"[\x6c-\xe0]\x07\x00\x00\x00(....)(....)", re.S)
_CONTRACT = re.compile(rb"\x00(....)(....)(..)([\xd5-\xde]\x07)\x02\x00\x00\x00", re.S)


@dataclass
class Contract:
    uid: int
    at: int          # posição do u32 índice do clube
    club: int        # índice do clube
    until: int       # ano do fim do contrato
    others: tuple[int, ...] = ()   # outros blocos do mesmo registro (empréstimo), com multi=True


def player_uids(people: bytes) -> set[int]:
    return {struct.unpack_from("<I", people, at + 4)[0] for at in range(T3_START, T3_END, T3_SIZE)}


def contracts(people: bytes, multi: bool = False) -> dict[int, Contract]:
    """UID -> contrato, só de quem tem exatamente um bloco de contrato no registro
    (multi=True: também quem tem vários; o primeiro vale, os outros vão em others)."""
    players = player_uids(people)
    found: dict[int, Contract] = {}
    previous = 0
    for match in _TAIL.finditer(people, 0, PEOPLE_END):
        _, uid = struct.unpack("<II", match.group(1) + match.group(2))
        if uid not in players:
            continue
        blocks = [b for b in _CONTRACT.finditer(people, previous, match.start())
                  if struct.unpack("<H", b.group(3))[0] <= 365]
        if blocks and (len(blocks) == 1 or multi) and uid not in found:
            block = blocks[0]
            found[uid] = Contract(uid, block.start() + 1, struct.unpack("<I", block.group(1))[0],
                                  struct.unpack("<H", block.group(4))[0], tuple(b.start() + 1 for b in blocks[1:]))
        previous = match.end()
    return found


def brazil_club_indexes(server: bytes) -> dict[int, int]:
    """UID verdadeiro -> índice, dos clubes brasileiros (como server_teams.true_uids)."""
    starts = [m.start() - 4 for m in re.finditer(re.escape(_CLUB_TAIL), server) if m.start() >= 8]
    indexes: dict[int, int] = {}
    for start, following in zip(starts, starts[1:] + [len(server)]):
        mark = server.find(_DATES, start, min(start + 0x600, following))
        if mark < 0:
            continue
        own = struct.unpack_from("<I", server, start - 4)[0] + 1
        if following - start <= 0x2000:
            index, uid = struct.unpack_from("<II", server, following - 4)
            indexes.setdefault(uid, index)
            continue
        at = server.find(struct.pack("<I", own), mark, start + 0x2000)
        if at > 0:
            indexes.setdefault(struct.unpack_from("<I", server, at + 4)[0], own)
    return indexes


def move(people: bytes, moves: dict[int, int], found: dict[int, Contract]) -> bytes:
    """moves: UID do jogador -> índice do clube novo."""
    out = bytearray(people)
    for uid, club in moves.items():
        for at in (found[uid].at,) + found[uid].others:
            struct.pack_into("<I", out, at, club)
    return bytes(out)


# Código da nação no people_db (byte depois do ano de nascimento, após o nome completo).
NATION_CODES = {
    "Argentina": 0xBB, "Bolívia": 0xBC, "Brasil": 0xBD, "Chile": 0xBE, "Colômbia": 0xBF, "Equador": 0xC0,
    "Paraguai": 0xC1, "Peru": 0xC2, "Uruguai": 0xC3, "Venezuela": 0xC4, "Portugal": 0xA2, "Espanha": 0xAA,
    "França": 0x8F, "Inglaterra": 0x8B, "Holanda": 0x9E, "Suécia": 0xAB, "Dinamarca": 0x8A, "Croácia": 0x87,
    "Bulgária": 0x86, "Camarões": 0x06, "Nigéria": 0x21, "Gana": 0x10, "Senegal": 0x24,
    "Costa do Marfim": 0x13, "Marrocos": 0x1D, "Angola": 0x01, "Guiné": 0x11, "RD Congo": 0x30,
    "México": 0x6D, "Panamá": 0x70, "Estados Unidos": 0x78, "Moçambique": 0x1E, "Mali": 0x1A,
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
        for tail in _TAIL.finditer(people, end, end + 0x400):
            index, uid = struct.unpack("<II", tail.group(1) + tail.group(2))
            if people.find(struct.pack("<I", index), end, tail.start()) >= 0:
                found.setdefault(nation, []).append((uid, year))
                break
    return found
