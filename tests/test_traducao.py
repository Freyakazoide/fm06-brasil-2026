from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import traducao  # noqa: E402

GLOSSARY = traducao.Glossary({"equipa": "time", "Equipa": "Time", "Treinador": "Técnico", "partida": "jogo",
                              "Guarda-redes": "Goleiro", "Época": "Temporada", "golo": "gol"},
                             {"Época": "Época"})


def _text(value: str) -> bytes:
    return struct.pack("<I", len(value)) + value.encode("utf-16-le") + b"\0\0"


class TraducaoTest(unittest.TestCase):
    def test_whole_words_and_case(self) -> None:
        self.assertEqual(GLOSSARY.translate("Treinador do Ano"), "Técnico do Ano")
        self.assertEqual(GLOSSARY.translate("Guarda-Redes do Ano"), "Goleiro do Ano")
        self.assertEqual(GLOSSARY.translate("Golos"), "Golos")          # palavra inteira: "golos" não é "golo"

    def test_skipped_and_extra_terms(self) -> None:
        self.assertEqual(GLOSSARY.translate("perna partida"), "perna partida")
        self.assertEqual(GLOSSARY.translate("Melhor Marcador - Bahia"), "Artilheiro - Bahia")

    def test_gender_of_time(self) -> None:
        self.assertEqual(GLOSSARY.translate("antiga equipa"), "antigo time")
        self.assertEqual(GLOSSARY.translate("Jogador da Equipa"), "Jogador do Time")
        self.assertIsNone(GLOSSARY.translate("equipa <%nation#1-nationality1>"))

    def test_plan_keeps_names_and_size(self) -> None:
        pt = _text("Treinador do Ano") + _text("Presidente Prudente (SP)") + _text("Treinador da Época")
        en = _text("Manager of the Year") + _text("Presidente Prudente (SP)")
        start_en = 0x80
        start_pt = start_en + len(en)
        head = b"\0" * 0x12 + struct.pack("<IIII", 0x20, start_en, traducao.PORTUGUESE, start_pt)
        data = head.ljust(start_en, b"\0") + en + pt
        changes, too_long = traducao.plan(data, GLOSSARY)
        self.assertEqual([(c.old, c.new) for c in changes],
                         [("Treinador do Ano", "Técnico do Ano"), ("Treinador da Época", "Técnico da Época")])
        out = traducao.apply(data, changes)
        self.assertEqual(len(out), len(data))
        self.assertIn("Técnico do Ano  ".encode("utf-16-le"), out)


if __name__ == "__main__":
    unittest.main()
