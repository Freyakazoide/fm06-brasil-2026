from __future__ import annotations

import datetime as dt
import json
import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch.live_player import (  # noqa: E402
    OBJECT_SPAN,
    LivePlayer,
    decode_date,
    encode_date,
    load_attributes,
    shift_years,
)


# Valores exibidos na ficha do jogo (prints de 12/10/2026).
SAVIOLA_SCREEN = {
    "Cabeceamento": 11, "Cantos": 15, "Cruzamentos": 15, "Desarme": 7,
    "Finalização": 15, "Finta": 19, "Lançam. Longos": 11, "Livres": 12,
    "Marcação": 7, "Marcação Penalties": 16, "Passe": 14, "Primeiro Toque": 19,
    "Remates Longe": 14, "Técnica": 20,
    "Agressividade": 4, "Antecipação": 16, "Bravura": 6, "Compostura": 16,
    "Concentração": 16, "Criatividade": 16, "Decisões": 14, "Determinação": 15,
    "Influência": 11, "Instinto": 16, "Posicionamento": 10, "Sem Bola": 17,
    "Trabalho Equipa": 12, "Índice Trabalho": 11,
    "Aceleração": 19, "Agilidade": 19, "Balance": 11, "Cond. Fís. Natural": 10,
    "Força": 6, "Impulsão": 7, "Resistência": 15, "Velocidade": 17,
}

ZIDANE_SCREEN = {
    "Cabeceamento": 15, "Cantos": 15, "Cruzamentos": 18, "Desarme": 14,
    "Finalização": 18, "Finta": 19, "Lançam. Longos": 7, "Livres": 19,
    "Marcação": 11, "Marcação Penalties": 17, "Passe": 19, "Primeiro Toque": 20,
    "Remates Longe": 19, "Técnica": 20,
    "Agressividade": 15, "Antecipação": 18, "Bravura": 12, "Compostura": 17,
    "Concentração": 19, "Criatividade": 20, "Decisões": 20, "Determinação": 18,
    "Influência": 15, "Instinto": 20, "Posicionamento": 16, "Sem Bola": 15,
    "Trabalho Equipa": 14, "Índice Trabalho": 14,
    "Aceleração": 11, "Agilidade": 16, "Balance": 12, "Cond. Fís. Natural": 16,
    "Força": 14, "Impulsão": 11, "Resistência": 13, "Velocidade": 14,
}


def fake_player(uid: int, ca: int, playing_raw_by_fmm_index: list[int]) -> LivePlayer:
    """Monta os três blocos como o script os leria do processo."""
    attributes = load_attributes()
    blocks, uid_at = {}, {}
    for kind, (before, after) in OBJECT_SPAN.items():
        block = bytearray(before + after)
        struct.pack_into("<I", block, before, uid)
        blocks[kind], uid_at[kind] = block, before
    player, at = blocks["Player"], uid_at["Player"]
    struct.pack_into("<HH", player, at - 204, ca, ca + 10)
    struct.pack_into("<HH", player, at - 78, 61, 168)
    player[at + 52:at + 56] = encode_date(dt.date(1981, 12, 11))
    player[at - 48] = 0b0100_0001  # moves 0 e 6
    for attribute in {a.fmm_index: a for a in attributes.values()}.values():
        raw = playing_raw_by_fmm_index[attribute.fmm_index]
        blocks["Playing"][uid_at["Playing"] + attribute.rel] = raw
    return LivePlayer(uid, blocks, uid_at)


def saviola() -> LivePlayer:
    fields = json.loads((ROOT / "reverse/fmm/playing_attributes_layout.json").read_text(encoding="utf-8"))["fields"]
    raw = [x["raw_value"] for x in sorted(fields, key=lambda x: x["fmm_index"])]
    return fake_player(3100367, 160, raw)


def zidane() -> LivePlayer:
    anchor = json.loads((ROOT / "reverse/fmm/anchor_8076.json").read_text(encoding="utf-8"))
    raw = [x.get("raw_value", x.get("value")) for x in anchor["playing_attributes"]]
    return fake_player(8076, 185, raw)


class DecodeTest(unittest.TestCase):

    def test_saviola_matches_screen(self) -> None:
        player = saviola()
        for name, shown in SAVIOLA_SCREEN.items():
            self.assertEqual(player.attribute_value(name), shown, name)

    def test_zidane_matches_screen(self) -> None:
        player = zidane()
        for name, shown in ZIDANE_SCREEN.items():
            self.assertEqual(player.attribute_value(name), shown, name)


class PlanTest(unittest.TestCase):

    def test_saviola_experiment(self) -> None:
        player = saviola()
        writes = player.plan({
            "ca": 111, "pa": 199, "height": 201, "weight": 99,
            "attributes": {"Finta": 1, "Cruzamentos": 20, "Velocidade": 2},
            "preferred_moves": {"add": ["Curls Ball"], "remove": [0]},
        })
        self.assertTrue(writes)
        self.assertEqual(player.get("ca"), 111)
        self.assertEqual(player.get("pa"), 199)
        self.assertEqual(player.get("height"), 201)
        self.assertEqual(player.get("weight"), 99)
        self.assertEqual(player.attribute_value("Finta"), 1)
        self.assertEqual(player.attribute_value("Cruzamentos"), 20)
        self.assertEqual(player.attribute_value("Velocidade"), 2)
        self.assertTrue(player.move_active(11))
        self.assertFalse(player.move_active(0))
        self.assertTrue(player.move_active(6))

    def test_profile_and_caps_from_montar_elencos(self) -> None:
        player = saviola()
        player.plan({
            "international_caps": 46, "international_goals": 3,
            "personality": {"Ambition": 17, "Temperament": 6},
            "attributes": {"Consistency": 16, "Imp. match": 15, "Injury prone.": 4},
            "preferred_moves": {"add": ["Cuts Inside"], "remove": ["Runs With Ball Down Left"]},
        })
        self.assertEqual((player.get("international_caps"), player.get("international_goals")), (46, 3))
        self.assertEqual(player.summary()["personality"]["Ambition"], 17)
        self.assertEqual(player.attribute_value("Consistency"), 16)
        self.assertEqual(player.attribute_value("Injury prone."), 4)
        self.assertTrue(player.move_active(39))
        self.assertFalse(player.move_active(0))

    def test_ca_change_keeps_relative_attributes(self) -> None:
        player = saviola()
        player.plan({"ca": 111})
        for name, shown in SAVIOLA_SCREEN.items():
            self.assertEqual(player.attribute_value(name), shown, name)

    def test_every_value_round_trips(self) -> None:
        for ca in (40, 111, 160, 185, 200):
            player = saviola()
            for value in range(1, 21):
                player.plan({"ca": ca, "attributes": {"Passe": value, "Velocidade": value}})
                self.assertEqual(player.attribute_value("Passe"), value, (ca, value))
                self.assertEqual(player.attribute_value("Velocidade"), value, (ca, value))

    def test_rejects_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            saviola().plan({"attributes": {"Passe": 21}})
        with self.assertRaises(ValueError):
            saviola().plan({"ca": 0})
        with self.assertRaises(KeyError):
            saviola().plan({"attributes": {"Chute de Bicicleta": 10}})

    def test_birth_date_with_year_shift(self) -> None:
        player = saviola()
        player.plan({"birth_date": "2004-02-29"}, year_shift=-21)
        self.assertEqual(player.born(), dt.date(1983, 2, 28))


class DateTest(unittest.TestCase):

    def test_saviola_born_matches_fmm_diff(self) -> None:
        # Diff confirmado: 11/12/1981 -> dia 344 (base zero).
        self.assertEqual(encode_date(dt.date(1981, 12, 11)), struct.pack("<HH", 344, 1981))
        self.assertEqual(decode_date(struct.pack("<HH", 345, 1981)), dt.date(1981, 12, 12))

    def test_shift_years_handles_leap_day(self) -> None:
        self.assertEqual(shift_years(dt.date(2004, 2, 29), -21), dt.date(1983, 2, 28))


if __name__ == "__main__":
    unittest.main()
