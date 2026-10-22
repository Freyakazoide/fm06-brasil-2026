from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import regens_futuros as rf  # noqa: E402


class RegensFuturosTest(unittest.TestCase):
    def test_engine_date(self) -> None:
        self.assertEqual(rf.engine_date("2010-03-15"), "15/03/1990")
        self.assertEqual(rf.engine_date("2008-02-29"), "28/02/1988")
        self.assertIsNone(rf.engine_date("15/03/2010"))

    def test_edt_lines(self) -> None:
        prospects = [rf.Prospect("Flamengo", "João", "da Silva", "Joãozinho", "2010-03-15"),
                     rf.Prospect("Palmeiras", "Juan", "Pérez", "", "2009-07-01", "Uruguai"),
                     rf.Prospect("Ibis", "Zé", "Ninguém", "", "2010-01-01"),
                     rf.Prospect("Flamengo", "Velho", "Demais", "", "1975-01-01"),
                     rf.Prospect("Flamengo", "Sem", "Data", "", "2010")]
        text, warnings = rf.edt_text(prospects, {"Flamengo": 322, "Palmeiras": 329})
        lines = text.splitlines()
        self.assertEqual(lines[1], '"FUTURE_REGEN"\t"João"\t"Joãozinho"\t"da Silva"\t"15/03/1990"\t"1651"\t"322"')
        self.assertEqual(lines[2], '"FUTURE_REGEN"\t"Juan"\t""\t"Pérez"\t"01/07/1989"\t"1657"\t"329"')
        self.assertEqual(len(lines), 3)
        self.assertEqual(len(warnings), 3)                       # clube, idade e data
        self.assertIn("\r\n", text)


if __name__ == "__main__":
    unittest.main()
