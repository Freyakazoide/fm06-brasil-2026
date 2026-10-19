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


def player_uids(people: bytes) -> set[int]:
    return {struct.unpack_from("<I", people, at + 4)[0] for at in range(T3_START, T3_END, T3_SIZE)}


def contracts(people: bytes) -> dict[int, Contract]:
    """UID -> contrato, só de quem tem exatamente um bloco de contrato no registro."""
    players = player_uids(people)
    found: dict[int, Contract] = {}
    previous = 0
    for match in _TAIL.finditer(people, 0, PEOPLE_END):
        _, uid = struct.unpack("<II", match.group(1) + match.group(2))
        if uid not in players:
            continue
        blocks = [b for b in _CONTRACT.finditer(people, previous, match.start())
                  if struct.unpack("<H", b.group(3))[0] <= 365]
        if len(blocks) == 1 and uid not in found:
            block = blocks[0]
            found[uid] = Contract(uid, block.start() + 1, struct.unpack("<I", block.group(1))[0],
                                  struct.unpack("<H", block.group(4))[0])
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
            if index == own:
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
        struct.pack_into("<I", out, found[uid].at, club)
    return bytes(out)
