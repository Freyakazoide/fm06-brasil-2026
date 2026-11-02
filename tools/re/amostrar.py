"""Amostrador de tempo do fm_brasil.exe (ficha T1): onde o jogo gasta tempo numa ação.

    python tools\\re\\amostrar.py 20        (amostra por 20 s; faça a ação no jogo nesse tempo)

Para cada linha de execução do jogo, pausa, lê o EIP e a pilha, e solta, centenas de vezes por
segundo. Conta o EIP por função (início antes do EIP, pela pilha de int3) e cada endereço de
retorno da pilha uma vez por amostra (tempo inclusivo). Só lê; não grava nada no jogo.
"""

from __future__ import annotations

import ctypes
import struct
import sys
import time
from collections import Counter
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tools" / "re"))
from live_player_memory import find_process_id, kernel32, read_memory  # noqa: E402

TEXT_LO, TEXT_HI = 0x00401000, 0x00E00000
TH32CS_SNAPTHREAD, THREAD_ALL = 0x4, 0x001F03FF
WOW64_CONTEXT_CONTROL = 0x00010001
STACK_BYTES = 0x2000
IDLE = {0x00C68B0F, 0x00C68B63}                     # laço de mensagens parado (PeekMessage/espera)


class THREADENTRY32(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ThreadID", wintypes.DWORD),
                ("th32OwnerProcessID", wintypes.DWORD), ("tpBasePri", wintypes.LONG),
                ("tpDeltaPri", wintypes.LONG), ("dwFlags", wintypes.DWORD)]


k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
k32.OpenThread.restype = wintypes.HANDLE
k32.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.Wow64SuspendThread.argtypes = [wintypes.HANDLE]
k32.ResumeThread.argtypes = [wintypes.HANDLE]
k32.Wow64GetThreadContext.argtypes = [wintypes.HANDLE, ctypes.c_void_p]


def threads(pid: int) -> list[int]:
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    entry = THREADENTRY32()
    entry.dwSize = ctypes.sizeof(entry)
    out = []
    ok = k32.Thread32First(snap, ctypes.byref(entry))
    while ok:
        if entry.th32OwnerProcessID == pid:
            out.append(entry.th32ThreadID)
        ok = k32.Thread32Next(snap, ctypes.byref(entry))
    k32.CloseHandle(snap)
    return out


def code_bytes() -> bytes:
    import json
    game = Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"])
    sys.path.insert(0, str(ROOT / "src"))
    from fm06patch.exe_cave import off
    exe = (game / "fm.exe").read_bytes()
    return exe, off


def main() -> None:
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 20
    watch = [int(x, 16) for x in sys.argv[2:]]                  # retornos a mostrar sempre
    exe, off = code_bytes()

    def after_call(ret: int) -> bool:
        if not TEXT_LO <= ret < TEXT_HI or (ret & 0xFF00FF00) == 0:   # 0x00XX00YY: texto UTF-16
            return False
        o = off(ret)
        if exe[o - 5] == 0xE8:                                  # call rel32 para dentro do código
            return TEXT_LO <= ret + struct.unpack_from("<i", exe, o - 4)[0] < TEXT_HI
        return (exe[o - 6] == 0xFF and exe[o - 5] == 0x15) or (exe[o - 3] == 0xFF and 0x50 <= exe[o - 2] <= 0x57)             or (exe[o - 2] == 0xFF and (0xD0 <= exe[o - 1] <= 0xD7 or 0x10 <= exe[o - 1] <= 0x17))             or (exe[o - 6] == 0xFF and 0x90 <= exe[o - 5] <= 0x97)

    def func_start(eip: int) -> int:
        o = off(eip)
        i = exe.rfind(b"\xCC\xCC", o - 0x20000, o)
        return eip - (o - (i + 2)) if i > 0 else eip

    pid = find_process_id("fm_brasil.exe")
    process = kernel32.OpenProcess(0x0410 | 0x0008, False, pid)
    handles = {tid: k32.OpenThread(THREAD_ALL, False, tid) for tid in threads(pid)}
    ctx = ctypes.create_string_buffer(0x2CC)
    eips: dict[int, Counter] = {tid: Counter() for tid in handles}
    rets: dict[int, Counter] = {tid: Counter() for tid in handles}
    samples, idle = Counter(), Counter()
    print(f"amostrando {len(handles)} linhas por {seconds:.0f} s: faça a ação no jogo agora")
    end = time.time() + seconds
    while time.time() < end:
        for tid, h in handles.items():
            if k32.Wow64SuspendThread(h) == 0xFFFFFFFF:
                continue
            try:
                struct.pack_into("<I", ctx, 0, WOW64_CONTEXT_CONTROL)
                if not k32.Wow64GetThreadContext(h, ctx):
                    continue
                eip, esp = struct.unpack_from("<I", ctx, 0xB8)[0], struct.unpack_from("<I", ctx, 0xC4)[0]
                stack = read_memory(process, esp, STACK_BYTES) or b""
            finally:
                k32.ResumeThread(h)
            samples[tid] += 1
            found = [v for (v,) in struct.iter_unpack("<I", stack[: len(stack) // 4 * 4]) if after_call(v)]
            if TEXT_LO <= eip < TEXT_HI:
                eips[tid][func_start(eip)] += 1
            else:                                               # numa DLL: quem do jogo chamou
                eips[tid][-(found[0]) if found else 0] += 1
            if not TEXT_LO <= eip < TEXT_HI and found and found[0] in IDLE:
                idle[tid] += 1
                continue
            seen = set(found)
            for v in seen:
                rets[tid][v] += 1
        time.sleep(0.002)
    for tid in sorted(samples, key=lambda t: -(samples[t] - eips[t][0])):
        busy = samples[tid] - eips[tid][0]                      # 0: DLL sem retorno do jogo
        if busy < samples[tid] * 0.05:
            continue
        print(f"\nlinha {tid}: {samples[tid]} amostras, {busy} no código do jogo")
        print("  funções (EIP):")
        for f, n in eips[tid].most_common(20):
            print(f"    {'DLL via ' if f < 0 else ''}0x{abs(f):08X}: {n}")
        for r in watch:
            print(f"  vigiado 0x{r:08X}: {rets[tid][r]}")
        print("  retornos na pilha (inclusivo):")
        for r, n in rets[tid].most_common(40):
            print(f"    0x{r:08X}: {n}")


if __name__ == "__main__":
    main()
