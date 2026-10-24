from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from fm06patch import estrangeiros as ex  # noqa: E402
from fm06patch import historico_jogadores as hj  # noqa: E402

RIVER = {"uid": 94, "repo": 93, "index": 33, "long": "CA River Plate", "short": "River"}
CLUBS = [RIVER,
         {"uid": 82, "repo": 81, "index": 22, "long": "CA Boca Juniors", "short": "Boca"},
         {"uid": 85, "repo": 83, "index": 24, "long": "Estudiantes de La Plata", "short": "Estudiantes (LP)"},
         {"uid": 86, "repo": 84, "index": 25, "long": "Estudiantes de Buenos Aires", "short": "Estudiantes (BA)"},
         {"uid": 87, "repo": 86, "index": 26, "long": "Central Córdoba de Rosario", "short": "Ctral. Córdoba"},
         {"uid": 88, "repo": 87, "index": 27, "long": "Huracán", "short": "Huracán"},
         {"uid": 89, "repo": 88, "index": 28, "long": "Huracán de Tres Arroyos", "short": "Huracán (TA)"},
         {"uid": 90, "repo": 89, "index": 29, "long": "CCD Tolima", "short": "Tolima"},
         {"uid": 91, "repo": 90, "index": 30, "long": "Lotería del Tolima Cooperamos", "short": "Cooperamos Tolima"},
         {"uid": 92, "repo": 91, "index": 31, "long": "C Deportivo Recoleta", "short": "Deportivo Recoleta"}]


class MatchClubTest(unittest.TestCase):
    def test_full_name_without_prefixes(self):
        self.assertEqual(ex.match_club("River Plate", CLUBS)["uid"], 94)
        self.assertEqual(ex.match_club("Boca Juniors", CLUBS)["uid"], 82)

    def test_contained_name_only_when_unique(self):
        self.assertEqual(ex.match_club("Estudiantes de La Plata", CLUBS)["uid"], 85)
        self.assertIsNone(ex.match_club("Estudiantes", CLUBS))         # dois clubes com o nome
        self.assertIsNone(ex.match_club("Deportivo Riestra", CLUBS))   # não existe no FM06

    def test_alias(self):
        self.assertEqual(ex.match_club("CARP", CLUBS, {"CARP": 94})["uid"], 94)
        self.assertEqual(ex.match("Gimnasia", CLUBS, {"Gimnasia": "Estudiantes de Buenos Aires"}), (CLUBS[3], "apelido"))

    def test_another_city_is_another_club(self):
        self.assertIsNone(ex.match_club("Central Córdoba", CLUBS))     # o de Santiago del Estero
        self.assertEqual(ex.match("Huracán", CLUBS), (CLUBS[5], "nome"))    # não o de Tres Arroyos

    def test_prefix_or_legal_form_more(self):
        self.assertEqual(ex.match("Deportes Tolima", CLUBS), (CLUBS[7], "aproximado"))
        self.assertEqual(ex.match("Recoleta", CLUBS), (CLUBS[9], "aproximado"))

    def test_display_name_has_the_country(self):
        self.assertEqual(ex.display_name("Nacional", "UY"), "Nacional (URU)")


class IdentitiesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp())
        self.br = self.dir / "identidade_fm06.csv"
        self.br.write_text("clube_2026,uid_jogo,uid_repo,tipo\nPalmeiras,329,328,clube\n", encoding="utf-8-sig")
        self.abroad = self.dir / "identidade_estrangeiros.csv"
        with self.abroad.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=ex.FIELDS)
            writer.writeheader()
            writer.writerow({"clube_2026": "River Plate (ARG)", "pais": "AR", "uid_jogo": 94, "uid_repo": 93,
                             "tipo": "estrangeiro"})
            writer.writerow({"clube_2026": "Riestra (ARG)", "pais": "AR", "uid_jogo": "", "tipo": "estrangeiro"})

    def test_rows_without_fm06_club_stay_out(self):
        with mock.patch.object(ex, "IDENTITIES", self.abroad):
            self.assertEqual([r["clube_2026"] for r in ex.identity_rows()], ["River Plate (ARG)"])
            self.assertEqual(ex.nation_of(94), 0xBB)
            self.assertEqual(ex.nation_of(329), 0xBD)

    def test_counting_list_has_brazil_and_abroad(self):
        out = self.dir / "todas.csv"
        with mock.patch.object(ex, "IDENTITIES", self.abroad), mock.patch.object(ex, "BR_IDENTITIES", self.br):
            ex.write_all_identities(out)
        rows = list(csv.DictReader(out.open(encoding="utf-8-sig")))
        self.assertEqual([(r["clube_2026"], r["uid_jogo"]) for r in rows], [("Palmeiras", "329"), ("River Plate (ARG)", "94")])

    def test_no_foreign_file(self):
        with mock.patch.object(ex, "IDENTITIES", self.dir / "nada.csv"):
            self.assertEqual(ex.identity_rows(), [])


class CareerClubsTest(unittest.TestCase):
    def test_foreign_2026_name_finds_the_club(self):
        names = {94: ("CA River Plate", "River"), 329: ("SE Palmeiras", "Palmeiras")}
        clubs = hj.Clubs(names, hj.Counter(), {"Palmeiras": 329, "River Plate (ARG)": 94}, strict=True)
        self.assertEqual(clubs.find("River Plate (ARG)"), (94, "brasil"))


BASELINE = ROOT / "workspace" / "baseline" / "server_db.original.dat"


@unittest.skipUnless(BASELINE.exists(), "precisa do server_db original em workspace/baseline")
class RealDatabaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = BASELINE.read_bytes()

    def test_clubs_of_each_country(self):
        argentina = {c["uid"]: c for c in ex.fm06_clubs(self.server, "AR")}
        self.assertEqual((argentina[94]["index"], argentina[82]["short"]), (33, "Boca"))
        for alpha2 in ex.NATIONS:                   # sem os pares falsos (belgas, brasileiros, UID 0)
            for club in ex.fm06_clubs(self.server, alpha2):
                self.assertTrue(0 < club["repo"] < club["uid"], club)
        self.assertIn("Colo Colo", {c["short"] for c in ex.fm06_clubs(self.server, "CL")})
        bolivia = {c["short"]: c["index"] for c in ex.fm06_clubs(self.server, "BO")}
        self.assertEqual((bolivia["Bolívar"], bolivia["The Strongest"]), (188, 189))   # índice = código de nação

    def test_indexes_and_team_values(self):
        rows = [{"clube_2026": "River Plate (ARG)", "pais": "AR", "uid_jogo": "94"},
                {"clube_2026": "Peñarol (URU)", "pais": "UY", "uid_jogo": "1922"}]
        self.assertEqual(ex.club_indexes(self.server, rows), {94: 33, 1922: 1467})
        values = ex.team_values(self.server)
        self.assertEqual((values[94], values[1922], values[329]), (84, 1665, 297))

    def test_montar_estrangeiros_matches_by_name(self):
        import montar_estrangeiros
        teams = [{"pais": "AR", "clube": "River Plate (ARG)", "liga": "Liga", "sofascore_id": 1, "sofascore_nome": "River Plate"},
                 {"pais": "AR", "clube": "Riestra (ARG)", "liga": "Liga", "sofascore_id": 2, "sofascore_nome": "Riestra"},
                 {"pais": "UY", "clube": "Peñarol (URU)", "liga": "Liga", "sofascore_id": 3, "sofascore_nome": "Peñarol"}]
        kept = {2: {"uid_jogo": "82", "uid_repo": "81", "fm06_nome": "Boca"}}     # posto à mão
        rows, notes = montar_estrangeiros.identities(teams, self.server, kept)
        self.assertEqual([r["uid_jogo"] for r in rows], [94, 82, 1922])
        self.assertEqual(notes, [])


if __name__ == "__main__":
    unittest.main()
