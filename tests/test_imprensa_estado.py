from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "imprensa"))

import estado  # noqa: E402


def entry(**extra) -> dict:
    return {"key": "noticia-965", "situation_id": "poor_streak", "answer_id": "protect", "player_id": 2115610,
            "outlet_id": "sportv", "question": 1, "date": "2026-07-24", "news_serial": 965,
            "effects": {"player": 9, "squad": 1, "fans": -2, "board": 0, "media": -1, "training": 1}, **extra}


def test_record_sums_and_limits_effects(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(estado, "BASE", tmp_path)
    state = estado.record("figueirense-301306", entry())
    assert state["respostas"]["noticia-965"]["effects"]["player"] == estado.LIMIT       # 9 vira 4
    assert state["relacao"]["2115610"] == 4 and state["credibilidade"]["sportv"] == -1
    assert state["torcida"] == -2 and state["elenco"] == 1
    saved = estado.load("figueirense-301306")
    assert saved["respostas"]["noticia-965"]["answer_id"] == "protect"
    log = (tmp_path / "figueirense-301306" / "eventos.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(log) == 1 and json.loads(log[0])["key"] == "noticia-965"


def test_one_answer_per_topic_and_safe_names(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(estado, "BASE", tmp_path)
    estado.record("demo", entry())
    with pytest.raises(ValueError):
        estado.record("demo", entry())
    with pytest.raises(ValueError):
        estado.record("../fora", entry(key="outra"))
    with pytest.raises(ValueError):
        estado.record("demo", entry(key="sem-jogador", player_id=None))
    assert estado.save_id("Figueirense", 301306) == "figueirense-301306"
