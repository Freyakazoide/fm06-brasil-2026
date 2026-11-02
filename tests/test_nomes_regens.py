from __future__ import annotations

import struct
import sys
import unittest
from collections import Counter
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

    def test_new_names_take_uncited_slots_inside_the_block(self) -> None:
        first = _table([("Mohamed", 9, 0), ("Marcelo", 30, 0xBD), ("Rodrigo", 10, 0xBD), ("Zeca", 4, 0xBD),
                        ("Juan", 20, 0xBE)])
        second = _table([("Silva", 40, 0xBD)])
        common = _table([("Juninho", 5, 0xBD), ("Zé Carlos", 3, 0xBD)])
        data = b"HEAD" + first + second + common + b"TAIL"
        starts = {"first": 4, "second": 4 + len(first), "common": 4 + len(first) + len(second)}
        wanted = {("first", 0xBD): {"Enzo": 100, "Kauã": 10, "Rodrigo": 100},
                  ("common", 0xBD): {"Endrick": 50}}
        citations = {"first": Counter({1: 3, 2: 1}), "common": Counter({0: 1})}   # Zeca: ninguém cita
        changes = nr.plan(data, wanted, starts, citations)
        out = nr.apply(data, changes, starts)
        self.assertTrue(out.startswith(b"HEAD") and out.endswith(b"TAIL"))
        names, end = nr.read_table(out, 4)
        self.assertEqual([n.text for n in names], ["Mohamed", "Marcelo", "Rodrigo", "Enzo", "Juan"])
        self.assertEqual([n.index for n in names], [0, 1, 2, 3, 4])    # nada entra no fim
        self.assertEqual(names[3].uid, 1003)                             # o UID do lugar fica
        self.assertEqual(changes.dropped, ["Kauã (first, nação 189)"])   # sem vaga: o de menor peso
        brazil = [n.uses for n in names if n.nation == 0xBD]
        self.assertEqual(sum(brazil), 44)                                # a soma da nação não muda
        self.assertAlmostEqual((names[2].uses + names[3].uses) / 44, nr.NEW_SHARE, delta=0.05)
        self.assertEqual((names[0].uses, names[4].uses), (9, 20))        # outras nações iguais
        second_t, end2 = nr.read_table(out, end)
        common_t, _ = nr.read_table(out, end2)
        self.assertEqual([n.text for n in common_t], ["Juninho", "Endrick"])   # o composto deu lugar
        self.assertEqual(sum(n.uses for n in common_t), 8)

    def test_filler_names_are_stable(self) -> None:
        wanted = {("first", 0xBD): {"Enzo": 100, "Kauã": 50}, ("second", 0xBD): {"Souza": 100},
                  ("common", 0xBD): {"Vini": 100}}
        filler = nr.Filler(wanted)
        self.assertTrue(filler)
        self.assertEqual(filler.name(42), filler.name(42))
        first, common, second = filler.name(7)
        self.assertIn(first, ("Enzo", "Kauã"))
        self.assertEqual(second, "Souza")
        self.assertIn(common, ("", "Vini"))
        self.assertFalse(nr.Filler({}))


if __name__ == "__main__":
    unittest.main()
