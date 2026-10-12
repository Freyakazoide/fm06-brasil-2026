from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_fmm_live import analyze  # noqa: E402
from fm06patch.fmm_schema import (  # noqa: E402
    FMM2_DEFAULT,
    counted_values,
    describe_schema,
    parse_fmm,
    section,
)


class FmmSchemaTests(unittest.TestCase):
    @unittest.skipUnless(FMM2_DEFAULT.exists(), "FMM2 não instalado")
    def test_fmm2_lists_and_target_row(self):
        schema = describe_schema(FMM2_DEFAULT)
        self.assertEqual(79, len(schema["playing_attributes"]))
        self.assertEqual(list(range(79)), sorted(schema["playing_position"]))
        self.assertEqual(48, len(schema["preferred_moves"]))
        self.assertEqual(0x010F1034, schema["roots"]["Player"][0])

    def test_duplicate_sections_are_preserved(self):
        sample = "[X]\n2\na\nb\n[X]\n1\nc\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "FMM.txt"
            path.write_text(sample, encoding="cp1252")
            parsed = parse_fmm(path)
        self.assertEqual(["a", "b"], counted_values(section(parsed, "X", 0)))
        self.assertEqual(["c"], counted_values(section(parsed, "X", 1)))

    @unittest.skipUnless(
        (ROOT / "workspace/live_memory/3100367/baseline_20261012.json").exists()
        and FMM2_DEFAULT.exists(),
        "snapshot vivo ausente",
    )
    def test_saviola_object_signatures(self):
        result = analyze(
            ROOT / "workspace/live_memory/3100367/baseline_20261012.json",
            FMM2_DEFAULT,
        )
        self.assertEqual(["0x0FC90168"], result["objects"]["Player"])
        self.assertEqual(["0x102101F8"], result["objects"]["PData"])
        self.assertEqual(["0x102D5134"], result["objects"]["Playing"])
        personalities = [item["value"] for item in result["personality"]]
        self.assertEqual([12, 18, 13, 14, 15, 5, 12, 8], personalities)


if __name__ == "__main__":
    unittest.main()
