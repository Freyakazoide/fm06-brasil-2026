"""Nomes das fases e rodadas em português do Brasil (lang_db.dat).

A tabela de nomes de fase (código lido por 0x00B43720 nas rodadas e por
0x00B4BE40 nas fases, via 0x00582440) fica no lang_db.dat em português de
Portugal: "Primeira Mão", "Quartos de Final", "Meia Final"... Cada registro é
u32 código e três textos (nome, nome curto, plural), cada um com u32 tamanho
(em caracteres), UTF-16LE, 00 00 e um byte.

O lang_db tem no início um índice com posições absolutas das seções, então o
tamanho do arquivo não pode mudar: o texto novo tem de caber no antigo e é
completado com espaços no fim.

Só o texto muda. O código não pode ser trocado no fm.exe: ele também é o
identificador da rodada. Ex.: a Libertadores manda os vencedores da rodada 0x1C
(Fase Preliminar) para a Fase de Grupos com 0x00B45500(0x1C, ...) em
0x00C07B35; com a rodada renomeada para 0x19 ninguém se classificou, a fase de
grupos nasceu com 26 clubes e o jogo caiu em 1/3/2026 (teste). Como os códigos
valem para todas as competições, um nome só da Libertadores (Pré-Libertadores,
Oitavas de Final) exige trocar o código em todas as referências da rodada.
"""

from __future__ import annotations

import struct

FIRST = (1, "Repetição")              # primeiro registro da tabela
COUNT = 167

# código: (nome, curto, plural); None = não muda
RENAMES: dict[int, tuple[str | None, str | None, str | None]] = {
    0x03: ("Ida", "Ida", "Idas"),
    0x04: ("Volta", "Volta", "Voltas"),
    0x11: ("Quartas de Final", "Quartas", "Quartas de Final"),
    0x12: ("Semifinal", "Semifinal", "Semifinais"),
    0x13: ("Disputa do 3º Lugar", "3º Lugar", "Disputa 3º Lugar"),
    0x17: ("Semifinal do Playoff", "Semifinal Pl.", "Semifinais dos Playoffs"),
    0x24: ("Disputa do 3º Lugar", "3º Lugar", "Disputa 3º Lugar"),
    0x26: ("Semifinal Menor", "Semifinal Menor", "Semifinais Menores"),
    0x27: ("Semifinal Maior", "Semifinal Maior", "Semifinais Maiores"),
    0xA2: ("Equipes de 3º Lugar", "Equipes de 3º Lugar", "Equipes de 3º Lugar"),
}


def _record(code: int, text: str) -> bytes:
    return struct.pack("<II", code, len(text)) + text.encode("utf-16-le") + b"\0\0"


def find_table(data: bytes) -> int:
    at = data.find(_record(*FIRST))
    if at < 0 or data.find(_record(*FIRST), at + 1) >= 0:
        raise ValueError("tabela de nomes de fase não encontrada (ou repetida) no lang_db")
    return at


def records(data: bytes, start: int):
    """(código, [(posição do tamanho, texto)] × 3) de cada registro."""
    at = start
    for _ in range(COUNT):
        code = struct.unpack_from("<I", data, at)[0]
        at += 4
        texts = []
        for _ in range(3):
            size = struct.unpack_from("<I", data, at)[0]
            texts.append((at, data[at + 4:at + 4 + 2 * size].decode("utf-16-le")))
            at += 4 + 2 * size
            if data[at:at + 2] != b"\0\0":
                raise ValueError(f"lang_db: registro de fase 0x{code:X} fora do formato")
            at += 3
        yield code, texts


def apply(data: bytes, renames=RENAMES) -> tuple[bytes, list[str]]:
    out = bytearray(data)
    done = []
    table = {code: texts for code, texts in records(data, find_table(data))}
    for code, new in renames.items():
        for (at, old), text in zip(table[code], new):
            if text is None:
                continue
            if len(text) > len(old):
                raise ValueError(f"lang_db: '{text}' não cabe no lugar de '{old}'")
            out[at + 4:at + 4 + 2 * len(old)] = text.ljust(len(old)).encode("utf-16-le")
        done.append(f"{table[code][0][1]} -> {new[0]}")
    return bytes(out), done
