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
