from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import ano_exibido as ae  # noqa: E402


def _year4(value: int) -> int:
    """O que o desvio YEAR4 faz com o número antes do texto."""
    return value + 20 if value >= 1000 else value


class AnoExibidoTest(unittest.TestCase):
    def test_shared_list_widget_only_shifts_4_digit_years(self) -> None:
        # 0x00C9B2D7 é o texto do item de várias listas (temporada, idade e atributos do filtro)
        self.assertIn(0x00C9B2D7, ae.YEAR4_CALLS)
        self.assertNotIn(0x00C9B2D7, ae.YEAR_CALLS)
        self.assertEqual([_year4(v) for v in (15, 16, 20, 99, 2005)], [15, 16, 20, 99, 2025])

    def test_year4_stub_compares_with_1000(self) -> None:
        code = ae._year4_stub()
        self.assertTrue(code.startswith(bytes.fromhex("8B442408" "3DE8030000" "7C07" "83C014" "89442408")))
        self.assertEqual(code[-5], 0xE9)                     # jmp para o formatador original


if __name__ == "__main__":
    unittest.main()
