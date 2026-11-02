from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import fornada  # noqa: E402


class FornadaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.types = {t.name: t for t in fornada.load_types()}

    def test_sheet_loads_every_type(self) -> None:
        self.assertGreaterEqual(len(self.types), 10)
        self.assertTrue(all(t.weight > 0 and t.positions and t.feet for t in self.types.values()))

    def test_positions_fill_general_and_side(self) -> None:
        model = fornada.build(self.types["Zagueiro clássico"], random.Random(3))
        p = model.playing
        self.assertEqual((p[21], p[10], p[19]), (20, 20, 20))      # DC, zagueiro, centro
        self.assertGreaterEqual(p[22], 8)                          # DD secundária
        self.assertEqual(p[8], 1)                                  # não é goleiro
        self.assertTrue(all(1 <= p[rel] <= 20 for rel in fornada.POSITION_RELS))

    def test_outfield_player_is_bad_in_goal_and_goalkeeper_is_good(self) -> None:
        attrs = {a.name: a for a in fornada.load_attributes().values()}
        handling = attrs["Handling"].rel
        signed = lambda b: b - 256 if b > 127 else b
        outfield = fornada.build(self.types["Meia armador"], random.Random(5))
        keeper = fornada.build(self.types["Goleiro"], random.Random(5))
        self.assertLess(signed(outfield.playing[handling]), -25)
        self.assertGreater(signed(keeper.playing[handling]), 0)

    def test_moves_come_from_the_type(self) -> None:
        kind = self.types["Ponta direita driblador"]
        for seed in range(30):
            model = fornada.build(kind, random.Random(seed))
            self.assertLessEqual(len(model.traits), 3)
            self.assertTrue(set(model.traits) <= set(kind.traits))
            self.assertEqual(bin(int.from_bytes(model.moves, "little")).count("1"), len(model.traits))

    def test_same_seed_same_player(self) -> None:
        kind = self.types["Atacante móvel"]
        a, b = (fornada.build(kind, random.Random(9)) for _ in range(2))
        self.assertEqual((a.playing, a.moves), (b.playing, b.moves))


if __name__ == "__main__":
    unittest.main()
