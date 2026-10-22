from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from fm06patch.squad_builder import build, read_targets  # noqa: E402
from test_live_player import saviola  # noqa: E402


def hosts(count: int, goalkeepers: int) -> list[dict]:
    rows = []
    for i in range(count):
        rows.append({
            "uid": 1000 + i, "vinculo": "contrato", "nascido": "1980-01-01",
            "ca": 150 - i, "peso": 75,
            "posicoes": "Goalkeeper" if i < goalkeepers else "Attacker Center side",
        })
    return rows


class SquadBuilderTest(unittest.TestCase):

    def setUp(self) -> None:
        self.targets = read_targets(ROOT / "data/brasil/flamengo_2026.csv")

    def test_flamengo_sheet_is_valid(self) -> None:
        self.assertEqual(len(self.targets), 27)
        self.assertEqual(sum(t.is_goalkeeper for t in self.targets), 3)

    def test_goalkeepers_get_goalkeeper_hosts(self) -> None:
        _, spec, mapping, _ = build(self.targets, hosts(35, 4))
        gk_names = {t.display_name for t in self.targets if t.is_goalkeeper}
        for row in mapping:
            if row["jogador_2026"] in gk_names:
                self.assertLess(row["uid_hospedeiro"], 1004)
        self.assertEqual(len({p["uid"] for p in spec["players"]}), 27)

    def test_every_generated_player_is_writable(self) -> None:
        _, spec, _, _ = build(self.targets, hosts(35, 4))
        for entry in spec["players"]:
            player = saviola()
            player.plan(entry, year_shift=spec["year_shift"])
            for name, value in entry["attributes"].items():
                self.assertEqual(player.attribute_value(name), value, (entry["name"], name))

    def test_lnc_has_one_line_per_player(self) -> None:
        lnc, _, _, _ = build(self.targets, hosts(35, 4))
        self.assertEqual(lnc.count('"CHANGE_PLAYER_NAME"'), 27)

    def test_not_enough_hosts(self) -> None:
        with self.assertRaises(ValueError):
            build(self.targets, hosts(10, 1))


if __name__ == "__main__":
    unittest.main()
