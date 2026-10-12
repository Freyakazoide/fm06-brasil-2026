from __future__ import annotations

import os
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch.server_teams import DIVISIONS, find_team, find_teams, write_team  # noqa: E402

SERVER_DB = os.environ.get("FM06_SERVER_DB")


@unittest.skipUnless(SERVER_DB and Path(SERVER_DB).exists(), "defina FM06_SERVER_DB com o server_db.dat original")
class ServerTeamsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = Path(SERVER_DB).read_bytes()
        cls.teams = find_teams(cls.data)

    def test_divisions_have_the_expected_sizes(self) -> None:
        counts = {key: sum(t.division == value for t in self.teams) for key, value in DIVISIONS.items()}
        self.assertEqual(counts, {"A": 20, "B": 20, "C": 128})

    def test_known_clubs(self) -> None:
        santos = find_team(self.teams, "Santos")
        self.assertEqual((santos.club_uid, santos.serie, santos.last_position), (334, "A", 1))
        self.assertEqual(find_team(self.teams, "Tubarão").serie, "C")
        self.assertEqual(find_team(self.teams, "321").short_name, "Flamengo")

    def test_write_changes_only_the_record(self) -> None:
        team = find_team(find_teams(self.data), "Flamengo")
        team.division = DIVISIONS["C"]
        team.last_position = 3
        buffer = bytearray(self.data)
        write_team(buffer, team)
        diff = [i for i, (a, b) in enumerate(zip(self.data, buffer)) if a != b]
        self.assertTrue(diff)
        self.assertGreaterEqual(min(diff), team.offset)
        self.assertLess(max(diff), team.offset + 15)
        self.assertEqual(struct.unpack_from("<I", buffer, team.offset + 7)[0], DIVISIONS["C"])
        self.assertEqual(find_team(find_teams(bytes(buffer)), "Flamengo").serie, "C")


if __name__ == "__main__":
    unittest.main()
