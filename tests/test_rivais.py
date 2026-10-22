from __future__ import annotations

import os
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import rivais  # noqa: E402
from fm06patch.server_teams import _CLUB_TAIL, _DATES  # noqa: E402

SERVER_DB = os.environ.get("FM06_SERVER_DB", str(ROOT / "workspace" / "baseline" / "server_db.original.dat"))


def _text(s: str) -> bytes:
    return struct.pack("<I", len(s)) + s.encode("utf-16-le") + b"\0\0"


def _club(repo: int, long_name: str, short: str, team: int, relations: list[tuple]) -> bytes:
    return (struct.pack("<I", repo) + _CLUB_TAIL + b"\0" * 6 + _DATES + _text(long_name) + _text(short)
            + b"\x02\x00\xff\x7f" + b"\x01" + struct.pack("<I", team) + bytes([len(relations)])
            + b"".join(struct.pack("<BBHI", *r) for r in relations) + bytes(range(18)))


def _db() -> bytes:
    # três clubes: índices 10, 11 e 12, UIDs verdadeiros 322, 323 e 339 (o UID do fim é o
    # primeiro u32 do registro seguinte); um registro sem datas fecha a lista
    flamengo = _club(321, "CR Flamengo", "Flamengo", 290, [(3, 1, 85, 10210), (1, 5, 70, 12)])
    fluminense = _club(322, "Fluminense FC", "Fluminense", 291, [(1, 5, 80, 10)])
    parana = _club(323, "Paraná Clube", "Paraná", 300, [])
    return (b"HEAD" + struct.pack("<I", 9) + flamengo + struct.pack("<I", 10) + fluminense + struct.pack("<I", 11)
            + parana + struct.pack("<I", 12) + struct.pack("<I", 339) + _CLUB_TAIL + b"\0" * 8)


class RivaisTest(unittest.TestCase):
    def test_read(self) -> None:
        clubs = rivais.read(_db())
        self.assertEqual(sorted(clubs), [322, 323, 339])
        self.assertEqual((clubs[322].index, clubs[322].name), (10, "Flamengo"))
        self.assertEqual(clubs[322].rivals(), {12: 70})
        self.assertEqual(clubs[339].relations, [])

    def test_plan_is_symmetric_and_keeps_the_rest(self) -> None:
        data = _db()
        clubs = rivais.read(data)
        changes = rivais.plan(clubs, [(322, 323, 3), (322, 339, 1)])
        # Fla-Flu entra com 90; o rival que já existia ganha o peso da planilha (1 -> 60)
        self.assertEqual(changes[322], [(3, 1, 85, 10210), (1, 5, 60, 12), (1, 5, 90, 11)])
        self.assertEqual(changes[323], [(1, 5, 90, 10)])
        self.assertEqual(changes[339], [(1, 5, 60, 10)])
        out = rivais.apply(data, clubs, changes)
        self.assertEqual(len(out), len(data) + 8 * 2)
        again = rivais.read(out)
        self.assertEqual({uid: c.relations for uid, c in again.items()}, changes)

    def test_level_three_keeps_a_higher_weight_and_substitutes_lose_old_rivals(self) -> None:
        clubs = rivais.read(_db())
        clubs[322].relations[1] = (1, 5, 101, 12)
        self.assertEqual(rivais.plan(clubs, [(322, 339, 3)]).get(322), None)       # 101 fica
        changes = rivais.plan(clubs, [], clear={339})                               # 339 virou outro clube
        self.assertEqual(changes, {322: [(3, 1, 85, 10210)]})
        changes = rivais.plan(clubs, [(322, 339, 2)], clear={339})                 # a planilha manda
        self.assertEqual(changes[322][-1], (1, 5, 75, 12))

    @unittest.skipUnless(Path(SERVER_DB).exists(), "defina FM06_SERVER_DB com o server_db.dat original")
    def test_real_database(self) -> None:
        clubs = rivais.read(Path(SERVER_DB).read_bytes())
        self.assertGreaterEqual(len(clubs), 690)
        flamengo, index = clubs[322], {c.index: c.name for c in clubs.values()}
        self.assertEqual({index[r]: level for r, level in flamengo.rivals().items()},
                         {"Vasco": 90, "Botafogo": 70, "Fluminense": 80})
        self.assertEqual(max(clubs[324].rivals().values()), 101)                   # Gre-Nal


if __name__ == "__main__":
    unittest.main()
