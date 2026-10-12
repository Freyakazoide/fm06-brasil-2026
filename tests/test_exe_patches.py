from __future__ import annotations

import hashlib
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch.exe_patches import EXE_SHA256, PATCHES, apply  # noqa: E402


EXE = Path(os.environ.get("FM06_EXE", ROOT / "workspace" / "fm.exe"))


@unittest.skipUnless(EXE.exists(), "fm.exe não disponível (defina FM06_EXE)")
class ExePatchTest(unittest.TestCase):

    def setUp(self) -> None:
        self.data = EXE.read_bytes()
        self.assertEqual(hashlib.sha256(self.data).hexdigest().upper(), EXE_SHA256)

    def test_every_patch_matches_original_bytes(self) -> None:
        for name in PATCHES:
            patched = apply(self.data, [name])
            self.assertEqual(len(patched), len(self.data))
            changed = sum(a != b for a, b in zip(patched, self.data))
            expected = sum(sum(x != y for x, y in zip(s.old, s.new)) for s in PATCHES[name].swaps_for(self.data))
            self.assertEqual(changed, expected, name)

    def test_all_patches_combine(self) -> None:
        # exp_cave_* são partes alternativas do serie_c_nova (mesma área livre);
        # serie_c_64_clubes é alternativa ao serie_d_96 (mesmos bytes).
        apply(self.data, [name for name in PATCHES
                          if not name.startswith("exp_cave_") and name != "serie_c_64_clubes"])

    def test_patch_cannot_apply_twice(self) -> None:
        once = apply(self.data, ["serie_a_rebaixa_4"])
        with self.assertRaises(ValueError):
            apply(once, ["serie_a_rebaixa_4"])

    def test_cave_cannot_apply_twice(self) -> None:
        once = apply(self.data, ["serie_c_nova"])
        with self.assertRaises(ValueError):
            apply(once, ["serie_c_nova"])


if __name__ == "__main__":
    unittest.main()
