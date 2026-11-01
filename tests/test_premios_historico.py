import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import historico, premios  # noqa: E402

SERVER = ROOT / "workspace" / "baseline" / "server_db.original.dat"
SHEET = ROOT / "data" / "modelos" / "premios_historico.xlsx"
pytestmark = pytest.mark.skipif(not SERVER.exists(), reason="sem o server_db original")


def test_original_list():
    data = SERVER.read_bytes()
    at, records = premios.locate(data)
    assert at == 0x1296FF5 and len(records) == 5362
    assert all(r.pack() == data[r.at:r.at + len(r.pack())] for r in records[:200] + records[-200:])
    golden = {r.year: r.names[0] for r in records if r.award == premios.GOLDEN_BALL}
    assert (golden[2004], golden[2003], golden[2002]) == ("Robinho", "Alex", "Kaká")
    scorer = [r for r in records if r.award == 131 and r.year == 2004][0]
    assert scorer.names[0] == "Washington" and scorer.numbers[0] == 34


def test_apply_shifts_and_appends():
    data = SERVER.read_bytes()
    winners = {2024: ("Estêvão", premios.NONE), 2025: ("Arrascaeta", 28628)}
    out, lines = premios.apply(data, winners)
    assert len(out) > len(data) and historico.find_list(out) > historico.find_list(data)
    _, records = premios.locate(out)
    assert len(records) == 5364
    golden = {r.year: r for r in records if r.award == premios.GOLDEN_BALL}
    assert golden[1984].names[0] == "Robinho"                       # 2004 na tela
    assert golden[2005].names[0] == "Arrascaeta" and golden[2005].people[0] == 28628
    assert golden[2004].people == (premios.NONE,) * 3 and golden[2004].names[0] == "Estêvão"
    assert all(r.year <= 1985 for r in records if r.award in premios.BRAZIL and r.uid < premios.NEW_UID)
    end = historico.find_list(data)
    assert out[historico.find_list(out):] == data[end:]               # o resto do arquivo não muda
    again, lines = premios.apply(out, winners)                          # rodar de novo não grava duas vezes
    assert again == out


def test_apply_unlinks_hosts():
    data = SERVER.read_bytes()
    out, _ = premios.apply(data, {}, gone={28921})                     # o Robinho de 2005 virou outro
    _, records = premios.locate(out)
    robinho = [r for r in records if r.award == premios.GOLDEN_BALL and r.names[0] == "Robinho"][0]
    assert robinho.people[0] == premios.NONE and robinho.year == 1984


@pytest.mark.skipif(not SHEET.exists(), reason="sem a planilha")
def test_sheet():
    winners = premios.load_sheet(SHEET)
    assert set(winners) == set(range(2006, 2026))
    assert winners[2025] == ("Arrascaeta", "Giorgian de Arrascaeta", "Flamengo")
    assert winners[2006][1:] == ("", "")
