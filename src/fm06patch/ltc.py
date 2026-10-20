"""data/languages/<idioma>.ltc: os textos das telas do FM06.

    02 01 "ctl." 03 00 00 u32 ? u32 n, nome do idioma (UTF-16LE, n caracteres), 00 00
    depois, para cada texto em inglês:
        64, u32 n, inglês (UTF-16LE), 00 00
        uma ou mais vezes: 65, u32 n, tradução (UTF-16LE), 00 00, u32 identificador
    no fim, a tabela de artigos dos {o}/{do} (marcador 66).

Conferido no portuguese.ltc da 6.0.2: 30.943 traduções até 0xFB28A0. O cache do skin
(data/cache/<idioma>) guarda cópias dos textos e tem de ser apagado depois de mudar o .ltc.
"""

from __future__ import annotations

import struct

KEY, TEXT = 0x64, 0x65


def _string(data: bytes, at: int) -> tuple[int, int, int]:
    """(início do texto, tamanho em caracteres, posição seguinte) da string em ``at``."""
    size = struct.unpack_from("<I", data, at)[0]
    start = at + 4
    end = start + 2 * size
    if data[end:end + 2] != b"\0\0":
        raise ValueError(f"ltc: texto sem 00 00 no fim em 0x{at:X}")
    return start, size, end + 2


def first_entry(data: bytes) -> int:
    if data[2:6] != b"ctl.":
        raise ValueError("ltc: o arquivo não começa com 'ctl.'")
    _, _, after = _string(data, 13)
    return after


def entries(data: bytes) -> list[tuple[str, list[tuple[int, str]]]]:
    """[(inglês, [(posição da tradução, tradução), ...])]."""
    out, at = [], first_entry(data)
    while at < len(data) and data[at] == KEY:
        start, size, at = _string(data, at + 1)
        english = data[start:start + 2 * size].decode("utf-16-le")
        found = []
        while at < len(data) and data[at] == TEXT:
            start, size, at = _string(data, at + 1)
            found.append((start, data[start:start + 2 * size].decode("utf-16-le")))
            at += 4                                     # identificador
        out.append((english, found))
    return out


def translations(data: bytes) -> list[tuple[int, str]]:
    return [item for _, found in entries(data) for item in found]
