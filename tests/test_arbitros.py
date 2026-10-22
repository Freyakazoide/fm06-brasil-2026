from __future__ import annotations

import os
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import arbitros  # noqa: E402

BASELINE = Path(os.environ.get("FM06_BASELINE", str(ROOT / "workspace" / "baseline")))


class ArbitrosTest(unittest.TestCase):
    def setUp(self) -> None:
        self.people = bytearray(64)
        struct.pack_into("<HHH", self.people, 10, 135, 160, 145)
        struct.pack_into("<HHH", self.people, 30, 160, 180, 160)
        struct.pack_into("<HHH", self.people, 50, 170, 175, 170)
        self.officials = [arbitros.Official(2102845, "Wilson Luís Seneme", 0xBD, 135, 160, 145, 10),
                          arbitros.Official(302174, "Ocimar Bolicenho", 0xBD, 160, 180, 160, 30),
                          arbitros.Official(302984, "Marcelo Sato", 0xBD, 170, 175, 170, 50, employed=True)]
        self.referees = [arbitros.Referee("Gleika Oliveira Pinheiro", "PA", "FIFA", 15),
                         arbitros.Referee("Raphael Claus", "SP", "FIFA", 19)]

    def test_level_to_ability(self) -> None:
        self.assertEqual([arbitros.Referee("x", "", "", n).ability for n in (1, 15, 19, 20, 30)],
                         [10, 142, 180, 190, 200])

    def test_best_referee_takes_the_best_free_official(self) -> None:
        pairs = arbitros.plan(self.officials, self.referees)
        self.assertEqual([(o.name, r.nome) for o, r in pairs],
                         [("Ocimar Bolicenho", "Raphael Claus"), ("Wilson Luís Seneme", "Gleika Oliveira Pinheiro")])
        out = arbitros.apply(bytes(self.people), pairs)
        self.assertEqual(struct.unpack_from("<HHH", out, 30), (180, 180, 180))
        self.assertEqual(struct.unpack_from("<HHH", out, 10), (142, 160, 142))     # potencial não baixa
        self.assertEqual(struct.unpack_from("<HHH", out, 50), (170, 175, 170))     # com contrato: intocado
        self.assertEqual(arbitros.lnc_text(pairs).splitlines()[1:], [
            '"CHANGE_PLAYER_NAME"\t302174\t"Raphael"\t""\t"Claus"',
            '"CHANGE_PLAYER_NAME"\t2102845\t"Gleika"\t"Gleika Oliveira Pinheiro"\t"Pinheiro"'])

    @unittest.skipUnless((BASELINE / "people_db.original.dat").exists() and (BASELINE / "server_db.original.dat").exists(),
                         "defina FM06_BASELINE com a pasta dos people_db/server_db originais")
    def test_real_database(self) -> None:
        officials = arbitros.read((BASELINE / "people_db.original.dat").read_bytes(),
                                  (BASELINE / "server_db.original.dat").read_bytes())
        self.assertEqual(len(officials), 492)
        seneme = next(o for o in officials if o.uid == 2102845)
        self.assertEqual((seneme.name, seneme.ability, seneme.potential, seneme.reputation),
                         ("Wilson Luís Seneme", 135, 160, 145))
        self.assertEqual(sum(o.employed for o in officials), 76)


if __name__ == "__main__":
    unittest.main()
