from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import centro  # noqa: E402


class CentroTest(unittest.TestCase):
    def test_codes(self) -> None:
        self.assertEqual(centro.code("PCAB"), 0x50434142)
        self.assertEqual((centro.JOB, centro.JUDGE_ABILITY), (centro.code("Pcjo"), centro.code("Npja")))

    def test_hook_answers_mod_codes_and_falls_back(self) -> None:
        base = 0x015C1200
        hook = centro.hook_code(base, base + 0x200, base + 0x3F0)
        self.assertTrue(hook.startswith(bytes.fromhex("8B442404")))       # mov eax, [esp+4] (código)
        for value in (centro.STAR_NOW, centro.STAR_POTENTIAL, centro.CA, centro.PA):
            self.assertIn(b"\x3D" + value.to_bytes(4, "little"), hook)
        at = hook.index(b"\xE9")                                          # primeiro jmp: o original
        target = base + at + 5 + int.from_bytes(hook[at + 1:at + 5], "little", signed=True)
        self.assertEqual(target, centro.PROPERTY)
        self.assertTrue(hook.endswith(bytes.fromhex("83C410 B001 C20800")))

    def test_star_error_shrinks_with_the_judge(self) -> None:
        def max_error(judge: int) -> int:                                 # décimos de estrela
            return (21 - max(1, judge)) * 3 // 2
        self.assertEqual((max_error(20), max_error(12), max_error(1), max_error(0)), (1, 13, 30, 30))

    def test_my_club_is_an_attribute(self) -> None:
        base = 0x015C16E0
        code = centro.attribute_code(base)
        self.assertIn(b"=" + centro.MY_CLUB.to_bytes(4, "little"), code)
        at = len(code) - 5
        self.assertEqual(base + len(code) + int.from_bytes(code[at + 1:], "little", signed=True),
                         centro.IS_ATTRIBUTE + 9)                         # segue no cmp seguinte
        self.assertLessEqual(len(code), 0x20)

    def test_prefilter_only_passes_my_club_when_marked(self) -> None:
        base, flag = 0x015C1740, 0x015C17F0
        code = centro.prefilter_code(base, flag, 0x015C1400, 0x015C15F0)
        self.assertTrue(code.startswith(bytes.fromhex("F6460C01 0F85")))  # o teste original continua
        self.assertIn(bytes.fromhex("833D") + flag.to_bytes(4, "little") + bytes(1), code)
        ends = [base + len(code) - 5 * (k - 1) + int.from_bytes(code[len(code) - 5 * k + 1:len(code) - 5 * (k - 1)],
                                                          "little", signed=True) for k in (2, 1)]
        self.assertEqual(ends, [centro.KNOWN_KEEP, centro.KNOWN_NEXT])
        panel = centro.panel_code(0x015C1700, flag)
        self.assertIn(bytes([0x81, 0x79, centro.PANEL_ID]) + centro.CENTRO_ID.to_bytes(4, "little"), panel)

    def test_back_button_treats_centro_like_search(self) -> None:
        base = 0x015C1700
        code = centro.section_list_code(base)
        self.assertTrue(code.startswith(bytes([0x3D]) + centro.CENTRO_ID.to_bytes(4, "little")))
        hit = base + 11 + int.from_bytes(code[7:11], "little", signed=True)
        self.assertEqual(hit, centro.SECTION_LIST_HIT)
        self.assertEqual(base + len(code) + int.from_bytes(code[-4:], "little", signed=True),
                         centro.SECTION_LIST_AT + 5)

    def test_click_from_centro_opens_training(self) -> None:
        last = 0x015C17F0
        opening = centro.open_code(0x015C1760, last)
        self.assertTrue(opening.startswith(centro.OPEN_OLD))
        self.assertIn(bytes([0x81, 0xFF]) + centro.PROFILE.to_bytes(4, "little"), opening)
        self.assertIn(bytes([0xBF]) + centro.TRAINING.to_bytes(4, "little"), opening)
        leave = centro.leave_code(0x015C1740, last)
        self.assertEqual(leave[:11], centro.LEAVE_OLD + bytes([0xA3]) + last.to_bytes(4, "little"))


if __name__ == "__main__":
    unittest.main()
