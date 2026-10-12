from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from generate_fmm_reports import personal_layout  # noqa: E402


class FmmReportTests(unittest.TestCase):
    def test_manual_personal_diffs_are_promoted(self) -> None:
        fields = {row["field"]: row for row in personal_layout()}
        self.assertEqual(fields["Height"]["relative_to_object_uid"], -76)
        self.assertEqual(fields["Height"]["confidence"], "CONFIRMED")
        self.assertEqual(fields["Adaptability"]["relative_to_object_uid"], 8)
        self.assertEqual(fields["Adaptability"]["confidence"], "CONFIRMED")
        self.assertEqual(fields["Nationality"]["relative_to_object_uid"], 64)
        self.assertEqual(fields["Born"]["relative_to_object_uid"], 52)
        self.assertEqual(fields["U21 Caps"]["relative_to_object_uid"], 73)
        self.assertEqual(fields["U21 Goals"]["relative_to_object_uid"], 75)

    def test_contract_pool_links_saviola_to_both_clubs(self) -> None:
        path = ROOT / "reverse" / "fmm" / "pool_link_analysis.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = [
            row for row in payload["linked_contracts"] if row["player_uid"] == 3100367
        ]
        by_club = {row["club_public_uid"]: row for row in rows}
        self.assertEqual(by_club[1708]["wages_if_tagged_x10_plus_2"], 650001)
        self.assertEqual(by_club[1759]["started_offset_24"]["year"], 2005)
        self.assertEqual(by_club[1759]["expires_offset_32"]["year"], 2006)

    def test_contract_report_contains_resolved_fields(self) -> None:
        path = ROOT / "reverse" / "fmm" / "contract_live_layout.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        fields = {row["field"]: row for row in payload["fields"]}
        self.assertEqual(fields["Wages"]["relative_offset"], 16)
        self.assertEqual(fields["Wages"]["confidence"], "CONFIRMED")
        self.assertEqual(fields["Started"]["relative_offset"], 24)
        self.assertEqual(fields["Expires"]["relative_offset"], 32)
        self.assertEqual(fields["Squad Number"]["relative_offset"], 49)
        self.assertEqual(fields["Clean Sheet"]["relative_offset"], 88)

    def test_preferred_moves_are_a_player_bitset(self) -> None:
        path = ROOT / "reverse" / "fmm" / "preferred_moves_layout.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["bitset_start_relative_to_player_uid"], -48)
        self.assertEqual(payload["moves"][0]["byte_offset"], -48)
        self.assertEqual(payload["moves"][31]["byte_offset"], -45)
        self.assertEqual(payload["moves"][31]["bit"], 7)
        self.assertEqual(payload["moves"][47]["byte_offset"], -43)

    def test_remaining_round_records_incomplete_restore(self) -> None:
        path = ROOT / "reverse" / "fmm" / "remaining_round_analysis.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        contract_runs = payload["restoration"]["contract"]["change_runs"]
        squad_number = [
            row
            for row in contract_runs
            if row.get("relative_offset") == 48
            or row.get("relative_offset") == 49
        ]
        self.assertTrue(squad_number)
        self.assertEqual(payload["restoration"]["nation"]["changed_byte_count"], 0)


if __name__ == "__main__":
    unittest.main()
