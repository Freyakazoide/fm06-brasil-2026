import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import clubes_novos as cn  # noqa: E402

SERVER = ROOT / "workspace" / "baseline" / "server_db.original.dat"
pytestmark = pytest.mark.skipif(not SERVER.exists(), reason="sem o server_db original")


@pytest.fixture(scope="module")
def db():
    data = SERVER.read_bytes()
    return data, cn.club_list(data), cn.team_list(data)


def test_lists(db):
    data, clubs, teams = db
    assert (clubs.count_at, len(clubs.ends), clubs.end(len(clubs.ends) - 1)) == (0xB7C7F, 19218, 0x5B8590)
    assert (teams.count_at, len(teams.ends), teams.end(len(teams.ends) - 1)) == (0xF81D57, 19445, 0x129278B)
    assert clubs.uid(data, 198) == 322 and teams.uid(data, 290) == 322          # Flamengo
    n_at, m_at = cn.club_lists(data, clubs.start(198), clubs.ends[198])
    assert (data[n_at], struct.unpack_from("<I", data, n_at + 1)[0], data[m_at]) == (1, 290, 22)
    team = cn.parse_team(data, teams.start(290), teams.end(290))
    assert len(team.players) == 45 and team.end - team.tail_at == 57
    assert struct.unpack_from("<I", data, team.end - 8 - cn.TEAM_CLUB)[0] == 198


def test_add_club(db):
    data, clubs, teams = db
    team = cn.parse_team(data, teams.start(290), teams.end(290))
    club_bytes = cn.clone_club(data, clubs, 198, 9_000_001, "Clube Teste", "Teste", [len(teams.ends)])
    team_bytes = cn.clone_team(data, team, len(clubs.ends), len(teams.ends), 9_000_001)
    out = cn.add(data, clubs, teams, club_bytes, team_bytes)
    clubs2, teams2 = cn.club_list(out), cn.team_list(out)
    assert len(clubs2.ends) == 19219 and len(teams2.ends) == 19446
    new = len(clubs2.ends) - 1
    assert clubs2.uid(out, new) == 9_000_001 and teams2.uid(out, len(teams2.ends) - 1) == 9_000_001
    start, pair = clubs2.start(new), clubs2.ends[new]
    long_at, short_at, _ = cn.club_names(out, start, pair)
    assert out[long_at + 4:long_at + 4 + 22].decode("utf-16-le") == "Clube Teste"
    n_at, m_at = cn.club_lists(out, start, pair)
    assert struct.unpack_from("<BI", out, n_at) == (1, 19445) and out[m_at] == 0          # sem relações
    new_team = cn.parse_team(out, teams2.start(19445), teams2.end(19445))
    assert new_team.players == [] and struct.unpack_from("<I", out, new_team.end - 22)[0] == new
    assert clubs2.uid(out, 198) == 322 and teams2.uid(out, 290) == 322            # o resto não muda
