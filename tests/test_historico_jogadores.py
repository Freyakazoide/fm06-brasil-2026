from __future__ import annotations

import os
import struct
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import historico_jogadores as hj  # noqa: E402

HEADER_INDEX = b"\x02\x01tad.\x27\x01\x00"
HEADER = b"\x02\x01tad.\x01\x00\x00"
PL_HIST = os.environ.get("FM06_PL_HIST", str(ROOT / "workspace" / "baseline"))   # pasta com os originais


def _files(players: list[tuple[int, list[list[tuple]]]]) -> tuple[bytes, bytes, bytes]:
    """[(UID, [bloco, ...])] com bloco = [(ano, empréstimo, jogos, gols, valor, clube), ...]."""
    entries, ids, dt, at, slot = [], b"", b"", 0, 0
    for uid, blocks in players:
        for block in blocks:
            entries.append((uid, slot))
            slot += 1
            ids += struct.pack("<II", at, at + 17 * (len(block) - 1))
            for i, record in enumerate(block):
                at += 17
                dt += struct.pack("<HBBBIII", *record, at if i < len(block) - 1 else hj.NONE)
    index = HEADER_INDEX + struct.pack("<I", len(entries)) + b"".join(struct.pack("<II", *e) for e in entries)
    return index, HEADER + ids, HEADER + dt


def _clubs() -> hj.Clubs:
    names = {1478: ("Futebol Clube do Porto, SAD", "Porto"), 1489: ("Sporting Clube de Portugal, SAD", "Sporting CP"),
             1747: ("Real Betis Balompié S.A.D.", "Betis"), 314617: ("Flamengo EC", "Flamengo (PI)"),
             1745: ("Real Sporting de Gijón B", "Sporting B"), 1099: ("AC Milan", "Milan"),
             865: ("Lyon", "Lyon"), 102852: ("Al Hilal (KSA)", "Al Hilal (KSA)"),
             5626530: ("Al Hilal Hudayda", "Al Hilal Hudayda"), 476: ("Sparta Prag", "Sparta Prag")}
    refs = Counter({1478: 500, 1489: 600, 1745: 270, 1099: 800, 865: 470, 102852: 257, 5626530: 5, 476: 300,
                    1747: 400, 314617: 3})
    return hj.Clubs(names, refs, {"Flamengo": 322, "Porto": 104000, "Atlético-MG": 316})


class HistoryFileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = _files([
            (29, [[(2001, 1, 255, 255, hj.NONE, 10)], [(1995, 0, 20, 3, hj.NONE, 11)]]),   # dois blocos
            (3100367, [[(2003, 0, 32, 14, hj.NONE, 1708), (2004, 1, 29, 8, hj.NONE, 826)]]),
            (3300977, [[(2004, 0, 65, 5, hj.NONE, 337)]]),
        ])

    def test_round_trip_is_byte_identical(self) -> None:
        self.assertEqual(hj.History(*self.raw).files(), self.raw)

    def test_career_joins_blocks_in_year_order(self) -> None:
        career = hj.History(*self.raw).career(29)
        self.assertEqual([(s.year, s.club, s.loan) for s in career], [(1995, 11, False), (2001, 10, True)])
        self.assertEqual(hj.History(*self.raw).career(3100367)[1], hj.Season(2004, 826, 29, 8, True))

    def test_replace_removes_adds_and_renumbers(self) -> None:
        history = hj.History(*self.raw)
        history.replace({29: [], 3200000: [hj.Season(2004, 322, 30, 2), hj.Season(2003, 337, 10)]})
        again = hj.History(*history.files())
        self.assertEqual([uid for uid, _ in again.entries], [3100367, 3200000, 3300977])
        self.assertEqual(sorted(slot for _, slot in again.entries), [0, 1, 2])
        self.assertEqual(again.career(29), [])
        self.assertEqual([(s.year, s.club, s.goals) for s in again.career(3200000)], [(2003, 337, 255), (2004, 322, 2)])
        self.assertEqual(again.career(3300977), [hj.Season(2004, 337, 65, 5)])

    @unittest.skipUnless((Path(PL_HIST) / "pl_hist_index.original.dat").exists(),
                         "defina FM06_PL_HIST com a pasta dos pl_hist_*.original.dat")
    def test_real_files_round_trip(self) -> None:
        raw = [(Path(PL_HIST) / f"pl_hist_{n}.original.dat").read_bytes() for n in ("index", "id", "dt")]
        history = hj.History(*raw)
        self.assertEqual(history.files(), tuple(raw))
        self.assertEqual([s.club for s in history.career(3100367)][-1], 826)       # Saviola, Monaco


class CareerTest(unittest.TestCase):
    def test_periods(self) -> None:
        self.assertEqual(hj.period("2016–2019"), (2016, 2019))
        self.assertEqual(hj.period("2025–"), (2025, None))
        self.assertEqual(hj.period("2022"), (2022, 2022))
        self.assertEqual(hj.period("2019/20"), (2019, 2019))
        with self.assertRaises(ValueError):
            hj.period("2019-20-21")

    def test_years_follow_the_next_club_and_loans(self) -> None:
        passages = [hj.Passage(2016, 2019, "Flamengo", 67, 15, False), hj.Passage(2019, 2020, "AC Milan", 37, 1, False),
                    hj.Passage(2020, 2022, "Lyon", 67, 18, False), hj.Passage(2022, 2026, "West Ham", 110, 16, False),
                    hj.Passage(2026, None, "Flamengo", 27, 10, False)]
        self.assertEqual(hj.years(passages), [[2016, 2017, 2018], [2019], [2020, 2021], [2022, 2023, 2024, 2025],
                                              [2026]])
        loans = [hj.Passage(2015, 2020, "Sporting CP", 15, 1, False), hj.Passage(2017, 2018, "Chaves", 27, 7, True),
                 hj.Passage(2018, 2019, "Nürnberg", 19, 3, True), hj.Passage(2020, 2021, "WBA", 33, 11, False)]
        self.assertEqual(hj.years(loans), [[2015, 2016, 2019], [2017], [2018], [2020, 2021]])
        self.assertEqual(hj.years([hj.Passage(2019, None, "Flamengo", 261, 77, False)]),
                         [list(range(2019, hj.SOURCE_YEAR + 1))])

    def test_seasons_split_totals_and_skip_the_current_season(self) -> None:
        passages = [hj.Passage(2019, 2020, "AC Milan", 37, 1, False), hj.Passage(2020, None, "Flamengo", 70, 20, False)]
        (_, milan, how, first), (_, flamengo, _, second) = hj.seasons(passages, _clubs(), current_club=322)
        self.assertEqual((milan, how, flamengo), (1099, "nome", 322))
        self.assertEqual(first, [hj.Season(1999, 1099, 37, 1)])                     # ano do motor: -20
        # 2020..2026 = 7 temporadas de 10 jogos; 2025 (a do jogo) e 2026 ficam de fora
        self.assertEqual([(s.year, s.apps) for s in second], [(y - 20, 10) for y in range(2020, 2025)])
        self.assertTrue(all(s.goals in (2, 3) for s in second))

    def test_unknown_stats_and_missing_club(self) -> None:
        passages = [hj.Passage(2018, 2020, "Patriotas", 36, 4, False), hj.Passage(2020, 2022, "Lyon", 23, None, False)]
        (_, none, how, skipped), (_, _, _, lyon) = hj.seasons(passages, _clubs(), current_club=322)
        self.assertEqual((none, how, skipped), (None, "sem clube", []))
        # última passagem, sem clube seguinte: 2020, 2021 e 2022
        self.assertEqual([(s.apps, s.goals) for s in lyon], [(7, 255), (8, 255), (8, 255)])

    def test_fee_goes_on_the_last_season_of_the_selling_club(self) -> None:
        passages = [hj.Passage(2016, 2019, "Flamengo", None, None, False),
                    hj.Passage(2018, 2019, "Lyon", None, None, True),
                    hj.Passage(2019, 2020, "AC Milan", None, None, False, fee=38_400_000)]
        (_, _, _, flamengo), (_, _, _, lyon), (_, _, _, milan) = hj.seasons(passages, _clubs(), current_club=865)
        # quem vende é o dono (Flamengo), não o clube do empréstimo; o valor vai em libras
        self.assertEqual([(s.year, s.fee) for s in flamengo], [(1996, hj.NONE), (1997, 32_820_513)])
        self.assertEqual([(s.year, s.fee) for s in lyon], [(1998, hj.NONE)])
        self.assertEqual(milan, [hj.Season(1999, 1099), hj.Season(2000, 1099)])     # sem jogos e gols: 255

    def test_merge_same_year_and_club(self) -> None:
        merged = hj.merge([hj.Season(1995, 1489, 14, 6), hj.Season(1995, 1489, 7, 0), hj.Season(1995, 1489, 5, 1, True),
                           hj.Season(1994, 1489, 255, 255), hj.Season(1994, 1489, 3, 255)])
        self.assertEqual([(s.year, s.apps, s.goals, s.loan) for s in merged],
                         [(1994, 3, 255, False), (1995, 21, 6, False), (1995, 5, 1, True)])


class TransfersTest(unittest.TestCase):
    def test_passages_from_transfers(self) -> None:
        T, d = hj.Transfer, (lambda y, m: __import__("datetime").date(y, m, 1))
        passages = hj.passages_from_transfers([
            T(d(2019, 6), "Flamengo", "AC Milan", 3, 38_400_000),   # saiu no 1º semestre: estava lá em 2018
            T(d(2020, 10), "AC Milan", "Lyon", 3, 20_000_000),
            T(d(2022, 8), "Lyon", "West Ham", 3, 43_000_000),
            T(d(2023, 1), "West Ham", "Fulham", 1),                           # empréstimo
            T(d(2023, 6), "Fulham", "West Ham", 2),                           # volta: fecha só o empréstimo
            T(d(2024, 7), "West Ham", "West Ham", 3),                         # renovou: a mesma passagem
            T(d(2026, 1), "West Ham", "Flamengo", 3, 42_000_000),
        ])
        self.assertEqual([(p.label, p.club, p.loan, p.fee) for p in passages], [
            ("2018–2019", "Flamengo", False, None), ("2019–2020", "AC Milan", False, 38_400_000),
            ("2020–2022", "Lyon", False, 20_000_000), ("2022–2026", "West Ham", False, 43_000_000),
            ("2023", "Fulham", True, None), ("2026–", "Flamengo", False, 42_000_000)])

    def test_youth_origin_free_agent_and_loan_fee(self) -> None:
        T, d = hj.Transfer, (lambda y, m: __import__("datetime").date(y, m, 1))
        passages = hj.passages_from_transfers([
            T(d(2018, 1), "Santos U20", "Santos", 7),                         # subiu da base: sem passagem na base
            T(d(2020, 2), "Santos", "Sport", 1, 500_000),                     # valor de empréstimo não entra
            T(d(2021, 1), "Sport", "No team", 6),
            T(d(2021, 3), "No team", "Bahia", 7),
        ])
        self.assertEqual([(p.label, p.club, p.loan, p.fee) for p in passages], [
            ("2018–2021", "Santos", False, None), ("2020–2021", "Sport", True, None),
            ("2021–", "Bahia", False, None)])


class ClubsTest(unittest.TestCase):
    def test_aliases_brazil_and_names(self) -> None:
        clubs = _clubs()
        self.assertEqual(clubs.find("Porto"), (1478, "apelido"))                   # o de Portugal
        self.assertEqual(clubs.find("Charlotte FC"), (None, "apelido"))
        self.assertEqual(clubs.find("→ Flamengo (loan)"), (322, "brasil"))
        self.assertEqual(clubs.find("Atlético Mineiro"), (316, "brasil"))
        self.assertEqual(clubs.find("Lyon B"), (865, "nome"))                      # time B: o principal
        self.assertEqual(clubs.find("Al-Hilal"), (102852, "aproximado"))          # "(KSA)" a mais
        self.assertEqual(clubs.find("Real Betis"), (1747, "aproximado"))          # "Balompié S.A.D." a mais
        self.assertEqual(clubs.find("Sparta"), (None, "sem clube"))               # "Prag" muda o clube
        self.assertEqual(clubs.find("Zulia"), (None, "sem clube"))
        self.assertEqual(clubs.find("Flamengo-PI"), (314617, "nome"))             # o "Flamengo (PI)" do banco
        self.assertEqual(clubs.find("Bahia-SE"), (None, "sem clube"))

    def test_clubs_of_2026_only_by_the_2026_name(self) -> None:
        names = {319: ("SC Corinthians Paulista", "Corinthians"), 340: ("EC Vitória", "Vitória"),
                 1494: ("Vitória Sport Clube", "Vitória")}
        refs = Counter({319: 900, 340: 800, 1494: 300})
        loose = hj.Clubs(names, refs, {"Corinthians": 319, "Vitória": 340})
        self.assertEqual(loose.find("Paulista"), (None, "sem clube"))             # nunca o Corinthians
        self.assertEqual(loose.find("Vitória FC"), (340, "nome"))
        strict = hj.Clubs(names, refs, {"Corinthians": 319, "Vitória": 340}, strict=True)
        self.assertEqual(strict.find("Vitória"), (340, "brasil"))
        self.assertEqual(strict.find("Vitória FC"), (1494, "nome"))               # o Vitória já veio como "Vitória"

    def test_lang_club_table(self) -> None:
        def text(s: str) -> bytes:
            return struct.pack("<I", len(s)) + s.encode("utf-16-le") + b"\0\0"
        lang = b"xx" + struct.pack("<I", 865) + text("Olympique Lyonnais") + b"\x00" + text("Lyon") + \
            struct.pack("<I", 7) + text("Gent") + b"\0\0\0\0\xff" + struct.pack("<I", 1099) + text("AC Milan") + \
            b"\x01" + text("Milan")
        self.assertEqual(hj.lang_clubs(lang, 0, len(lang), {865, 1099, 7}),
                         {865: ("Olympique Lyonnais", "Lyon"), 1099: ("AC Milan", "Milan")})


if __name__ == "__main__":
    unittest.main()
