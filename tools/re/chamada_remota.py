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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("chamar")
    c.add_argument("func", type=lambda s: int(s, 0))
    c.add_argument("--ecx")
    c.add_argument("--args", nargs="*", type=lambda s: int(s, 0), default=[])
    r = sub.add_parser("ler")
    r.add_argument("addr", type=lambda s: int(s, 0))
    r.add_argument("size", type=lambda s: int(s, 0))
    a = parser.parse_args()
    _, handle = game()
    if a.cmd == "ler":
        data = read_memory(handle, a.addr, a.size)
        for i in range(0, len(data), 16):
            print(f"{a.addr + i:08X}  {data[i:i + 16].hex(' ')}")
        return
    result = run(handle, call_code(a.func, a.ecx, a.args))
    print(f"retorno: 0x{result:08X} ({result})")


if __name__ == "__main__":
    main()
