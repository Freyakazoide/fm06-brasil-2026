from __future__ import annotations

import os
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch.brasil_2026 import SIZES, apply, plan  # noqa: E402
from fm06patch.server_teams import find_teams  # noqa: E402

SERVER_DB = os.environ.get("FM06_SERVER_DB")


@unittest.skipUnless(SERVER_DB and Path(SERVER_DB).exists(), "defina FM06_SERVER_DB com o server_db.dat original")
class Brasil2026Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = Path(SERVER_DB).read_bytes()
        cls.placements = plan(cls.data, ROOT / "data" / "brasil")

    def test_sizes_and_unique_clubs(self) -> None:
        self.assertEqual(Counter(p.serie for p in self.placements), SIZES)
        uids = [p.team.club_uid for p in self.placements]
        self.assertEqual(len(uids), len(set(uids)))

    def test_known_equivalents(self) -> None:
        found = {(p.serie, p.clube): p.team.short_name for p in self.placements}
        self.assertEqual(found[("A", "Athletico-PR")], "Atlético Paranaense")
        self.assertEqual(found[("A", "Mirassol")], "Mirassol")
        self.assertEqual(found[("D", "Tombense")], "Tombense")

    def test_database_counts_after_apply(self) -> None:
        counts = Counter(t.serie for t in find_teams(apply(self.data, self.placements), with_names=False))
        self.assertEqual(counts, {"A": 20, "B": 20, "NOVA_C": 20, "C": 96})


if __name__ == "__main__":
    unittest.main()
