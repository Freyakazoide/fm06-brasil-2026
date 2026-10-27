import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import orcamentos  # noqa: E402

ORIGINAL = ROOT / "workspace" / "baseline" / "server_db.original.dat"


def fake_db(records):
    """records: (time, empréstimo, meses, orçamento, tipo) -> banco com só a tabela."""
    body = b"".join(struct.pack("<BIIHIBIi", 0, *rec, i, -1) for i, rec in enumerate(records))
    return b"\xaa" * 32 + struct.pack("<I", len(records)) + body + b"\xbb" * 16


def test_two_records_become_one_and_the_spare_goes_to_a_club_without(monkeypatch):
    records = [(10, 0, 0, 50_000, 0)] + [(500 + i, 0, 0, 1000, 0) for i in range(120)] + [(10, 900_000, 60, 0, 1)]
    db = fake_db(records)
    teams = {1: 10, 2: 77}
    monkeypatch.setattr(orcamentos, "team_index", lambda data, repo: teams[repo])
    result = orcamentos.plan(db, {1: 5.08e6, 2: 2.54e6})
    out = orcamentos.apply(db, result.changes)
    assert len(out) == len(db) and not result.missing
    table = {(e.team, e.loan, e.budget) for e in orcamentos.entries(out)}
    assert (10, 900_000, 1_000_000) in table           # orçamento foi para o registro do empréstimo
    assert (77, 0, 500_000) in table                   # o que sobrou foi para o clube sem registro
    assert not any(e.team == 10 and e.loan == 0 for e in orcamentos.entries(out))
    assert sum(1 for e in orcamentos.entries(out) if e.budget == 1000) == 120   # os outros não mudam


def test_without_spare_the_club_is_reported(monkeypatch):
    db = fake_db([(500 + i, 0, 0, 1000, 0) for i in range(120)])
    monkeypatch.setattr(orcamentos, "team_index", lambda data, repo: 77)
    result = orcamentos.plan(db, {2: 1e6})
    assert result.missing == [2] and not result.changes


@pytest.mark.skipif(not ORIGINAL.exists(), reason="sem o server_db original em workspace/baseline")
def test_original_table():
    """Corinthians 287 (£4,7 mi) e Flamengo 290 (£50 mil e o empréstimo de £22,5 mi): os valores
    do New Game de 27/10. Chelsea 544 (£100 mi)."""
    data = ORIGINAL.read_bytes()
    assert orcamentos.locate(data) == 0x13D8555
    table = orcamentos.entries(data)
    assert len(table) == 3536
    assert orcamentos.team_index(data, 317) == 287 and orcamentos.team_index(data, 321) == 290
    by_team = {}
    for entry in table:
        by_team.setdefault(entry.team, []).append((entry.loan, entry.months, entry.budget))
    assert by_team[287] == [(0, 0, 4_700_000)]
    assert sorted(by_team[290]) == [(0, 0, 50_000), (22_500_000, 103, 0)]
    assert (0, 0, 100_000_000) in by_team[544]
