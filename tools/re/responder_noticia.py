r"""Responde pelo Python a uma notícia que pede escolha, pela própria função do jogo.

Slot 22 da 1ª vtable (RED_CARD_BAN_NEWS: 0x5918C0; ret 8): recebe (resposta, aplicar). Lê a opção em
resposta+0xE, grava em +0x20 e liga +0x22 bit 8; com aplicar != 0 e opção 1, faz a apelação. O slot
13 (0x4015D0) só devolve +0x20. Em +0x20: -3 esperando, 2 sem apelação (slot 21, ou a data passou,
slot 19). Só com a thread principal parada (laco.parked).

    python tools\re\responder_noticia.py 1067 1          (série, opção)
"""

from __future__ import annotations

import ctypes
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "central"), str(ROOT / "tools" / "imprensa"), str(ROOT / "tools" / "re")]

import chamada_remota as cr  # noqa: E402
import laco  # noqa: E402
import leitor  # noqa: E402
import noticias  # noqa: E402

REPLY_SLOT, OPTION_AT = 0x58, 0xE
OPTIONS = {"RED_CARD_BAN_NEWS": {1: "Apelar Contra Suspensão", 2: "Não Apelar"}}
WAITING = (-2, -3, -4)


def reply_code(news: int, answer: int) -> bytes:
    c = bytearray(b"\x53\x56\x57\x6A\x01")                                  # push ebx/esi/edi; push 1
    c += b"\x68" + answer.to_bytes(4, "little")                             # push resposta
    c += b"\xB9" + news.to_bytes(4, "little") + b"\x8B\x01"                 # mov ecx, notícia; mov eax, [ecx]
    c += b"\xFF\x50" + bytes([REPLY_SLOT])                                  # call [eax+0x58]
    c += b"\x5F\x5E\x5B\x33\xC0\xC2\x04\x00"                                # pop; eax = 0; ret 4
    return bytes(c)


def answer(jogo: leitor.Jogo, pid: int, handle, serial: int, option: int) -> int:
    """Devolve o novo +0x20. Recusa o que não estiver esperando resposta ou opção desconhecida."""
    _, data, count, _ = noticias.box(jogo)
    items = struct.unpack(f"<{count}I", jogo.raw(data, 4 * count))
    news = next((p for p in items if jogo.u32(p + noticias.SERIAL) == serial), None)
    if not news:
        raise LookupError(f"notícia {serial} não está na caixa")
    kind = noticias.CLASSES.get(jogo.u32(news))
    state = struct.unpack("<h", jogo.raw(news + noticias.REPLY, 2))[0]
    if option not in OPTIONS.get(kind, {}):
        raise ValueError(f"{kind}: opção {option} desconhecida")
    if state not in WAITING:
        raise ValueError(f"notícia {serial} não está esperando resposta (+0x20 = {state})")
    page = cr.kernel32.VirtualAllocEx(handle, None, 0x1000, cr.MEM_COMMIT_RESERVE, 0x04)
    if not page:
        raise OSError(ctypes.get_last_error(), "VirtualAllocEx falhou")
    try:
        cr.poke(handle, page + OPTION_AT, option.to_bytes(2, "little"))
        with laco.parked(pid, handle):
            cr.run(handle, reply_code(news, page))
    finally:
        cr.kernel32.VirtualFreeEx(handle, page, 0, 0x8000)
    return struct.unpack("<h", jogo.raw(news + noticias.REPLY, 2))[0]


def main() -> None:
    serial, option = int(sys.argv[1]), int(sys.argv[2])
    jogo = leitor.Jogo()
    pid, handle = cr.game()
    print(f"notícia {serial}: +0x20 = {answer(jogo, pid, handle, serial, option)}")


if __name__ == "__main__":
    main()
