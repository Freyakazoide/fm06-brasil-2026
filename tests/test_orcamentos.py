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


def test_clear_loans_keeps_budget_and_other_clubs():
    records = [(10, 900_000, 60, 1_000_000, 1), (11, 0, 0, 2000, 0), (12, 500_000, 42, 0, 1)] +               [(500 + i, 0, 0, 1000, 0) for i in range(120)] + [(77, 300_000, 30, 0, 1)]
    db = fake_db(records)
    out, cleared = orcamentos.clear_loans(db, {10, 11, 12})
    assert len(out) == len(db) and len(cleared) == 2
    table = {e.team: (e.loan, e.months, e.budget) for e in orcamentos.entries(out)}
    assert table[10] == (0, 0, 1_000_000) and table[12] == (0, 0, 0)
    assert table[77] == (300_000, 30, 0)


@pytest.mark.skipif(not ORIGINAL.exists(), reason="sem o server_db original")
def test_clear_loans_brazil_original():
    import csv

    data = ORIGINAL.read_bytes()
    ids = csv.DictReader((ROOT / "data" / "brasil" / "clubes" / "identidade_fm06.csv").open(encoding="utf-8-sig"))
    teams = {t for t in (orcamentos.team_index(data, int(r["uid_repo"])) for r in ids if r["uid_repo"]) if t}
    out, cleared = orcamentos.clear_loans(data, teams)
    before = {e.at: e for e in orcamentos.entries(data)}
    assert 290 in teams and any(e.team == 290 and before[e.at].loan == 22_500_000 for e in cleared)   # Flamengo
    assert all(e.loan == 0 for e in orcamentos.entries(out) if e.team in teams)
    assert sum(1 for e in orcamentos.entries(out) if e.loan) == 420 - len(cleared)



def test_wage_stub():
    from fm06patch import exe_patches
    from fm06patch.exe_cave import off, sec_off

    sys.path.insert(0, str(ROOT / "workspace" / "pydeps"))
    capstone = pytest.importorskip("capstone")
    exe = ROOT / "workspace" / "rea" / "fm_602_original.exe"
    if not exe.exists():
        pytest.skip("sem o exe original")
    data = exe.read_bytes()
    assert struct.unpack_from("<I", data, off(orcamentos.WAGE_SLOT_AT))[0] == orcamentos.WAGE_FORMULA
    out = exe_patches.apply(data, ["orcamento_salarial_folha"])
    assert struct.unpack_from("<I", out, off(orcamentos.WAGE_SLOT_AT))[0] == orcamentos.WAGE_STUB
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    at = sec_off(orcamentos.WAGE_STUB)
    ins = list(md.disasm(out[at:at + 0x40], orcamentos.WAGE_STUB))
    text = [f"{i.mnemonic} {i.op_str}".strip() for i in ins]
    assert text[:4] == ["push esi", "mov esi, ecx", "push dword ptr [esp + 8]", f"call {orcamentos.WAGE_FORMULA:#x}"]
    assert "mov eax, dword ptr [esi + 0x90]" in text and "imul eax, eax, 0xb" in text
    tail = [i.mnemonic for i in ins][text.index("cmp eax, ecx"):][:5]
    assert tail == ["cmp", "jge", "mov", "pop", "ret"]


def _run_stub(formula, payroll):
    """O que o desvio devolve, em Python (mesma conta)."""
    return max(formula, payroll * orcamentos.WAGE_MARGIN // 10)


def test_wage_rule():
    assert _run_stub(413_803, 520_578) == 572_635          # Flamengo de 27/10: sobe para a folha + 10%
    assert _run_stub(341_132, 100_000) == 341_132          # fórmula maior fica
