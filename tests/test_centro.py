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


if __name__ == "__main__":
    unittest.main()
