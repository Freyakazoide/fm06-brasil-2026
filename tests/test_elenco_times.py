from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import elenco_times as et  # noqa: E402


def team(value: int, uid: int, players: list[int], coaches: list[int] = (), physios: list[int] = (),
         manager: int = et.NONE) -> bytes:
    """Registro de time como o leitor TEAM (0x00A1FA30) lê, com o par (índice, UID) do fim."""
    fixed = bytearray(et.PREFIX)
    struct.pack_into("<I", fixed, et.MANAGER, manager)
    body = b"\x0a" + bytes(fixed)
    body += bytes([len(physios)]) + struct.pack(f"<{len(physios)}I", *physios)
    body += struct.pack("<H", len(players)) + struct.pack(f"<{len(players)}I", *players)
    body += bytes([len(coaches)]) + struct.pack(f"<{len(coaches)}I", *coaches)
    body += b"\x00" + b"\x00\x00" + b"\x00" * 0x30           # olheiros, objetos, datas
    return body + struct.pack("<II", value, uid)


def database(*teams: bytes) -> bytes:
    lo = et.REGION[0]
    data = b"\x00" * (lo - 8) + struct.pack("<II", 285, 316)  # o par que fecha o time anterior
    for record in teams:
        data += record
    return data + b"\x0a\x00" + b"\x00" * 200


class TeamListsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data = database(team(286, 317, [5322, 6537], coaches=[25205], manager=139254),   # Bragantino
                             team(287, 329, [139122, 140000], physios=[25553]))                # Palmeiras

    def test_reads_lists_and_manager(self):
        teams = {t.uid: t for t in et.all_teams(self.data)}
        self.assertEqual(teams[317].value, 286)
        self.assertEqual(teams[317].lists[et.PLAYERS], [5322, 6537])
        self.assertEqual(teams[317].manager, 139254)
        self.assertEqual(teams[329].lists[et.PHYSIOS], [25553])

    def test_move_player_coach_and_manager(self):
        moves = [et.Move(139122, 317, 286, et.PLAYERS),          # Warley do Palmeiras para o Bragantino
                 et.Move(25553, 317, 286, et.PHYSIOS),
                 et.Move(139254, 329, 287, "tecnico"),
                 et.Move(1, 999, 999, et.PLAYERS)]               # clube sem time: fica de fora
        out, missing = et.apply(self.data, moves)
        self.assertEqual(missing, [moves[-1]])
        teams = {t.uid: t for t in et.all_teams(out)}
        self.assertEqual(teams[317].lists[et.PLAYERS], [5322, 6537, 139122])   # em ordem
        self.assertEqual(teams[329].lists[et.PLAYERS], [140000])
        self.assertEqual(teams[317].lists[et.PHYSIOS], [25553])
        self.assertEqual(teams[329].lists[et.PHYSIOS], [])
        self.assertEqual((teams[317].manager, teams[329].manager), (et.NONE, 139254))
        self.assertEqual(len(out), len(self.data))               # 4 bytes saem de um time e entram no outro

    def test_moving_again_changes_nothing(self):
        moves = [et.Move(139122, 317, 286, et.PLAYERS)]
        once, _ = et.apply(self.data, moves)
        twice, _ = et.apply(once, moves)
        self.assertEqual(once, twice)


BASELINE = ROOT / "workspace" / "baseline" / "server_db.original.dat"


@unittest.skipUnless(BASELINE.exists(), "precisa do server_db original em workspace/baseline")
class RealDatabaseTest(unittest.TestCase):
    def test_palmeiras(self):
        teams = {t.uid: t for t in et.all_teams(BASELINE.read_bytes())}
        palmeiras = teams[329]
        self.assertEqual((palmeiras.value, len(palmeiras.lists[et.PLAYERS]), palmeiras.manager), (297, 106, 139254))
        self.assertIn(139122, palmeiras.lists[et.PLAYERS])       # Warley
        self.assertEqual(len(palmeiras.lists[et.COACHES]), 6)


if __name__ == "__main__":
    unittest.main()
