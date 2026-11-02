"""Chama uma função do fm.exe dentro do jogo aberto (thread remota) e mostra o retorno.

    python tools\\re\\chamada_remota.py chamar 0x582440 --ecx [0x14EAA4C] --args 1651
    python tools\\re\\chamada_remota.py ler 0x14EAB34 16

Para testar rotinas do jogo sem reinstalar (ficha C14). O código vai numa página nova do
processo e roda numa thread nova enquanto o jogo está parado numa tela (sem avançar dias):
o motor do FM06 é de uma thread só, então chamar algo que mexe no banco com o jogo
processando pode corromper a partida. Use um save de teste.

--ecx aceita um número (0x...) ou [0x...] (o valor guardado nesse endereço).
"""

from __future__ import annotations

import argparse
import ctypes
import struct
import sys
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from live_player_memory import find_process_id, kernel32, read_memory  # noqa: E402

PROCESS_ACCESS = 0x0002 | 0x0008 | 0x0010 | 0x0020 | 0x0400   # criar thread, VM, consulta
MEM_COMMIT_RESERVE = 0x3000
MEM_RELEASE = 0x8000
PAGE_EXECUTE_READWRITE = 0x40

kernel32.VirtualAllocEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
kernel32.VirtualAllocEx.restype = ctypes.c_void_p
kernel32.VirtualFreeEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD]
kernel32.WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                        ctypes.POINTER(ctypes.c_size_t)]
kernel32.CreateRemoteThread.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
                                        ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]
kernel32.CreateRemoteThread.restype = wintypes.HANDLE
kernel32.GetExitCodeThread.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]


def game() -> tuple[int, int]:
    for name in ("fm_brasil.exe", "fm.exe"):
        try:
            pid = find_process_id(name)
            break
        except RuntimeError:
            continue
    else:
        raise SystemExit("abra o fm_brasil.exe antes")
    handle = kernel32.OpenProcess(PROCESS_ACCESS, False, pid)
    if not handle:
        raise SystemExit("OpenProcess falhou (abra o terminal como Administrador)")
    return pid, handle


def run(handle, code: bytes, timeout_ms: int = 10_000) -> int:
    """Grava ``code`` (stdcall, 1 argumento, devolve eax) e roda numa thread do jogo."""
    page = kernel32.VirtualAllocEx(handle, None, 0x1000, MEM_COMMIT_RESERVE, PAGE_EXECUTE_READWRITE)
    if not page:
        raise OSError(ctypes.get_last_error(), "VirtualAllocEx falhou")
    try:
        written = ctypes.c_size_t()
        buf = ctypes.create_string_buffer(code, len(code))
        if not kernel32.WriteProcessMemory(handle, page, buf, len(code), ctypes.byref(written)):
            raise OSError(ctypes.get_last_error(), "WriteProcessMemory falhou")
        thread = kernel32.CreateRemoteThread(handle, None, 0, page, None, 0, None)
        if not thread:
            raise OSError(ctypes.get_last_error(), "CreateRemoteThread falhou")
        if kernel32.WaitForSingleObject(thread, timeout_ms) != 0:
            raise TimeoutError("a função não voltou a tempo")
        code_out = wintypes.DWORD()
        kernel32.GetExitCodeThread(thread, ctypes.byref(code_out))
        kernel32.CloseHandle(thread)
        return code_out.value
    finally:
        kernel32.VirtualFreeEx(handle, page, 0, MEM_RELEASE)


def call_code(func: int, ecx: str | None, args: list[int]) -> bytes:
    """mov ecx, ... ; push args ; mov eax, func ; call eax ; ret 4"""
    code = bytearray()
    if ecx:
        if ecx.startswith("["):
            code += b"\x8B\x0D" + struct.pack("<I", int(ecx.strip("[]"), 0))      # mov ecx, [addr]
        else:
            code += b"\xB9" + struct.pack("<I", int(ecx, 0))                       # mov ecx, imm
    for value in reversed(args):
        code += b"\x68" + struct.pack("<I", value & 0xFFFFFFFF)                    # push imm32
    code += b"\xB8" + struct.pack("<I", func) + b"\xFF\xD0"                        # mov eax, f ; call eax
    code += b"\xC2\x04\x00"                                                        # ret 4
    return bytes(code)


def youth_code(club_uid: int, nation_uid: int, playing: dict[int, int] | None = None,
               moves: bytes = b"") -> bytes:
    """Um garoto novo no clube, como o REGENERATION_MANAGER faz (ficha C14): molde na pilha
    (0xA47930), bloco de atributos novo (PLAYING_DATA, 0x70 bytes, 0x7B9670) acrescentado à
    tabela do banco ([0x14EAA6C]) com o índice em +0x18, molde+0xAC = bloco (0xA3EF40), criação
    0x77BEF0(molde, 0, nação) e contrato 0x779B40(garoto+0x278(), clube). Devolve o garoto, ou
    1/2/3/4 se a nação, o clube, a alocação ou a criação falhar. ``playing``: {deslocamento a
    partir do UID do bloco: byte} gravados no bloco antes da criação (posições, pés, perfil);
    ``moves``: os 48 bits de movimentos preferidos, somados ao jogador depois (UID − 48)."""
    def mov_eax_call(target: int) -> bytes:
        return b"\xB8" + struct.pack("<I", target) + b"\xFF\xD0"

    def fail(n: int) -> bytes:                                   # mov eax, n ; jmp fim
        return b"\xB8" + struct.pack("<I", n)

    c = bytearray()
    c += bytes.fromhex("55 8BEC 81EC00040000 53 56 57")          # prólogo, 1 KB de pilha p/ o molde
    c += b"\x8B\x0D" + struct.pack("<I", 0x14EAA4C) + b"\x68" + struct.pack("<I", nation_uid)
    c += mov_eax_call(0x582440) + b"\x8B\xD8"                    # ebx = nação
    checks = []                                                   # (posição do jz, código de erro)
    c += b"\x85\xDB\x0F\x84" + b"\0\0\0\0"; checks.append((len(c) - 4, 1))
    c += b"\x8B\x0D" + struct.pack("<I", 0x14EAA30) + b"\x68" + struct.pack("<I", club_uid)
    c += mov_eax_call(0x582440) + b"\x8B\xF8"                    # edi = clube
    c += b"\x85\xFF\x0F\x84" + b"\0\0\0\0"; checks.append((len(c) - 4, 2))
    c += b"\x6A\x01\x8D\x8D\x00\xFC\xFF\xFF" + mov_eax_call(0xA47930)            # molde(1)
    c += b"\x6A\x70" + mov_eax_call(0xA3BB00) + b"\x83\xC4\x04\x8B\xF0"          # esi = new(0x70)
    c += b"\x85\xF6\x0F\x84" + b"\0\0\0\0"; checks.append((len(c) - 4, 3))
    c += b"\x8B\xCE" + mov_eax_call(0x7B9670)                                    # PLAYING_DATA()
    for rel, value in sorted((playing or {}).items()):                          # mov byte [esi+d], v
        c += b"\xC6\x46" + bytes([0x14 + rel, value & 0xFF])
    c += b"\x8B\x15" + struct.pack("<I", 0x14EAA6C) + bytes.fromhex("8B4A04 8B01 56 FF10 894618")
    c += b"\x56\x8D\x8D\x00\xFC\xFF\xFF" + mov_eax_call(0xA3EF40)                # molde+0xAC = bloco
    c += b"\x53\x6A\x00\x8D\x85\x00\xFC\xFF\xFF\x50\xB9" + struct.pack("<I", 0x132C108)
    c += mov_eax_call(0x77BEF0) + b"\x8B\xF0"                                    # esi = garoto
    c += b"\x85\xF6\x0F\x84" + b"\0\0\0\0"; checks.append((len(c) - 4, 4))
    for i, bits in enumerate(moves):                                             # or byte [esi+d], b
        if bits:
            c += b"\x80\x4E" + bytes([(0x14 - 48 + i) & 0xFF, bits])
    c += b"\x57\x8B\x16\x8B\xCE\xFF\x92" + struct.pack("<I", 0x278)              # push clube ; +0x278()
    c += b"\x50\xB9" + struct.pack("<I", 0x132C108) + mov_eax_call(0x779B40)     # contrato
    c += b"\x8B\xC6\xEB\x00"; ok_jump = len(c) - 1                               # eax = garoto
    fails = {}
    for n in (1, 2, 3, 4):
        fails[n] = len(c)
        c += fail(n) + b"\xEB\x00"
        fails[(n, "jmp")] = len(c) - 1
    end = len(c)
    c += bytes.fromhex("5F 5E 5B 8BE5 5D C20400")
    c[ok_jump] = end - (ok_jump + 1)
    for n in (1, 2, 3, 4):
        c[fails[(n, "jmp")]] = end - (fails[(n, "jmp")] + 1)
    for at, n in checks:
        struct.pack_into("<i", c, at, fails[n] - (at + 4))
    return bytes(c)


# deslocamentos no bloco PLAYING_DATA a partir do UID (reverse/fmm/playing_attributes_layout.json):
# posições gerais 8–16, lados 17–19, detalhadas 20–32 (1 a 20, direto); pés 57/58 (5 × nota + 2)
POSITIONS = range(8, 33)
LEFT_FOOT, RIGHT_FOOT = 57, 58


def _profile(ratings: dict[int, int], left: int, right: int) -> dict[int, int]:
    out = {rel: 1 for rel in POSITIONS}
    out.update(ratings)
    out[LEFT_FOOT], out[RIGHT_FOOT] = 5 * left + 2, 5 * right + 2
    return out


PROFILES = {
    # ponta direita: MO 20, atacante 14, meia 13; direita 20, esquerda 15; MOD 20, MOE 15, AC 14, MD 13
    "ponta": _profile({13: 20, 14: 14, 12: 13, 17: 20, 18: 15, 19: 10, 29: 20, 27: 15, 30: 14, 26: 13},
                      left=10, right=18),
}


def describe(handle, player: int) -> str:
    """Nome, UID, CA e PA do jogador (ACTUAL_PLAYER; mapa na ficha C14)."""
    u = lambda at: struct.unpack("<I", read_memory(handle, at, 4))[0]

    def text(person_name: int) -> str:
        if not person_name:
            return ""
        raw = read_memory(handle, u(u(person_name + 0x24) + 8), 64) or b""
        return raw.decode("utf-16-le", "replace").split("\x00")[0]

    ca, pa = struct.unpack("<HH", read_memory(handle, player + 0x14 - 204, 4))
    return (f"{text(u(player + 44))} {text(u(player + 48))} (\"{text(u(player + 52))}\"), "
            f"UID {u(player + 0x14)}, CA {ca}, PA {pa}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("chamar")
    c.add_argument("func", type=lambda s: int(s, 0))
    c.add_argument("--ecx")
    c.add_argument("--args", nargs="*", type=lambda s: int(s, 0), default=[])
    g = sub.add_parser("garoto", help="cria um garoto no clube (UID do jogo)")
    g.add_argument("clube", type=int)
    g.add_argument("--nacao", type=int, default=1651)
    g.add_argument("--mostrar", action="store_true", help="só mostra o código")
    g.add_argument("--perfil", choices=sorted(PROFILES), help="posições e pés antes da criação")
    t = sub.add_parser("tipo", help="garoto de um tipo da data/modelos/fornada_tipos.csv")
    t.add_argument("clube", type=int)
    t.add_argument("tipo", nargs="?", help="nome do tipo (sem: sorteado pelo peso)")
    t.add_argument("--semente", type=int, default=None)
    t.add_argument("--nacao", type=int, default=1651)
    v = sub.add_parser("vitrine", help="um garoto de cada tipo no clube")
    v.add_argument("clube", type=int)
    v.add_argument("--semente", type=int, default=1)
    v.add_argument("--nacao", type=int, default=1651)
    r = sub.add_parser("ler")
    r.add_argument("addr", type=lambda s: int(s, 0))
    r.add_argument("size", type=lambda s: int(s, 0))
    a = parser.parse_args()
    if a.cmd == "garoto" and a.mostrar:
        sys.path.insert(0, str(ROOT / "workspace" / "pydeps"))
        from capstone import CS_ARCH_X86, CS_MODE_32, Cs
        for i in Cs(CS_ARCH_X86, CS_MODE_32).disasm(youth_code(a.clube, a.nacao, PROFILES.get(a.perfil)), 0):
            print(f"{i.address:04x}  {i.mnemonic} {i.op_str}")
        return
    _, handle = game()
    if a.cmd == "garoto":
        result = run(handle, youth_code(a.clube, a.nacao, PROFILES.get(a.perfil)), timeout_ms=30_000)
        print({1: "nação não achada", 2: "clube não achado", 3: "alocação falhou",
               4: "criação falhou"}.get(result, f"garoto criado: 0x{result:08X}"))
        return
    if a.cmd in ("tipo", "vitrine"):
        import random
        sys.path.insert(0, str(ROOT / "src"))
        from fm06patch import fornada
        types = fornada.load_types()
        rng = random.Random(a.semente)
        if a.cmd == "vitrine":
            chosen = types
        elif a.tipo:
            chosen = [next(k for k in types if fornada._norm(k.name) == fornada._norm(a.tipo))]
        else:
            chosen = [fornada.pick(types, rng)]
        for kind in chosen:
            model = fornada.build(kind, rng)
            result = run(handle, youth_code(a.clube, a.nacao, model.playing, model.moves), timeout_ms=30_000)
            if result < 16:
                print(f"{kind.name}: falhou ({result})")
                continue
            print(f"{kind.name:26} pé {model.foot}  traits: {', '.join(model.traits) or '-':60} "
                  f"-> {describe(handle, result)}")
        return
    if a.cmd == "ler":
        data = read_memory(handle, a.addr, a.size)
        for i in range(0, len(data), 16):
            print(f"{a.addr + i:08X}  {data[i:i + 16].hex(' ')}")
        return
    result = run(handle, call_code(a.func, a.ecx, a.args))
    print(f"retorno: 0x{result:08X} ({result})")


if __name__ == "__main__":
    main()
