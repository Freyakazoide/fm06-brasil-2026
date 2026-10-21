from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import nomes_regens as nr  # noqa: E402


def _table(names: list[tuple[str, int, int]]) -> bytes:
    body = b"".join(nr._record(text, uses, nation, i, 1000 + i) for i, (text, uses, nation) in enumerate(names))
    return struct.pack("<I", len(names)) + body


class NomesRegensTest(unittest.TestCase):
    def setUp(self) -> None:
        first = _table([("Mohamed", 9, 0), ("Marcelo", 30, 0xBD), ("Rodrigo", 10, 0xBD)])
        second = _table([("Silva", 40, 0xBD)])
        common = _table([("Juninho", 5, 0xBD)])
        self.data = b"HEAD" + first + second + common + b"TAIL"
        self.starts = {"first": 4, "second": 4 + len(first), "common": 4 + len(first) + len(second)}

    def test_appends_new_names_and_boosts_existing(self) -> None:
        wanted = {("first", 0xBD): {"Enzo": 100, "Rodrigo": 100}, ("common", 0xBD): {"Endrick": 50}}
        changes = nr.plan(self.data, wanted, self.starts)
        out = nr.apply(self.data, changes, self.starts)
        self.assertTrue(out.startswith(b"HEAD") and out.endswith(b"TAIL"))
        first, end = nr.read_table(out, 4)
        self.assertEqual([n.text for n in first], ["Mohamed", "Marcelo", "Rodrigo", "Enzo"])
        self.assertEqual([n.index for n in first], [0, 1, 2, 3])        # índice = posição
        self.assertEqual(first[3].nation, 0xBD)
        self.assertGreater(first[2].uses, 10)                            # Rodrigo ficou mais comum
        # os nomes novos somam ~70% do uso brasileiro
        new = first[2].uses + first[3].uses
        self.assertAlmostEqual(new / (new + 30), nr.NEW_SHARE, delta=0.05)
        second, end2 = nr.read_table(out, end)
        self.assertEqual([n.text for n in second], ["Silva"])
        common, _ = nr.read_table(out, end2)
        self.assertEqual([n.text for n in common], ["Juninho", "Endrick"])
        self.assertEqual(common[1].index, 1)
        self.assertEqual((first[3].uid, common[1].uid), (nr.NEW_UID, nr.NEW_UID + 1))   # UIDs novos, sem repetir


if __name__ == "__main__":
    unittest.main()
