import importlib.util
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import exe_patches, transferencias  # noqa: E402
from fm06patch.exe_cave import off, sec_off  # noqa: E402

EXE = ROOT / "workspace" / "rea" / "fm_602_original.exe"
SETUP = 0x00BB32A0


def _disasm(data, va, size):
    sys.path.insert(0, str(ROOT / "workspace" / "pydeps"))
    capstone = pytest.importorskip("capstone")
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    return list(md.disasm(data[off(va):off(va) + size], va))


def _pushes_before(ins, call_at):
    """Valores dos push entre a chamada anterior e a chamada em call_at, na ordem do código."""
    i = next(n for n, x in enumerate(ins) if x.address == call_at)
    out = []
    for x in reversed(ins[:i]):
        if x.mnemonic == "call":
            break
        if x.mnemonic == "push":
            v = int(x.op_str, 16)
            out.append(v - (1 << 32) if v >= 0x80000000 else v)
    return out[::-1]


@pytest.mark.skipif(not EXE.exists(), reason="sem o fm.exe original em workspace/rea")
def test_original_window_is_1_jan_to_26_sep():
    data = EXE.read_bytes()
    ins = _disasm(data, SETUP, 0x90)
    assert _pushes_before(ins, 0x00BB32EF) == [1, 1, -1, -1, 1, 2000, 8, 26, 0, 2000, 0, 1, 0]
    assert transferencias._window_args((1, 1), (26, 9)) == [1, 1, -1, -1, 1, 2000, 8, 26, 0, 2000, 0, 1, 0]


@pytest.mark.skipif(not EXE.exists(), reason="sem o fm.exe original em workspace/rea")
def test_two_windows_2026():
    data = EXE.read_bytes()
    out = exe_patches.apply(data, ["janelas_2026"])
    ins = _disasm(out, SETUP, 0x90)
    assert _pushes_before(ins, 0x00BB32EF) == transferencias._window_args((5, 1), (3, 3))
    site = next(x for x in ins if x.address == transferencias.NEXT_CALL_AT)
    assert site.mnemonic == "call" and int(site.op_str, 16) == transferencias.SECOND_STUB
    assert all(x.mnemonic == "nop" for x in ins if 0x00BB32F9 <= x.address < 0x00BB3301)
    stub_at = sec_off(transferencias.SECOND_STUB)
    sys.path.insert(0, str(ROOT / "workspace" / "pydeps"))
    capstone = pytest.importorskip("capstone")
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    stub = list(md.disasm(out[stub_at:stub_at + 0x40], transferencias.SECOND_STUB))
    calls = [x for x in stub if x.mnemonic == "call"]
    assert [int(c.op_str, 16) for c in calls] == [transferencias.WINDOW, transferencias.RULE]
    first = _pushes_before(stub, calls[0].address)
    assert first == transferencias._window_args((20, 7), (11, 9))
    assert _pushes_before(stub, calls[1].address) == [-1, 3, 4]
    assert stub[stub.index(calls[1]) + 1].mnemonic == "ret"


@pytest.mark.skipif(not EXE.exists(), reason="sem o fm.exe original em workspace/rea")
def test_applies_with_all_patches():
    spec = importlib.util.spec_from_file_location("aplicar", ROOT / "scripts" / "aplicar_brasil_2026.py")
    aplicar = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(aplicar)
    assert "janelas_2026" in aplicar.EXE_PATCHES
    out = exe_patches.apply(EXE.read_bytes(), aplicar.EXE_PATCHES)
    assert out[off(transferencias.NEXT_CALL_AT)] == 0xE8


@pytest.mark.skipif(not EXE.exists(), reason="sem o fm.exe original em workspace/rea")
def test_foreign_rules_2026():
    data = EXE.read_bytes()
    fixture = _disasm(data, 0x00BBA3B0, 0x30)
    assert _pushes_before(fixture, 0x00BBA3D6) == [0, -1, 3, 4]       # código 4, valor 3
    out = exe_patches.apply(data, ["janelas_2026", "estrangeiros_2026"])
    fixture = _disasm(out, 0x00BBA3B0, 0x30)
    assert _pushes_before(fixture, 0x00BBA3D6) == [0, -1, 9, 4]
    sys.path.insert(0, str(ROOT / "workspace" / "pydeps"))
    capstone = pytest.importorskip("capstone")
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    at = sec_off(transferencias.SECOND_STUB)
    stub = list(md.disasm(out[at:at + 0x40], transferencias.SECOND_STUB))
    calls = [x for x in stub if x.mnemonic == "call"]
    assert [int(c.op_str, 16) for c in calls] == [transferencias.WINDOW]
    after = stub[stub.index(calls[0]) + 1:]
    assert [x.mnemonic for x in after][:14] == ["nop"] * 13 + ["ret"]

