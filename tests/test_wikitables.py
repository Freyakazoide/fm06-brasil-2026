from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import wikitables  # noqa: E402

TABLE = """
==Champions==
{| class="wikitable"
! Season
! Champion
! Runner-up
|-
|[[2024 Campeonato Mineiro|2024]]
|[[Clube Atlético Mineiro|Atlético Mineiro]] <br>([[Belo Horizonte]])
|[[Cruzeiro Esporte Clube|Cruzeiro]] <br>([[Belo Horizonte]])
|-
|[[2025 Campeonato Mineiro|2025]]<ref>x</ref>
|{{flagicon|Minas Gerais}} [[Clube Atlético Mineiro|Atlético Mineiro]] (49)
|{{flagicon|Minas Gerais}} [[América Futebol Clube (MG)|América]]
|}
"""

FINALS = """
{| class="wikitable"
! Year !! Country !! Winner !! Score !! Runner-up !! Country
|-
|[[2025 Copa Libertadores|2025]] || {{BRA}} || [[Clube de Regatas do Flamengo|Flamengo]] || [[2025 Copa Libertadores final|1–0]] || [[Sociedade Esportiva Palmeiras|Palmeiras]] || {{BRA}}
|}
"""


class ChampionsTest(unittest.TestCase):
    def test_columns_by_header_skip_city_links(self):
        found = wikitables.champions(wikitables.section(TABLE, "==Champions=="))
        self.assertEqual(found[2024][0][:2], ("Atlético Mineiro", "Clube Atlético Mineiro"))
        self.assertEqual(found[2024][1][0], "Cruzeiro")
        self.assertEqual(found[2025][0][2], "Minas Gerais")
        self.assertEqual(found[2025][1][0], "América")

    def test_score_and_country_cells_are_not_teams(self):
        champ, runner = wikitables.champions(FINALS)[2025]
        self.assertEqual((champ[0], champ[2]), ("Flamengo", "BRA"))
        self.assertEqual(runner[0], "Palmeiras")


if __name__ == "__main__":
    unittest.main()
