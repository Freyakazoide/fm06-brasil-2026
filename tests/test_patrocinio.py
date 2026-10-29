import datetime as dt
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import patrocinio  # noqa: E402

ORIGINAL = ROOT / "workspace" / "baseline" / "server_db.original.dat"


def test_contract_bytes():
    """Flamengo no New Game de 27/10: £1.912.500, fim no dia 212 de 2008 ("2028"), 5 anos."""
    contract = patrocinio.Contract(1_912_500 * 5.08, dt.date(2028, 7, 31), 5)
    assert contract.pack() == bytes.fromhex("00000000 b42e1d00 d400 d807 05")


@pytest.mark.skipif(not ORIGINAL.exists(), reason="sem o server_db original em workspace/baseline")
def test_insert_after_finances():
    data = ORIGINAL.read_bytes()
    at = patrocinio.flag_at(data, 321)                       # Flamengo
    assert struct.unpack_from("<I", data, at)[0] == 0
    contract = patrocinio.Contract(268_500_000, dt.date(2028, 12, 31), 3)
    out, kept = patrocinio.apply(data, {321: contract, 317: contract})
    assert not kept and len(out) == len(data) + 2 * 13
    at = patrocinio.flag_at(out, 321)
    assert struct.unpack_from("<I", out, at)[0] == 1
    assert out[at + 4:at + 17] == contract.pack()
    assert out[at + 17:at + 21] == data[patrocinio.flag_at(data, 321) + 4:patrocinio.flag_at(data, 321) + 8]
    _, kept = patrocinio.apply(out, {321: contract})
    assert kept == [321]                                     # não grava duas vezes


def test_pay_stub_jumps_land_on_ret():
    """Os dois saltos do desvio caem no ret (um byte antes travaria o New Game)."""
    code = patrocinio._pay_stub()
    ret = code.index(b"\xC3", len(code) - 1)
    je, jne = code.index(bytes.fromhex("85C074")) + 2, code.index(bytes.fromhex("837E7C0075")) + 4
    assert je + 2 + code[je + 1] == ret and jne + 2 + code[jne + 1] == ret
