r"""Teste: tirar uma notícia da caixa de entrada do FM06 aberto (só a lista; o objeto fica na memória).

A caixa é o NEWS_ITEM_ARRAY em [humano - 0x1E0]: +4 dados, +8 quantidade, +0xC capacidade (75/100
em 03/11); o u32 logo antes (`caixa - 4`, humano-0x1E4) conta as não lidas (conferido: abrir uma
notícia nova mudou 7 -> 6 junto com o bit de lida). Remover = deslocar os ponteiros seguintes uma
posição e baixar a quantidade (e as não lidas, se for o caso). O ponteiro e a posição ficam em workspace/imprensa/caixa_removidas.json para desfazer.

    python tools\re\caixa_remover.py remover 963
    python tools\re\caixa_remover.py desfazer 963
    python tools\re\caixa_remover.py estado
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "central"), str(ROOT / "tools" / "re")]

import chamada_remota as cr  # noqa: E402
import leitor  # noqa: E402

ARRAY_VT, ARRAY_REL, SERIAL, STATUS, UNREAD = 0x010F6DD4, -0x1E0, 0x1C, 0x22, -4
LOG = ROOT / "workspace" / "imprensa" / "caixa_removidas.json"


def array(jogo: leitor.Jogo) -> tuple[int, int, int, int, list[int]]:
    human = next(p for p in jogo.table(leitor.PEOPLE) if p and jogo.u32(p) == leitor.HUMAN_VT)
    at = human + ARRAY_REL
    vt, data, count, capacity = struct.unpack("<4I", jogo.raw(at, 16))
    if vt != ARRAY_VT or not 0 < count <= capacity <= 10000:
        raise SystemExit(f"NEWS_ITEM_ARRAY inesperado em {at:#x}: {vt:#x} {count}/{capacity}")
    return at, data, count, capacity, list(struct.unpack(f"<{count}I", jogo.raw(data, 4 * count)))


def serial(jogo: leitor.Jogo, item: int) -> int:
    return jogo.u32(item + SERIAL)


def load() -> dict:
    try:
        return json.loads(LOG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def main() -> None:
    action = sys.argv[1]
    jogo = leitor.Jogo()
    at, data, count, capacity, items = array(jogo)
    if action == "estado":
        print(f"caixa {at:#x}: {count}/{capacity} notícias, {jogo.u32(at + UNREAD)} não lidas, dados {data:#x}; removidas: {sorted(load())}")
        return
    wanted = int(sys.argv[2])
    _, handle = cr.game()
    log = load()
    if action == "remover":
        index = next((i for i, p in enumerate(items) if serial(jogo, p) == wanted), None)
        if index is None:
            raise SystemExit(f"notícia {wanted} não está na caixa")
        item = items[index]
        log[str(wanted)] = {"ponteiro": item, "posicao": index, "caixa": at, "bytes": jogo.raw(item, 0x80).hex()}
        LOG.parent.mkdir(parents=True, exist_ok=True)
        LOG.write_text(json.dumps(log, indent=1), encoding="utf-8")
        rest = items[:index] + items[index + 1:]
        cr.poke(handle, at + 8, struct.pack("<I", count - 1))           # quantidade primeiro: sem duplicata
        cr.poke(handle, data, struct.pack(f"<{count}I", *rest, 0))
        if not jogo.raw(item + STATUS, 1)[0] & 1:                       # não lida: baixa o contador
            cr.poke(handle, at + UNREAD, struct.pack("<I", max(0, jogo.u32(at + UNREAD) - 1)))
        print(f"removida {wanted} (posição {index}, objeto {item:#x}); caixa {count} -> {array(jogo)[2]}")
    elif action == "desfazer":
        entry = log.get(str(wanted))
        if not entry or entry["caixa"] != at:
            raise SystemExit("nada para desfazer nesta caixa")
        if count >= capacity or jogo.raw(entry["ponteiro"], 0x80).hex() != entry["bytes"] and serial(jogo, entry["ponteiro"]) != wanted:
            raise SystemExit("o objeto da notícia mudou; não reinsiro")
        index = next((i for i, p in enumerate(items) if serial(jogo, p) > wanted), count)
        new = items[:index] + [entry["ponteiro"]] + items[index:]
        cr.poke(handle, data, struct.pack(f"<{count + 1}I", *new))      # lista primeiro, quantidade depois
        cr.poke(handle, at + 8, struct.pack("<I", count + 1))
        if not jogo.raw(entry["ponteiro"] + STATUS, 1)[0] & 1:
            cr.poke(handle, at + UNREAD, struct.pack("<I", jogo.u32(at + UNREAD) + 1))
        del log[str(wanted)]
        LOG.write_text(json.dumps(log, indent=1), encoding="utf-8")
        print(f"reinserida {wanted} na posição {index}; caixa {count} -> {count + 1}")


if __name__ == "__main__":
    main()
