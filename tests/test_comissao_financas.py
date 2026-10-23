from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import comissao, financas, instalacoes  # noqa: E402


def text(value: str) -> bytes:
    raw = value.encode("utf-16-le")
    return struct.pack("<I", len(value)) + raw + (b"\0\0" if value else b"")


def club_record(uid: int, balance: int, attendance=(15326, 10000, 95000)) -> bytes:
    """Registro de clube no formato do leitor do CLUB (financas.py)."""
    body = b"\x00" + struct.pack("<I", 0xBD) + b"\x00" + text("Tricolor") + b"\x00" + text("")
    body += b"\x10\x10" + struct.pack("<H", 1902) + b"\xff" * 4 + b"\x01"
    body += struct.pack("<III", *attendance) + b"\x0f\x00" + struct.pack("<I", 132914) + b"\x64" + b"\xff" * 4 + b"\x00"
    body += b"\x02" + struct.pack("<II", 1, 2) + b"\x00" + b"\x00" + struct.pack("<i", balance) + b"\x00" * 8
    return struct.pack("<I", 198) + struct.pack("<I", uid) + body


class FinanceTest(unittest.TestCase):
    def test_reads_and_writes_balance_and_attendance(self):
        data = b"\xaa" * 64 + club_record(322, 800000) + b"\xbb" * 64
        info = financas.read(data, financas.record_start(data, 322))
        self.assertEqual((info.balance, info.attendance, info.finance_type), (800000, (15326, 10000, 95000), 0))
        out = financas.apply(data, {322: (5_080_000, 30000)})
        info = financas.read(out, financas.record_start(out, 322))
        self.assertEqual(info.balance, 1_000_000)               # R$ 5,08 = £1
        self.assertEqual(info.attendance, (30000, 15000, 95000))
        self.assertEqual(len(out), len(data))


class FacilitiesTest(unittest.TestCase):
    def test_reads_and_writes_training_youth_and_recruitment(self):
        data = b"\xaa" * 64 + club_record(322, 800000) + b"\xbb" * 64
        info = instalacoes.read(data, financas.record_start(data, 322))
        self.assertEqual((info.training, info.youth, info.recruitment), (15, 16, 16))   # +0xEB, +0xE1, +0xE0
        out = instalacoes.apply(data, {322: (19, 20, None)})
        info = instalacoes.read(out, financas.record_start(out, 322))
        self.assertEqual((info.training, info.youth, info.recruitment), (19, 20, 16))
        self.assertEqual(financas.read(out, financas.record_start(out, 322)).balance, 800000)
        self.assertEqual(len(out), len(data))

    def test_rating(self):
        self.assertEqual((instalacoes.rating(18), instalacoes.rating("17,6"), instalacoes.rating(None)), (18, 18, None))
        with self.assertRaises(ValueError):
            instalacoes.rating(21)


class NamesakeTest(unittest.TestCase):
    def test_same_name_and_real_birth_date(self):
        persons = [comissao.Person(20178, "Carlo Ancelotti", None, (160, 1959), 0x96),          # 10/6/1959
                   comissao.Person(305715, "Adenor Leonardo Bachi", "Tite", (144, 1961), 0xBD),  # 25/5/1961
                   comissao.Person(7, "Carlo Ancelotti", None, (160, 1960), 0x96),               # outro ano
                   comissao.Person(8, "Tite", None, (144, 1961), 0xBD)]                          # já ocupado
        wanted = [({"Carlo Ancelotti"}, "1959-06-10"), ({"Tite", "Adenor Leonardo Bachi"}, "1961-05-25")]
        found = comissao.namesakes(persons, wanted, taken={8})
        self.assertEqual(sorted(p.uid for p in found), [20178, 305715])


class RecordBoundaryTest(unittest.TestCase):
    def test_names_search_stops_at_previous_record(self):
        tables = ({1: "Ana"}, {2: "Silva"}, {})
        names = struct.pack("<IIII", 1, 2, comissao.NONE, 0) + struct.pack("<HH", 10, 1980) + b"\0" * 30
        tail = struct.pack("<H", 2008) + b"\0\0\0" + struct.pack("<II", 500, 1234)   # fim do registro anterior
        data = b"\0" * 40 + names + tail + b"\x11" * 60          # o registro seguinte não tem nomes
        self.assertEqual(comissao._names_before(data, 40 + len(names) - 5, tables), 40)
        self.assertIsNone(comissao._names_before(data, len(data) - 4, tables))


class StaffTest(unittest.TestCase):
    def test_split_name(self):
        self.assertEqual(comissao.split_name("Tite"), ("Tite", "Tite", ""))
        self.assertEqual(comissao.split_name("Leonardo Jardim"), ("Leonardo", "", "Jardim"))
        self.assertEqual(comissao.split_name("Márcio de Moraes Torres"),
                         ("Márcio", "Márcio de Moraes Torres", "Torres"))

    def test_engine_birth_is_twenty_years_earlier(self):
        self.assertEqual(comissao.engine_birth("1974-08-01"), (212, 1954))
        self.assertEqual(comissao.engine_birth("1920-02-29"), (58, 1900))     # 1900 não é bissexto: 28/2

    def test_nation_codes(self):
        self.assertEqual(comissao.nation_code("PRT"), comissao.nation_code("POR"))
        self.assertEqual(comissao.nation_code("Brazil"), 0xBD)
        self.assertIsNone(comissao.nation_code("ATL"))


if __name__ == "__main__":
    unittest.main()


BASELINE = ROOT / "workspace" / "baseline"


@unittest.skipUnless((BASELINE / "people_db.original.dat").exists() and (BASELINE / "server_db.original.dat").exists(),
                     "precisa do people_db e do server_db originais em workspace/baseline")
class NationalManagerTest(unittest.TestCase):
    def test_brazil_and_argentina(self) -> None:
        managers = comissao.read_national_managers((BASELINE / "people_db.original.dat").read_bytes(),
                                                   (BASELINE / "server_db.original.dat").read_bytes())
        self.assertEqual([(p.name, p.uid) for p in managers[0xBD]], [("Carlos Alberto Parreira", 1200738)])
        self.assertEqual([p.name for p in managers[0xBB]], ["José Pekerman"])
