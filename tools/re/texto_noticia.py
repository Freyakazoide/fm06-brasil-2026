r"""O texto (manchete e corpo) de uma notícia da caixa, montado pelo próprio jogo.

Caminho da tela de Notícias (0x4DA130, conferido com sonda em 0x5EF4C0, 03/11): string vazia
(0xC50A00; objeto de 0xC bytes: 2 vtables e o nó), arg = 0x886840(ecx = 0x4BD400(1)),
notícia->vtable[5](arg, &string, 0 = manchete / 1 = corpo). Depois disso a string já tem o texto
final em UTF-16 (nó: u16, u16, u16 tamanho, u16 capacidade, ponteiro para o texto), com os links
como registros "<record>...</record>" antes da palavra clicável (dref = objeto do jogo). A tela
ainda passa a string por 0xC74DC0 (texto rico), que aqui não é preciso. Conferido: "Figueirense com
vitória gorda" e o corpo igual ao da tela. Thread remota; a string é destruída (0xC50B30) depois.

    python tools\re\texto_noticia.py 1019          (série da notícia)
"""

from __future__ import annotations

import ctypes
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "central"), str(ROOT / "tools" / "imprensa"), str(ROOT / "tools" / "re")]

import chamada_remota as cr  # noqa: E402
import leitor  # noqa: E402
import noticias  # noqa: E402

STRING_NEW, STRING_FREE, VIEWER, VIEWER_ARG = 0x00C50A00, 0x00C50B30, 0x004BD400, 0x00886840
HEADLINE, BODY = 0, 1


def build_code(news: int, flag: int, string: int) -> bytes:
    c = bytearray(b"\x53\x56\x57")                                               # push ebx/esi/edi
    c += b"\xB9" + string.to_bytes(4, "little") + b"\xB8" + STRING_NEW.to_bytes(4, "little") + b"\xFF\xD0"
    c += b"\x6A\x01\xB8" + VIEWER.to_bytes(4, "little") + b"\xFF\xD0\x83\xC4\x04"  # push 1; call; add esp,4
    c += b"\x8B\xC8\xB8" + VIEWER_ARG.to_bytes(4, "little") + b"\xFF\xD0"         # ecx = eax; call
    c += b"\x6A" + bytes([flag]) + b"\x68" + string.to_bytes(4, "little") + b"\x50"    # flag, &string, arg
    c += b"\xB9" + news.to_bytes(4, "little") + b"\x8B\x01\xFF\x50\x14"          # ecx = notícia; call [vt+0x14]
    c += b"\x5F\x5E\x5B\x33\xC0\xC2\x04\x00"                                     # pop; eax = 0; ret 4
    return bytes(c)


def read_string(jogo: leitor.Jogo, string: int) -> str:
    node = jogo.u32(string + 8)
    _, _, length, _, data = struct.unpack("<4HI", jogo.raw(node, 12))
    return jogo.raw(data, 2 * length).decode("utf-16-le", "replace") if length else ""


def plain(text: str) -> str:
    """Tira os registros de link (aninhados) e as marcas de trecho clicável (caracteres 01 e 02) e
    deixa só o texto que a tela mostra."""
    out, depth, i = [], 0, 0
    for match in re.finditer(r"<record[^>]*>|</record>", text):
        if depth == 0:
            out.append(text[i:match.start()])
        depth += -1 if match.group().startswith("</") else 1
        i = match.end()
    out.append(text[i:] if depth == 0 else "")
    text = "".join(out).replace("\\", "").replace("\x13", "–")              # 0x13: travessão do jogo
    return re.sub(r"[\x00-\x09\x0b-\x1f]", "", text).strip()


def news_text(jogo: leitor.Jogo, handle, news: int) -> tuple[str, str]:
    page = cr.kernel32.VirtualAllocEx(handle, None, 0x1000, cr.MEM_COMMIT_RESERVE, 0x04)
    if not page:
        raise OSError(ctypes.get_last_error(), "VirtualAllocEx falhou")
    try:
        texts = []
        for flag in (HEADLINE, BODY):
            string = page + 0x40 * flag
            cr.run(handle, build_code(news, flag, string))
            texts.append(read_string(jogo, string))
            cr.run(handle, cr.call_code(STRING_FREE, hex(string), []))
        return texts[0], texts[1]
    finally:
        cr.kernel32.VirtualFreeEx(handle, page, 0, 0x8000)


def text_of(jogo: leitor.Jogo, serial: int) -> dict:
    """Manchete e corpo (texto da tela, sem os links) da notícia de série `serial` da caixa."""
    _, data, count, _ = noticias.box(jogo)
    items = struct.unpack(f"<{count}I", jogo.raw(data, 4 * count)) if count else ()
    news = next((p for p in items if jogo.u32(p + noticias.SERIAL) == serial), None)
    if not news:
        raise LookupError(f"notícia {serial} não está na caixa")
    _, handle = cr.game()
    try:
        headline, body = news_text(jogo, handle, news)
    finally:
        cr.kernel32.CloseHandle(handle)
    return {"manchete": plain(headline), "corpo": plain(body)}


def main() -> None:
    jogo = leitor.Jogo()
    _, data, count, _ = noticias.box(jogo)
    items = struct.unpack(f"<{count}I", jogo.raw(data, 4 * count))
    _, handle = cr.game()
    for serial in map(int, sys.argv[1:]):
        news = next((p for p in items if jogo.u32(p + noticias.SERIAL) == serial), None)
        if not news:
            print(f"{serial}: não está na caixa")
            continue
        headline, body = news_text(jogo, handle, news)
        print(f"{serial} [{noticias.CLASSES.get(jogo.u32(news), '?')}]\n  {plain(headline)}\n  {plain(body)}\n")


if __name__ == "__main__":
    main()
