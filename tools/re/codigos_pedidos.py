"""Sonda: quais códigos de propriedade o jogo pergunta aos jogadores (instalar / ler / desfazer).

No desvio de propriedades do jogador (patch centro_colunas, .fm26+0xD200: o código chega em
[esp+4]) grava cada código diferente numa tabela com contagem. Só anota; não muda nada.
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "re"), str(ROOT / "scripts")]
import chamada_remota as cr  # noqa: E402
from live_player_memory import read_memory  # noqa: E402

HOOK, STOLEN = 0x015C1200, bytes.fromhex("8B442404 3D6C636D50")       # mov eax,[esp+4]; cmp eax,'Pmcl'
TABLE, STUB, SLOTS = cr.COUNTERS_AT + 0x800, cr.COUNTERS_AT + 0xC00, 120


def stub_code() -> bytes:
    c = bytes.fromhex("505152 8B442410 B9") + TABLE.to_bytes(4, "little") + bytes([0xBA]) + SLOTS.to_bytes(4, "little")
    c += bytes.fromhex("3901 740F 833900 7408 83C108 4A 75F1 EB05 8901 FF4104 5A5958")
    c += STOLEN
    c += bytes([0xE9]) + ((HOOK + len(STOLEN)) - (STUB + len(c) + 5)).to_bytes(4, "little", signed=True)
    return c


def main() -> None:
    _, h = cr.game()
    action = sys.argv[1]
    if action == "instalar":
        assert read_memory(h, HOOK, len(STOLEN)) == STOLEN, "desvio de propriedades diferente do esperado"
        cr.poke(h, TABLE, bytes(8 * SLOTS))
        cr.poke(h, STUB, stub_code())
        cr.poke(h, HOOK, bytes([0xE9]) + (STUB - (HOOK + 5)).to_bytes(4, "little", signed=True) + bytes([0x90] * 4))
        print("sonda instalada")
    elif action == "desfazer":
        cr.poke(h, HOOK, STOLEN)
        print("original de volta")
    else:
        raw = read_memory(h, TABLE, 8 * SLOTS)
        rows = [struct.unpack_from("<II", raw, 8 * i) for i in range(SLOTS)]
        for code, n in sorted((r for r in rows if r[0]), key=lambda r: -r[1]):
            text = code.to_bytes(4, "big").decode("latin-1")
            print(f"{text} ({code:#010x}): {n}")


if __name__ == "__main__":
    main()
