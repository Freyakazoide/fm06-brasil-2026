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


    def test_config_is_day_of_year_base_0(self) -> None:
        cfg = fornada.load_config()
        self.assertEqual((cfg.day, cfg.per_club, cfg.sieve_day), (5, 10, 181))   # 6/1, 10 por clube, 1/7

    def test_template_table_layout(self) -> None:
        table = fornada.template_table(count=8)
        self.assertEqual(len(table), 8 * fornada.RECORD)
        first = table[:fornada.RECORD]
        positions = first[:fornada.PLAYING_LAST - fornada.PLAYING_FIRST + 1][:25]   # 8..32
        self.assertTrue(all(1 <= b <= 20 for b in positions))
        self.assertEqual(first[79], 0)                             # livre entre o bloco e os movimentos

    def test_hook_calls_original_and_checks_the_day(self) -> None:
        base = 0x015BB000
        code = fornada.hook_code(base, [(5, base + 0x80, base + 0x300), (181, base + 0x5C00, base + 0x304)])
        self.assertEqual(code[:7], bytes.fromhex("56 8BF1 FF742408"))
        target = base + 7 + 5 + int.from_bytes(code[8:12], "little", signed=True)
        self.assertEqual(target, fornada.DAILY_TARGET)             # a rotina original continua
        self.assertIn(bytes.fromhex("3D05000000"), code)           # cmp eax, 5 (fornada)
        self.assertIn(bytes.fromhex("3DB5000000"), code)           # cmp eax, 181 (peneira)
        self.assertTrue(code.endswith(bytes.fromhex("5E C20400")))
        self.assertLessEqual(len(code), 0x80)                      # cabe antes do laço

    def test_sieve_chance_follows_recruitment(self) -> None:
        code = fornada.sieve_code(0x015C0C00, 0x015BB140, 0x015C0E00)
        self.assertIn(bytes.fromhex("8D0480 83E819"), code)        # 5c - 25
        self.assertIn(b"\x05" + fornada.SIEVE_BASE.to_bytes(4, "little"), code)   # PA 140 + sorteio


if __name__ == "__main__":
    unittest.main()
