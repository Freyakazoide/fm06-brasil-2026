"""Tela atual do jogo aberto (ficha T1): quem é e quais propriedades ela responde.

    python tools\\re\\tela_viva.py instalar        (grava o gerente de telas a cada troca de tela)
    python tools\\re\\tela_viva.py ver Pnam Psnu   (pergunta códigos à tela atual)
    python tools\\re\\tela_viva.py desfazer

0x4C99B0 (this = gerente de telas) roda a cada troca de tela; a tela atual fica em [this+0x1B0]
e responde propriedades por [[tela]+0x20](código, &valor), como faz com scpc e bgnd.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "re"), str(ROOT / "scripts")]
import chamada_remota as cr  # noqa: E402
from live_player_memory import read_memory  # noqa: E402

SCREENS = 0x004C99B0
STOLEN = bytes.fromhex("558BEC83E4F8")              # push ebp; mov ebp,esp; and esp,-8
SLOT = cr.COUNTERS_AT + 0x700                      # onde o desvio grava o gerente
STUB = cr.COUNTERS_AT + 0x710
CURRENT = 0x1B0
# ficha de pessoa: 0x4FFFB0 recebe os dados da tela (this = tela); 0x9F9190 lê do pedido as
# referências do banco em [tela+0x360] e [tela+0x364] (a pessoa?)
SHEET, SHEET_STOLEN = 0x004FFFCC, bytes.fromhex("8B7C2430 8B472C")
SHEET_SLOT, SHEET_STUB = cr.COUNTERS_AT + 0x780, cr.COUNTERS_AT + 0x790
VALUE_NEW = 0x00C74A80                             # construtor do valor (ecx = valor)


def code(text: str) -> int:
    return int.from_bytes(text.encode("ascii"), "big")


def ask_code(screen: int, prop: int) -> bytes:
    """Pergunta prop à tela com um valor criado pelo jogo (0xC74A80); guarda os 8 primeiros bytes
    do valor em SLOT+8."""
    c = bytearray(b"\x83\xEC\x10\x8D\x0C\x24\xB8") + VALUE_NEW.to_bytes(4, "little") + b"\xFF\xD0"
    c += b"\x54\x68" + prop.to_bytes(4, "little")                         # push &valor; push código
    c += b"\xB9" + screen.to_bytes(4, "little") + b"\x8B\x01\xFF\x50\x20"  # call [[tela]+0x20]
    c += b"\x8B\x04\x24\xA3" + (SLOT + 8).to_bytes(4, "little")
    c += b"\x8B\x44\x24\x04\xA3" + (SLOT + 12).to_bytes(4, "little")
    c += b"\x83\xC4\x10\xC2\x04\x00"
    return bytes(c)


def main() -> None:
    _, h = cr.game()
    u = lambda at: struct.unpack("<I", read_memory(h, at, 4))[0]
    action = sys.argv[1]
    if action == "ficha-instalar":
        assert read_memory(h, SHEET, len(SHEET_STOLEN)) == SHEET_STOLEN
        stub = bytes([0x89, 0x0D]) + SHEET_SLOT.to_bytes(4, "little") + SHEET_STOLEN
        stub += bytes([0xE9]) + (SHEET + len(SHEET_STOLEN) - (SHEET_STUB + len(stub) + 5)).to_bytes(4, "little", signed=True)
        cr.poke(h, SHEET_SLOT, bytes(4))
        cr.poke(h, SHEET_STUB, stub)
        cr.poke(h, SHEET, bytes([0xE9]) + (SHEET_STUB - (SHEET + 5)).to_bytes(4, "little", signed=True) + bytes([0x90, 0x90]))
        print("gravador da ficha instalado: abra a ficha de um jogador")
        return
    if action == "ficha-desfazer":
        cr.poke(h, SHEET, SHEET_STOLEN)
        print("original de volta")
        return
    if action == "ficha":
        sheet = u(SHEET_SLOT)
        print(f"tela da ficha 0x{sheet:08X}, vtable 0x{u(sheet):08X}, seção {read_memory(h, sheet + 0x1AC, 4)[::-1]}")
        for off in (0x360, 0x364):
            obj = u(sheet + off)
            print(f"  +0x{off:X}: 0x{obj:08X}" + (f" vtable 0x{u(obj):08X}" if obj else ""))
            if obj:
                try:
                    print("     ", cr.describe(h, obj))
                except Exception as e:
                    print("      (não é jogador:", e, ")")
        return
    if action == "instalar":
        assert read_memory(h, SCREENS, len(STOLEN)) == STOLEN
        stub = b"\x89\x0D" + SLOT.to_bytes(4, "little") + STOLEN
        stub += b"\xE9" + (SCREENS + len(STOLEN) - (STUB + len(stub) + 5)).to_bytes(4, "little", signed=True)
        cr.poke(h, SLOT, bytes(16))
        cr.poke(h, STUB, stub)
        cr.poke(h, SCREENS, b"\xE9" + (STUB - (SCREENS + 5)).to_bytes(4, "little", signed=True) + b"\x90")
        print("gravador instalado: troque de tela no jogo")
    elif action == "desfazer":
        cr.poke(h, SCREENS, STOLEN)
        print("original de volta")
    else:
        manager = u(SLOT)
        if not manager:
            raise SystemExit("o gerente ainda não foi gravado: troque de tela no jogo")
        screen = u(manager + CURRENT)
        print(f"gerente 0x{manager:08X}, tela 0x{screen:08X}, vtable 0x{u(screen):08X}")
        for name in sys.argv[2:]:
            cr.run(h, ask_code(screen, code(name)))
            a, b = struct.unpack("<II", read_memory(h, SLOT + 8, 8))
            text = ""
            if 0x10000 < a < 0x7FFF0000:
                text += " | bloco " + (read_memory(h, a, 0x20) or b"").hex()
            for p in (a, b):
                raw = read_memory(h, p, 48) if 0x10000 < p < 0x7FFF0000 else None
                if raw:
                    text += " | " + raw.split(b"\0")[0][:40].decode("latin-1", "replace")
            print(f"  {name}: 0x{a:08X} 0x{b:08X}{text}")


if __name__ == "__main__":
    main()
