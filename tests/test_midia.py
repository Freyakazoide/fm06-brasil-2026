import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import midia  # noqa: E402

SERVER = ROOT / "workspace" / "baseline" / "server_db.original.dat"
SHEET = ROOT / "data" / "brasil" / "midia_2026.csv"
pytestmark = pytest.mark.skipif(not SERVER.exists(), reason="sem o server_db original")


def test_original_list():
    data = SERVER.read_bytes()
    at, sources = midia.locate(data)
    assert at == 0x5CA056 and len(sources) == midia.COUNT
    assert all(m.pack() == data[m.at:m.at + len(m.pack())] for m in sources)
    by_name = {m.name: m for m in sources}
    assert (by_name["London's Evening Standard"].scope, by_name["London's Evening Standard"].place) == (2, 100023)
    assert (by_name["The Guardian"].scope, by_name["The Guardian"].place) == (4, 765)
    assert by_name["O JOGO"].place == 788 and by_name["Skysports.com"].kind == 6
    assert [m.clubs for m in sources if m.name == "icLiverpool.com"] == [[676], [650]]


def test_add():
    data = SERVER.read_bytes()
    count_at, sources = midia.locate(data)
    end = sources[-1].at + len(sources[-1].pack())
    new = [midia.Media("Lance!", 6, 1, midia.COUNTRY, midia.BRAZIL, url="https://www.lance.com.br/"),
           midia.Media("O Globo", 1, 2, midia.CITY, 102498, [322, 323, 339, 316])]
    out, added = midia.add(data, new)
    assert len(added) == 2
    _, after = midia.locate(out)
    assert len(after) == midia.COUNT + 2
    assert after[-1].name == "O Globo" and after[-1].clubs == [322, 323, 339, 316] and after[-1].place == 102498
    assert after[-2].uid == midia.NEW_UID and after[-2].index == midia.COUNT
    assert out[after[-1].at + len(after[-1].pack()):] == data[end:]        # o resto do arquivo não muda
    again, none = midia.add(out, new)
    assert again == out and none == []


def test_sheet():
    cities = {"São Paulo": 102497, "Rio de Janeiro": 102498, "Belo Horizonte": 102499, "Porto Alegre": 102501,
              "Salvador": 102502, "Recife": 102500, "Fortaleza": 107174, "Curitiba": 102504}
    clubs = iter(range(1, 1000))
    wanted, problems = midia.load_sheet(SHEET, cities.get, lambda club: next(clubs))
    assert problems == [] and len(wanted) >= 20
    assert all(m.place == midia.BRAZIL for m in wanted if m.scope == midia.COUNTRY)
    assert {m.name for m in wanted} >= {"ge", "Lance!", "O Globo", "Zero Hora", "Placar"}
