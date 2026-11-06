r"""Pausa no laço principal do jogo: o Python só mexe no jogo com a thread principal parada num ponto seguro.

Por quê (crash de 03/11, dump 21.02.52): o leitor de textos chamava 0xC50A00/0xC50B30 (string do
jogo) de uma thread remota ao mesmo tempo que a thread principal; a lista livre do alocador de
strings (0xC67270, cabeça em [esi+0x18]) ficou com "dive" (0x65766964) no lugar de um ponteiro e a
tela de Notícias caiu ao liberar uma string (0x4DBC28). Esse alocador não é para duas threads.

Laço principal (0xC68A50): PeekMessage/Translate/Dispatch, depois 0xC68B34 `mov ecx,[0x14EDD08]` e
o quadro do jogo (`call [edx+4]`), depois espera mensagem. O gancho troca 0xC68B34 por um jmp para
uma página nossa: se PARK != 0, marca PARKED = 1 e espera PARK voltar a 0; depois refaz a instrução
original e volta para 0xC68B3A. Nesse ponto a thread principal não está no meio de nenhum quadro.
O jmp é gravado com todas as threads do jogo suspensas (o EIP de uma thread suspensa só pode estar
no início de 0xC68B34, que vira o jmp inteiro, ou em 0xC68B3A, que não muda).

2º crash (06/11, dumps 07.52.16/17): mesmo ponto, com "text" na lista livre, mesmo com a pausa. Cada
pedaço do alocador é {etiqueta, valor} e o ponteiro da lista livre ocupa a etiqueta: um pedaço liberado
duas vezes, ou liberado e ainda em uso, dá isso. Causa ainda não provada. Fechadas três brechas: o
código nosso roda na própria thread principal (`run_on_main`, não mais em thread remota); a pausa só
vale no laço de fora (esp igual ao maior visto; o laço pode rodar dentro de um processamento); e o
servidor só age com o jogo parado por 6 s.

    python tools\re\laco.py estado | instalar | desfazer
"""

from __future__ import annotations

import ctypes
import struct
import sys
import time
from contextlib import contextmanager
from ctypes import wintypes
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chamada_remota as cr  # noqa: E402

k32 = cr.kernel32
HOOK_AT, RESUME_AT, FRAME_OBJ = 0x00C68B34, 0x00C68B3A, 0x014EDD08
ORIGINAL = bytes.fromhex("8B0D08DD4E01")                                 # mov ecx, [0x14EDD08]
SIGNATURE = b"FM06LAC4"
PARK, PARKED, JOB, STACK, CODE, JOB_CODE = 0x10, 0x14, 0x18, 0x1C, 0x20, 0x100   # deslocamentos na página

TH32CS_SNAPTHREAD, THREAD_SUSPEND_RESUME = 0x00000004, 0x0002


class THREADENTRY32(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ThreadID", wintypes.DWORD),
                ("th32OwnerProcessID", wintypes.DWORD), ("tpBasePri", ctypes.c_long),
                ("tpDeltaPri", ctypes.c_long), ("dwFlags", wintypes.DWORD)]


k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
k32.OpenThread.restype = wintypes.HANDLE
k32.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]
k32.FlushInstructionCache.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t]


def read(handle, address: int, size: int) -> bytes:
    buf, got = ctypes.create_string_buffer(size), ctypes.c_size_t()
    if not k32.ReadProcessMemory(handle, ctypes.c_void_p(address), buf, size, ctypes.byref(got)):
        raise OSError(ctypes.get_last_error(), f"leitura falhou em 0x{address:08X}")
    return buf.raw


def cave_code(page: int) -> bytes:
    park, parked, job, stack = (page + x for x in (PARK, PARKED, JOB, STACK))
    is_parked = b"\x83\x3D" + park.to_bytes(4, "little") + b"\x00"        # cmp dword [park], 0
    # JOB é um byte: WriteProcessMemory não é atômica, e um ponteiro de 4 bytes foi lido pela metade
    # (dumps 07.58.19 e 08.01.00: 0x023F0100 virou 0x003F0100).
    run_job = b"\x6A\x00\xB8" + (page + JOB_CODE).to_bytes(4, "little") + b"\xFF\xD0"   # push 0; mov eax, código; call eax
    run_job += b"\xC6\x05" + job.to_bytes(4, "little") + b"\x00"          # mov byte [job], 0
    spin = b"\xF3\x90" + b"\x80\x3D" + job.to_bytes(4, "little") + b"\x00"   # spin: pause; cmp byte [job], 0
    spin += b"\x74" + bytes([len(run_job)]) + run_job + is_parked         # jz sem_job; job; sem_job: cmp
    spin += b"\x75" + bytes([(-(len(spin) + 2)) & 0xFF])                  # jne spin
    body = b"\x60\x89\x25" + stack.to_bytes(4, "little")                 # pushad; mov [stack], esp
    body += b"\xC7\x05" + parked.to_bytes(4, "little") + (1).to_bytes(4, "little")  # mov [parked], 1
    body += spin + b"\xC7\x05" + parked.to_bytes(4, "little") + bytes(4) + b"\x61"  # [parked] = 0; popad
    c = bytearray(SIGNATURE) + bytes(CODE - len(SIGNATURE))
    c += is_parked + b"\x74" + bytes([len(body)]) + body                  # je done
    c += ORIGINAL                                                         # done: mov ecx, [0x14EDD08]
    jmp_from = page + len(c) + 5
    c += b"\xE9" + ((RESUME_AT - jmp_from) & 0xFFFFFFFF).to_bytes(4, "little")
    return bytes(c)


def _threads(pid: int) -> list[int]:
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    entry, out = THREADENTRY32(), []
    entry.dwSize = ctypes.sizeof(THREADENTRY32)
    try:
        ok = k32.Thread32First(snap, ctypes.byref(entry))
        while ok:
            if entry.th32OwnerProcessID == pid:
                out.append(entry.th32ThreadID)
            ok = k32.Thread32Next(snap, ctypes.byref(entry))
    finally:
        k32.CloseHandle(snap)
    return out


def _write_frozen(pid: int, handle, address: int, data: bytes) -> None:
    """Grava código com todas as threads do jogo suspensas."""
    held = []
    try:
        for tid in _threads(pid):
            th = k32.OpenThread(THREAD_SUSPEND_RESUME, False, tid)
            if th and k32.SuspendThread(th) != 0xFFFFFFFF:
                held.append(th)
            elif th:
                k32.CloseHandle(th)
        cr.poke(handle, address, data)
        k32.FlushInstructionCache(handle, ctypes.c_void_p(address), len(data))
    finally:
        for th in held:
            k32.ResumeThread(th)
            k32.CloseHandle(th)


def page_of(handle) -> int | None:
    """Página do gancho se ele está instalado (jmp em 0xC68B34 para uma página com a assinatura)."""
    code = read(handle, HOOK_AT, 6)
    if code == ORIGINAL:
        return None
    if code[0] != 0xE9:
        raise RuntimeError(f"0x{HOOK_AT:08X} tem bytes inesperados: {code.hex()}")
    target = (HOOK_AT + 5 + struct.unpack_from("<i", code, 1)[0]) & 0xFFFFFFFF
    page = target - CODE
    if read(handle, page, len(SIGNATURE)) != SIGNATURE:
        raise RuntimeError(f"jmp em 0x{HOOK_AT:08X} não leva ao gancho do laço")
    return page


def install(pid: int, handle) -> int:
    page = page_of(handle)
    if page:
        return page
    page = k32.VirtualAllocEx(handle, None, 0x1000, cr.MEM_COMMIT_RESERVE, cr.PAGE_EXECUTE_READWRITE)
    if not page:
        raise OSError(ctypes.get_last_error(), "VirtualAllocEx falhou")
    cr.poke(handle, page, cave_code(page))
    jmp = b"\xE9" + ((page + CODE - (HOOK_AT + 5)) & 0xFFFFFFFF).to_bytes(4, "little") + b"\x90"
    _write_frozen(pid, handle, HOOK_AT, jmp)
    return page


def uninstall(pid: int, handle) -> None:
    page = page_of(handle)
    if page:
        cr.poke(handle, page + PARK, bytes(4))
        _write_frozen(pid, handle, HOOK_AT, ORIGINAL)                    # a página fica (pode estar em uso)


_outer_stack: dict[int, int] = {}                                        # página -> maior esp visto


@contextmanager
def parked(pid: int, handle, timeout: float = 3.0):
    """Para a thread principal no laço e só entra no bloco quando ela confirmou que parou, no laço de
    fora. Se não der (quadro longo, ou laço interno de um processamento), levanta TimeoutError sem
    mexer em nada."""
    page = install(pid, handle)
    cr.poke(handle, page + PARK, (1).to_bytes(4, "little"))
    try:
        end = time.monotonic() + timeout
        while read(handle, page + PARKED, 4) != (1).to_bytes(4, "little"):
            if time.monotonic() > end:
                raise TimeoutError("a thread principal do jogo não parou no laço")
            time.sleep(0.005)
        stack = struct.unpack("<I", read(handle, page + STACK, 4))[0]
        outer = _outer_stack[page] = max(stack, _outer_stack.get(page, 0))
        if stack != outer:
            raise TimeoutError(f"laço interno (esp 0x{stack:08X}, fora 0x{outer:08X})")
        yield
    finally:
        cr.poke(handle, page + PARK, bytes(4))


def run_on_main(handle, code: bytes, timeout: float = 10.0) -> None:
    """Roda `code` (ret 4, como os de chamada_remota) na thread principal parada. Só dentro de `parked`."""
    page = page_of(handle)
    if not page or read(handle, page + PARKED, 4) != (1).to_bytes(4, "little"):
        raise RuntimeError("a thread principal não está parada")
    if len(code) > 0x1000 - JOB_CODE:
        raise ValueError("código grande demais para a página do gancho")
    if read(handle, page + JOB, 1) != b"\x00":
        raise RuntimeError("ainda há uma função rodando na thread principal")
    cr.poke(handle, page + JOB_CODE, code)
    k32.FlushInstructionCache(handle, ctypes.c_void_p(page + JOB_CODE), len(code))
    cr.poke(handle, page + JOB, b"\x01")
    end = time.monotonic() + timeout
    while read(handle, page + JOB, 1) != b"\x00":
        if time.monotonic() > end:
            raise RuntimeError("a função não voltou na thread principal")
        time.sleep(0.001)


def main() -> None:
    pid, handle = cr.game()
    action = sys.argv[1] if len(sys.argv) > 1 else "estado"
    if action == "instalar":
        print(f"gancho em 0x{install(pid, handle):08X}")
    elif action == "desfazer":
        uninstall(pid, handle)
        print("desfeito")
    elif action == "teste":
        start = time.monotonic()
        with parked(pid, handle):
            print(f"thread principal parada em {1000 * (time.monotonic() - start):.0f} ms")
            page = page_of(handle)
            print(f"esp 0x{struct.unpack('<I', read(handle, page + STACK, 4))[0]:08X}")
            run_on_main(handle, b"\x33\xC0\xC2\x04\x00")                   # xor eax, eax; ret 4
            print("função vazia rodou na thread principal")
        print("liberada")
    page = page_of(handle)
    print(f"0x{HOOK_AT:08X}: {read(handle, HOOK_AT, 6).hex()} ({'gancho em 0x%08X' % page if page else 'original'})")


if __name__ == "__main__":
    main()
