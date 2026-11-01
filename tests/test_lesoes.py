import datetime as dt
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import lesoes  # noqa: E402

SERVER = ROOT / "workspace" / "baseline" / "server_db.original.dat"
PEOPLE = ROOT / "workspace" / "baseline" / "people_db.original.dat"


def fake_db(rows):
    """rows: (pessoa, lesão, dia1, ano1, dia2, ano2) -> banco com só a lista."""
    rows = list(rows) + [(9, 9, 0, 1900, 0, 1900)] * 100       # a lista válida tem pelo menos 100
    body = b"".join(lesoes.Injury(p, k, (d1, y1), (d2, y2)).pack(i) for i, (p, k, d1, y1, d2, y2) in enumerate(rows))
    return b"\xaa" * 32 + struct.pack("<I", len(rows)) + body + b"\xbb" * 16


def test_add_fake():
    db = fake_db([(5, 11, 151, 2005, 221, 2005)])
    new = [lesoes.Injury(7, 25, (355, 2005), (45, 2006))]
    out, added = lesoes.add(db, new)
    assert added == new and len(out) == len(db) + lesoes.RECORD
    recs = lesoes.records(out)
    assert len(recs) == 102 and recs[-1] == new[0] and recs[0].person == 5
    assert out[-16:] == b"\xbb" * 16
    assert struct.unpack_from("<Ii", out, len(out) - 16 - 8) == (101, -1)
    again, added = lesoes.add(out, new)                         # rodar de novo não duplica
    assert again == out and added == []


def test_kind_of():
    assert lesoes.kind_of("lesão do menisco medial; artroscopia")[0] == 25
    assert lesoes.kind_of("cirurgia no calcanhar")[0] == 9         # "calcanhar" não é "lca"
    assert lesoes.kind_of("artroscopia no joelho esquerdo")[0] == 25
    assert lesoes.kind_of("recuperação de cirurgia na tíbia direita")[0] == 21
    assert lesoes.kind_of("ruptura do LCA")[0] == 27
    assert lesoes.kind_of("gripe") is None


def test_engine_date():
    assert lesoes.engine_date(dt.date(2025, 12, 22)) == (355, 2005)
    assert lesoes.engine_date(dt.date(2026, 1, 1)) == (0, 2006)
    assert lesoes.engine_date(dt.date(2028, 2, 29)) == (59, 2008)       # 2008 também é bissexto


@pytest.mark.skipif(not SERVER.exists(), reason="sem o server_db original")
def test_original_list():
    data = SERVER.read_bytes()
    assert lesoes.locate(data) == 0x13CE347
    recs = lesoes.records(data)
    assert len(recs) == 1225
    inzaghi = [r for r in recs if r.person == 317]
    assert inzaghi == [lesoes.Injury(317, 11, (151, 2005), (243, 2005))]
    out, added = lesoes.add(data, [lesoes.Injury(139156, 25, (355, 2005), (45, 2006))])
    assert len(added) == 1 and lesoes.records(out)[-1].person == 139156
    end = 0x13CE347 + 4 + 1225 * lesoes.RECORD
    assert out[end + lesoes.RECORD:] == data[end:]


@pytest.mark.skipif(not PEOPLE.exists(), reason="sem o people_db original")
def test_person_index():
    people = PEOPLE.read_bytes()
    assert lesoes.person_index(people, 811) == 317                 # Filippo Inzaghi
    assert lesoes.person_index(people, 114) == 71                  # Johan Mjällby


def test_latest_start_before_new_game():
    # New Game no dia 359 de 2005 do motor (26/12/2025); o Neymar (22/12) pegou, o Saúl (20/1) não
    assert lesoes.engine_date(lesoes.LATEST_START) < (359, 2005)
