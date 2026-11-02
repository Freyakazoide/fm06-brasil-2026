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
kernel32.VirtualProtectEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD,
                                      ctypes.POINTER(wintypes.DWORD)]


def poke(handle, address: int, data: bytes) -> None:
    """Grava na memória do jogo, inclusive em código (troca a proteção da página na hora)."""
    old = wintypes.DWORD()
    if not kernel32.VirtualProtectEx(handle, ctypes.c_void_p(address), len(data), PAGE_EXECUTE_READWRITE,
                                     ctypes.byref(old)):
        raise OSError(ctypes.get_last_error(), f"VirtualProtectEx falhou em 0x{address:08X}")
    written = ctypes.c_size_t()
    buf = ctypes.create_string_buffer(data, len(data))
    ok = kernel32.WriteProcessMemory(handle, ctypes.c_void_p(address), buf, len(data), ctypes.byref(written))
    kernel32.VirtualProtectEx(handle, ctypes.c_void_p(address), len(data), old.value, ctypes.byref(old))
    if not ok:
        raise OSError(ctypes.get_last_error(), f"WriteProcessMemory falhou em 0x{address:08X}")


# colunas da lista de pessoas (ficha T1): 0x008D0780 preenche cada célula por código; código que
# ela não conhece vai, em 0x008D0FE0, para a pessoa ([esi], interface em +4, método 1), que dá "-".
CELL_DEFAULT, CELL_NUMBER = 0x008D0FE0, 0x008D0804      # "número em eax -> texto na célula"
CELL_HOOK_AT = 0x015C1100                               # .fm26 + 0xD100 (livre)
CELL_DEBUG = 0x015C11F0                                 # ponteiros guardados pelo teste
CA_CODE, PA_CODE = 0x50434142, 0x50504142               # 'PCAB', 'PPAB'


def cell_test_code() -> bytes:
    """Teste: C.A mostra 42 e P.A 77, e guarda [esi] e esi em CELL_DEBUG."""
    from_here = lambda target, at: (target - (at + 5)).to_bytes(4, "little", signed=True)
    c = bytearray()
    c += b"\x3D" + CA_CODE.to_bytes(4, "little") + b"\x74\x11"           # cmp eax,'PCAB'; je ca (+0x18)
    c += b"\x3D" + PA_CODE.to_bytes(4, "little") + b"\x74\x22"           # cmp eax,'PPAB'; je pa (+0x30)
    c += b"\x8B\x36\x8B\x56\x04"                                         # original: mov esi,[esi]; mov edx,[esi+4]
    c += b"\xE9" + from_here(CELL_DEFAULT + 5, CELL_HOOK_AT + len(c))
    # ca:
    c += b"\x8B\x0E\x89\x0D" + CELL_DEBUG.to_bytes(4, "little")          # [debug] = [esi]
    c += b"\x89\x35" + (CELL_DEBUG + 8).to_bytes(4, "little")            # [debug+8] = esi
    c += b"\xB8\x2A\x00\x00\x00"                                         # eax = 42
    c += b"\xE9" + from_here(CELL_NUMBER, CELL_HOOK_AT + len(c))
    # pa:
    c += b"\x8B\x0E\x89\x0D" + (CELL_DEBUG + 4).to_bytes(4, "little")    # [debug+4] = [esi]
    c += b"\xB8\x4D\x00\x00\x00"                                         # eax = 77
    c += b"\xE9" + from_here(CELL_NUMBER, CELL_HOOK_AT + len(c))
    return bytes(c)


# o jogador responde as propriedades das colunas por ACTUAL_PLAYER::propriedade(código, saída)
# (0x00A40D20, ret 8), chamada pela interface em jogador+4: vtable 0x010F1020, método 1 =
# 0x00A47530 (ajusta o this e salta). Desviar esse ponteiro vale para todos os jogadores.
PLAYER_PROPERTY_SLOT, PLAYER_PROPERTY = 0x010F1024, 0x00A47530
VALUE_FROM_INT, VALUE_COPY, VALUE_FREE = 0x00C74B10, 0x00C72670, 0x00C72650
PROPERTY_HOOK_AT = 0x015C1200                          # .fm26 + 0xD200 (livre)


def property_hook_code() -> bytes:
    """PCAB/PPAB: CA/PA do jogador (ecx = jogador + 4: CA em ecx − 0xBC, PA em ecx − 0xBA)."""
    from_here = lambda target, at: (target - (at + 5)).to_bytes(4, "little", signed=True)
    c = bytearray()
    c += b"\x8B\x44\x24\x04"                                             # mov eax, [esp+4] (código)
    c += b"\x3D" + CA_CODE.to_bytes(4, "little") + b"\x74\x0C"           # je ca
    c += b"\x3D" + PA_CODE.to_bytes(4, "little") + b"\x74\x0E"           # je pa
    c += b"\xE9" + from_here(PLAYER_PROPERTY, PROPERTY_HOOK_AT + len(c))  # os outros: original
    c += b"\x0F\xB7\x81" + (-0xBC & 0xFFFFFFFF).to_bytes(4, "little")    # ca: movzx eax, word [ecx-0xBC]
    c += b"\xEB\x07"                                                     # jmp grava
    c += b"\x0F\xB7\x81" + (-0xBA & 0xFFFFFFFF).to_bytes(4, "little")    # pa: movzx eax, word [ecx-0xBA]
    c += b"\x83\xEC\x10"                                                 # grava: sub esp,0x10 (valor em [esp])
    c += b"\x50\x8D\x4C\x24\x04"                                         # push eax; lea ecx,[esp+4]
    c += b"\xE8" + from_here(VALUE_FROM_INT, PROPERTY_HOOK_AT + len(c))  # valor(int)
    c += b"\x8B\x4C\x24\x18\x8D\x04\x24\x50"                             # ecx = saída ([esp+0x18]); push &valor
    c += b"\xE8" + from_here(VALUE_COPY, PROPERTY_HOOK_AT + len(c))      # saída = valor
    c += b"\x8D\x0C\x24"                                                 # lea ecx, [esp]
    c += b"\xE8" + from_here(VALUE_FREE, PROPERTY_HOOK_AT + len(c))
    c += b"\x83\xC4\x10\xB0\x01\xC2\x08\x00"                             # add esp,0x10; mov al,1; ret 8
    return bytes(c)


def property_code(person: int, code: int) -> bytes:
    """Pergunta a propriedade ``code`` à pessoa (ponteiro da tabela de pessoas; a interface de
    propriedades fica em +4, método 1) e devolve o primeiro dword do valor (o número)."""
    c = bytearray()
    c += b"\x83\xEC\x08\x31\xC0\x89\x04\x24\x89\x44\x24\x04"            # valor vazio em [esp]
    c += b"\x54\x68" + code.to_bytes(4, "little")                        # push &valor; push código
    c += b"\xB9" + (person + 4).to_bytes(4, "little")                     # ecx = pessoa + 4
    c += b"\x8B\x01\xFF\x50\x04"                                         # call [[ecx]+4]
    c += b"\x8B\x04\x24\x83\xC4\x08\xC2\x04\x00"                          # eax = número; ret 4
    return bytes(c)


COUNTERS_AT = 0x015C2000                              # .fm26 + 0xE000: contadores e trampolins


def counter_patches(functions: list[int]) -> tuple[list[tuple[int, bytes, bytes]], bytes]:
    """Para cada função: trampolim (inc contador; instruções roubadas; jmp de volta) e o jmp na
    entrada. Devolve ([(endereço, original, novo)], bloco da .fm26 com contadores e trampolins)."""
    sys.path.insert(0, str(ROOT / "workspace" / "pydeps"))
    from capstone import CS_ARCH_X86, CS_MODE_32, Cs
    sys.path.insert(0, str(ROOT / "src"))
    from fm06patch.exe_cave import off

    exe = (Path(json_game_dir()) / "fm.exe").read_bytes()
    cs = Cs(CS_ARCH_X86, CS_MODE_32)
    block = bytearray(4 * len(functions))
    patches = []
    for n, f in enumerate(functions):
        stolen = b""
        for ins in cs.disasm(exe[off(f):off(f) + 32], f):
            if ins.mnemonic in ("call", "jmp") or ins.mnemonic.startswith("j") or "rip" in ins.op_str:
                raise SystemExit(f"0x{f:08X}: salto nos primeiros bytes ({ins.mnemonic}); escolha outra")
            stolen += bytes(ins.bytes)
            if len(stolen) >= 5:
                break
        tramp = COUNTERS_AT + len(block)
        code = b"\xFF\x05" + (COUNTERS_AT + 4 * n).to_bytes(4, "little") + stolen
        code += b"\xE9" + ((f + len(stolen)) - (tramp + len(code) + 5)).to_bytes(4, "little", signed=True)
        block += code
        new = b"\xE9" + (tramp - (f + 5)).to_bytes(4, "little", signed=True) + b"\x90" * (len(stolen) - 5)
        patches.append((f, stolen, new))
    return patches, bytes(block)


CALLERS_TABLE, CALLERS_TRAMP, CALLERS_SLOTS = COUNTERS_AT + 0x800, COUNTERS_AT + 0xC00, 64


def callers_patch(f: int, stolen: bytes) -> tuple[bytes, bytes]:
    """Trampolim que conta quem chama f (endereço de retorno em [esp]) numa tabela de 64 pares
    (retorno, contagem); depois executa as instruções roubadas e volta. Devolve (trampolim, jmp)."""
    code = bytes.fromhex("505152 8B44240C B9") + CALLERS_TABLE.to_bytes(4, "little")
    code += bytes([0xBA]) + CALLERS_SLOTS.to_bytes(4, "little")
    code += bytes.fromhex("3901 740F 833900 7408 83C108 4A 75F1 EB05 8901 FF4104 5A5958")
    code += stolen
    code += bytes([0xE9]) + ((f + len(stolen)) - (CALLERS_TRAMP + len(code) + 5)).to_bytes(4, "little", signed=True)
    jump = bytes([0xE9]) + (CALLERS_TRAMP - (f + 5)).to_bytes(4, "little", signed=True) + bytes([0x90]) * (len(stolen) - 5)
    return code, jump


def json_game_dir() -> str:
    import json
    return json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"]


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


def run(handle, code, timeout_ms: int = 10_000) -> int:
    """Grava ``code`` (stdcall, 1 argumento, devolve eax) e roda numa thread do jogo. ``code``
    pode ser uma função do endereço da página (para código com call relativo)."""
    page = kernel32.VirtualAllocEx(handle, None, 0x1000, MEM_COMMIT_RESERVE, PAGE_EXECUTE_READWRITE)
    if not page:
        raise OSError(ctypes.get_last_error(), "VirtualAllocEx falhou")
    if callable(code):
        code = code(page)
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


def news_test_code(page: int, club_uid: int, nation_uid: int, count: int) -> bytes:
    """count garotos no clube pela rotina da fornada (.fm26, patch fornada_base) e a notícia."""
    sys.path.insert(0, str(ROOT / "src"))
    from fm06patch import fornada
    from fm06patch.exe_cave import SECTION_VA

    make_youth, news_at = SECTION_VA + 0x7140, page + 0x400
    a = fornada._Code(page)
    a.raw("55 8BEC 83EC40 53 56 57")
    a.raw("8B0D").u32(0x14EAA4C).raw("68").u32(nation_uid).acall(0x582440).raw("8BD8")   # ebx = nação
    a.raw("8B0D").u32(0x14EAA30).raw("68").u32(club_uid).acall(0x582440).raw("8BF8")     # edi = clube
    a.raw("85FF").jump("0F84", "fim").raw("85DB").jump("0F84", "fim")
    a.raw("C745E0").u32(fornada.PERSON_LIST_VTABLE).raw("C745E400000000 C645E800 C645EC00")
    a.raw("BE").u32(count)
    a.label("laco").raw("53 57").acall(make_youth).raw("85C0").jump("0F84", "prox")
    a.raw("50 8D4DE0").acall(fornada.LIST_ADD)
    a.label("prox").raw("4E").jump("0F85", "laco")
    a.raw("8D45E0 50 57").acall(news_at)
    a.raw("0FB645E8")                                       # devolve quantos entraram na lista
    a.label("fim").raw("5F 5E 5B 8BE5 5D C20400")
    main = a.done()
    return main + bytes(0x400 - len(main)) + fornada.news_code(news_at, absolute=True)


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
    n = sub.add_parser("noticia", help="garotos pela rotina da fornada e a notícia de juniores")
    n.add_argument("clube", type=int)
    n.add_argument("--quantos", type=int, default=2)
    n.add_argument("--nacao", type=int, default=1651)
    k = sub.add_parser("colunas", help="teste das colunas C.A/P.A na memória do jogo (ficha T1)")
    k.add_argument("acao", choices=("instalar", "desfazer", "ler", "jogador", "jogador-desfazer"))
    q = sub.add_parser("contar", help="conta chamadas de funções do jogo (instalar/ler/desfazer)")
    q.add_argument("acao", choices=("instalar", "ler", "desfazer"))
    q.add_argument("funcoes", nargs="+", type=lambda s: int(s, 16))
    w = sub.add_parser("chamadores", help="quem chama uma função (instalar/ler/desfazer)")
    w.add_argument("acao", choices=("instalar", "ler", "desfazer"))
    w.add_argument("funcao", type=lambda s: int(s, 16))
    w.add_argument("roubados", type=int, help="bytes inteiros de instrução copiados (>= 5)")
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
    if a.cmd == "chamadores":
        saved = ROOT / "workspace" / f"chamadores_{a.funcao:08X}.bin"
        if a.acao == "instalar":
            stolen = read_memory(handle, a.funcao, a.roubados)
            code, jump = callers_patch(a.funcao, stolen)
            saved.write_bytes(stolen)
            poke(handle, CALLERS_TABLE, bytes(8 * CALLERS_SLOTS))
            poke(handle, CALLERS_TRAMP, code)
            poke(handle, a.funcao, jump)
            print(f"instalado; roubados {stolen.hex()}")
        elif a.acao == "ler":
            raw = read_memory(handle, CALLERS_TABLE, 8 * CALLERS_SLOTS)
            rows = [struct.unpack_from("<II", raw, 8 * i) for i in range(CALLERS_SLOTS)]
            for ret, n in sorted((r for r in rows if r[0]), key=lambda r: -r[1]):
                print(f"retorno 0x{ret:08X}: {n}")
        else:
            poke(handle, a.funcao, saved.read_bytes())
            print("original de volta")
        return
    if a.cmd == "contar":
        patches, block = counter_patches(a.funcoes)
        if a.acao == "instalar":
            for f, old, new in patches:
                here = read_memory(handle, f, len(old))
                if here != old:
                    raise SystemExit(f"0x{f:08X} já mudado: {here.hex()}")
            poke(handle, COUNTERS_AT, block)
            for f, old, new in patches:
                poke(handle, f, new)
            print(f"{len(patches)} contadores instalados")
        elif a.acao == "ler":
            counts = struct.unpack(f"<{len(patches)}I", read_memory(handle, COUNTERS_AT, 4 * len(patches)))
            for (f, _, _), n in zip(patches, counts):
                print(f"0x{f:08X}: {n}")
        else:
            for f, old, new in patches:
                poke(handle, f, old)
            print("originais de volta")
        return
    if a.cmd == "colunas":
        original = bytes.fromhex("8B368B5604")                   # mov esi,[esi]; mov edx,[esi+4]
        jump = b"\xE9" + (CELL_HOOK_AT - (CELL_DEFAULT + 5)).to_bytes(4, "little", signed=True)
        here = read_memory(handle, CELL_DEFAULT, 5)
        if a.acao in ("jogador", "jogador-desfazer"):
            slot = struct.unpack("<I", read_memory(handle, PLAYER_PROPERTY_SLOT, 4))[0]
            if slot not in (PLAYER_PROPERTY, PROPERTY_HOOK_AT):
                raise SystemExit(f"vtable inesperada: 0x{slot:08X}")
            if a.acao == "jogador":
                poke(handle, PROPERTY_HOOK_AT, property_hook_code())
                poke(handle, PLAYER_PROPERTY_SLOT, PROPERTY_HOOK_AT.to_bytes(4, "little"))
                print("desvio na vtable do jogador: C.A e P.A devem mostrar os números reais")
            else:
                poke(handle, PLAYER_PROPERTY_SLOT, PLAYER_PROPERTY.to_bytes(4, "little"))
                print("vtable original de volta")
            return
        if a.acao == "instalar":
            if here not in (original, jump):
                raise SystemExit(f"bytes inesperados em 0x{CELL_DEFAULT:08X}: {here.hex()}")
            free = read_memory(handle, CELL_HOOK_AT, 0x100)
            if any(free) and here == original:
                raise SystemExit(f"0x{CELL_HOOK_AT:08X} não está livre")
            poke(handle, CELL_HOOK_AT, cell_test_code())
            poke(handle, CELL_DEBUG, bytes(12))
            poke(handle, CELL_DEFAULT, jump)
            print("teste instalado: C.A deve mostrar 42 e P.A 77")
        elif a.acao == "desfazer":
            poke(handle, CELL_DEFAULT, original)
            print("original de volta")
        else:
            person, person_pa, this = struct.unpack("<III", read_memory(handle, CELL_DEBUG, 12))
            print(f"[esi] na coluna C.A: 0x{person:08X}; na P.A: 0x{person_pa:08X}; esi: 0x{this:08X}")
            for name, at in (("[esi]", person), ("[esi]-0xD0", person - 0xD0)):
                head = read_memory(handle, at, 0x18) if at else None
                if head:
                    print(f"  {name}: dwords {[hex(x) for x in struct.unpack('<6I', head)]}")
        return
    if a.cmd == "noticia":
        result = run(handle, lambda page: news_test_code(page, a.clube, a.nacao, a.quantos), timeout_ms=60_000)
        print(f"{result} garoto(s) na lista da notícia")
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
