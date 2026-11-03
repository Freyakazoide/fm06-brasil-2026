from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRESS = ROOT / "tools" / "imprensa"
sys.path.insert(0, str(PRESS))

import banco  # noqa: E402
import demo  # noqa: E402
import veiculos  # noqa: E402


def test_editorial_bank_is_large_and_consistent() -> None:
    stats = banco.stats()
    assert banco.validate() == []
    assert stats["situations"] >= 50
    assert stats["questions"] >= stats["situations"] * 3
    assert stats["response_combinations"] >= stats["situations"] * 8
    assert len({item["id"] for item in banco.SITUATIONS}) == stats["situations"]
    assert all(len(item["intentions"]) == 8 for item in banco.bank())


def test_every_intention_has_follow_up_and_bounded_demo_effects() -> None:
    for situation in banco.bank():
        for answer in situation["intentions"]:
            assert answer["text"] and answer["follow_up"]
            assert answer["risk"] in {"baixo", "médio", "alto"}
            assert set(answer["effects"]) == {"player", "squad", "fans", "board", "media", "training"}
            assert all(-4 <= value <= 4 for value in answer["effects"].values())


def test_all_csv_outlets_have_local_identity_and_two_journalists() -> None:
    outlets = veiculos.load_outlets()
    assert len(outlets) >= 23
    assert {item["name"] for item in outlets} >= {"ge", "Lance!", "SporTV", "Rádio Itatiaia", "O Globo"}
    assert all(len(item["journalists"]) == 2 for item in outlets)
    assert all(veiculos.logo_svg(item["id"]) for item in outlets)
    seeds = [person["seed"] for outlet in outlets for person in outlet["journalists"]]
    assert len(seeds) == len(set(seeds))


def test_demo_payload_does_not_require_a_save() -> None:
    payload = demo.payload()
    assert payload["mode"] == "demo"
    assert payload["players"] and payload["agenda"]
    assert len(payload["situations"]) == banco.stats()["situations"]
    assert len(payload["outlets"]) == len(veiculos.load_outlets())
    assert all(item["situation_id"] in {s["id"] for s in payload["situations"]} for item in payload["agenda"])

