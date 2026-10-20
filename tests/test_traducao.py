from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import ltc, traducao  # noqa: E402

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


SCREENS = traducao.Glossary({"equipa": "time", "plantel": "elenco", "descida": "rebaixamento",
                              "médio": "meia", "época": "temporada", "Época": "Temporada",
                              "grande penalidade": "pênalti"},
                             {"época": "época", "Época": "Época"}, traducao.SCREENS)


def _ltc(*items: tuple[str, list[str]]) -> bytes:
    def text(value: str) -> bytes:
        return struct.pack("<I", len(value)) + value.encode("utf-16-le") + b"\0\0"
    body = b"".join(b"\x64" + text(key) + b"".join(b"\x65" + text(t) + struct.pack("<I", 7) for t in found)
                    for key, found in items)
    return b"\x02\x01ctl.\x03\x00\x00" + b"\0" * 4 + text("Português") + body + b"\x66\x05"


class TelasTest(unittest.TestCase):
    def test_screen_rules(self) -> None:
        self.assertEqual(SCREENS.translate("A equipa principal"), "A equipe principal")
        self.assertEqual(SCREENS.translate("Salário Médio"), "Salário Médio")
        self.assertEqual(SCREENS.translate("Médio Direito"), "Meia Direita")
        self.assertEqual(SCREENS.translate("a subida de divisão"), "o acesso")
        self.assertEqual(SCREENS.translate("evitar a descida"), "evitar a descida")
        self.assertEqual(SCREENS.translate("O árbitro assinalou uma grande penalidade"),
                         "O árbitro assinalou um pênalti")
        self.assertIsNone(SCREENS.translate("uma grande penalidade duvidosa"))
        self.assertEqual(SCREENS.translate("actualmente no plantel"), "atualmente no elenco")
        self.assertEqual(SCREENS.translate("Remunerações <%team#1-short>"), "Salários <%team#1-short>")

    def test_short_keeps_growing_terms(self) -> None:
        # "temporada" não cabe: fica "época" e o resto muda
        self.assertEqual(SCREENS.fit("o plantel desta época"), ("o elenco desta época", True))

    def test_ltc_round_trip(self) -> None:
        data = _ltc(("Squad", ["Plantel"]), ("Tactics", ["Tácticas", "Táctico"]))
        self.assertEqual([t for _, t in ltc.translations(data)], ["Plantel", "Tácticas", "Táctico"])
        glossary = traducao.Glossary({"plantel": "elenco", "tácticas": "táticas", "táctico": "tático"},
                                     rules=traducao.SCREENS)
        changes, too_long = traducao.plan_screens(data, glossary)
        out = traducao.apply(data, changes)
        self.assertEqual(len(out), len(data))
        self.assertEqual([t.rstrip() for _, t in ltc.translations(out)], ["Elenco", "Táticas", "Tático"])


if __name__ == "__main__":
    unittest.main()
