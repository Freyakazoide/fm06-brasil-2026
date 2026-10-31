import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import exe_patches, premiacao  # noqa: E402
from fm06patch.copa_do_brasil import BUILDER  # noqa: E402
from fm06patch.exe_cave import off, sec_off  # noqa: E402

EXE = ROOT / "workspace" / "rea" / "fm_602_original.exe"
SHEET = ROOT / "data" / "modelos" / "premiacao_2026.xlsx"
SETTER = 0x00B3BA80


@pytest.mark.skipif(not EXE.exists(), reason="sem o fm.exe original em workspace/rea")
def test_pushes_are_setter_args_in_original():
    """Cada posição é um push imm32 com o valor de 2005, e o setter vem logo depois dos três
    push (o 1º push é o +0x48, o 3º o +0x40)."""
    data = EXE.read_bytes()
    for _, at, old, _, _ in premiacao.COPA_2026:
        va = BUILDER + at
        assert data[off(va):off(va) + 5] == b"\x68" + struct.pack("<I", old), hex(va)
    final = BUILDER + premiacao.F_LOSER_AT
    assert data[off(final - 1)] == 0x53                     # push ebx (+0x48 = 0)
    call = data.find(b"\xE8", off(BUILDER + premiacao.F_WINNER_AT + 5))
    assert call - off(BUILDER) < premiacao.F_WINNER_AT + 0x30
    rel = struct.unpack_from("<i", data, call + 1)[0]
    assert call + 5 + rel == off(SETTER)


@pytest.mark.skipif(not EXE.exists(), reason="sem o fm.exe original em workspace/rea")
def test_applies_after_copa():
    data = EXE.read_bytes()
    out = exe_patches.apply(data, ["copa_do_brasil_2026", "premiacao_copa_2026"])
    from fm06patch.copa_do_brasil import S1
    at = sec_off(S1 + premiacao.F_WINNER_AT)
    assert out[at:at + 5] == b"\x68" + struct.pack("<I", round(78_000_000 / 5.08))


@pytest.mark.skipif(not SHEET.exists(), reason="sem a planilha de premiação")
def test_values_match_sheet():
    import openpyxl

    rows = openpyxl.load_workbook(SHEET, read_only=True, data_only=True)["Premiacao"].iter_rows(values_only=True)
    header = next(rows)
    sheet = {(r[0], r[2]): r[3] for r in rows if r[0] == "Copa do Brasil"}
    assert header[:4] == ("competicao", "temporada", "fase_ou_posicao", "valor")
    for _, _, _, brl, label in premiacao.COPA_2026:
        assert sheet[("Copa do Brasil", label)] == brl, label


@pytest.mark.skipif(not EXE.exists(), reason="sem o fm.exe original em workspace/rea")
def test_serie_b_quota_slot():
    data = EXE.read_bytes()
    slot = off(premiacao.SERIE_B_VTABLE + 0x128)
    assert struct.unpack_from("<I", data, slot)[0] == premiacao.SERIE_B_QUOTA_OLD
    out = exe_patches.apply(data, ["cota_serie_b_2026"])
    assert struct.unpack_from("<I", out, slot)[0] == premiacao.SERIE_B_QUOTA
    stub = sec_off(premiacao.SERIE_B_QUOTA)
    assert out[stub:stub + 8] == b"\xB8" + struct.pack("<I", round(14_900_000 / 5.08)) + b"\xC2\x04\x00"
    assert out[off(premiacao.SERIE_B_QUOTA_OLD):off(premiacao.SERIE_B_QUOTA_OLD) + 5] == bytes.fromhex("b890d00300")


def test_serie_b_uids():
    uids = premiacao.serie_b_uids()
    assert len(uids) == 20 and len(set(uids)) == 20
    assert 102555 in uids                                   # Goiás


@pytest.mark.skipif(not EXE.exists(), reason="sem o fm.exe original em workspace/rea")
def test_first_quota_after_sponsor():
    sys.path.insert(0, str(ROOT / "workspace" / "pydeps"))
    capstone = pytest.importorskip("capstone")

    from fm06patch.patrocinio import PAY_STUB, _pay_stub

    data = EXE.read_bytes()
    out = exe_patches.apply(data, ["patrocinio_inicio", "cota_serie_b_2026", "cota_serie_b_inicio"])
    ret_at = PAY_STUB + len(_pay_stub()) - 1
    at = sec_off(ret_at)
    assert out[at] == 0xE9
    assert ret_at + 5 + struct.unpack_from("<i", out, at + 1)[0] == premiacao.FIRST_QUOTA
    stub = sec_off(premiacao.FIRST_QUOTA)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    ins = list(md.disasm(out[stub:stub + 0x50], premiacao.FIRST_QUOTA))
    fim = next(i.address for i in ins if i.mnemonic == "ret")
    for i in ins:
        if i.mnemonic in ("je", "jne"):
            target = int(i.op_str, 16)
            assert target == fim or any(j.address == target for j in ins), i
        if i.address == fim:
            break
    text = " | ".join(f"{i.mnemonic} {i.op_str}" for i in ins if i.address <= fim)
    assert f"push 0x{round(14_900_000 / 5.08):x}" in text
    assert "call dword ptr [eax + 0x98]" in text
    table = sec_off(premiacao.FIRST_QUOTA_TABLE)
    uids = struct.unpack_from("<21I", out, table)
    assert list(uids[:20]) == premiacao.serie_b_uids() and uids[20] == 0
