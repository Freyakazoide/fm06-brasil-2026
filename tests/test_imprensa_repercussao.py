from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "imprensa"))

import banco  # noqa: E402
import estado  # noqa: E402
import repercussao  # noqa: E402

SITUATIONS = {item["id"]: item for item in banco.bank()}
OUTLET = {"id": "sportv", "name": "SporTV"}
PLAYER = {"id": 8833546, "short_name": "Leonan"}
CONTEXT = {"club": "Figueirense", "rival": "Avaí", "competition": "a temporada", "manager": "Seu treinador"}


def story(situation_id: str, answer_id: str, effects: dict, moral: dict | None = None, credibility: int = 0) -> dict:
    situation = SITUATIONS[situation_id]
    intention = next(i for i in situation["intentions"] if i["id"] == answer_id)
    answer = {"effects": {**{k: 0 for k in estado.EFFECTS}, **effects}}
    if moral:
        answer["moral"] = moral
    state = {**estado.empty(), "credibilidade": {"sportv": credibility}}
    return repercussao.build("noticia-957", answer, intention, situation, PLAYER, OUTLET, CONTEXT, state)


def test_story_is_filled_and_deterministic() -> None:
    first = story("red_card", "listen", {"player": 2, "squad": 1, "board": 1}, {"antes": 9, "depois": 11})
    assert first == story("red_card", "listen", {"player": 2, "squad": 1, "board": 1}, {"antes": 9, "depois": 11})
    text = " ".join([first["manchete"], first["trecho"], first["jogador"], first["follow_up"]["pergunta"]])
    assert "{" not in text and "Leonan" in first["trecho"]
    assert "9 → 11" in first["jogador"] and first["follow_up"]["status"] == "pendente"
    assert first["outros"] == ["A diretoria gostou do tom."]


def test_mood_follows_tone_and_risk() -> None:
    assert story("poor_streak", "protect", {"player": 2})["tom"] == "apoio"
    assert story("poor_streak", "challenge", {"player": -1})["tom"] == "cobranca"
    assert story("poor_streak", "provoke", {"media": -2})["tom"] == "tensao"


def test_credibility_uses_running_total() -> None:
    assert "perdeu" in story("poor_streak", "provoke", {"media": -2}, credibility=-4)["credibilidade"]
    assert "ruim (-4)" in story("poor_streak", "provoke", {"media": -2}, credibility=-4)["credibilidade"]


def test_note_repercussion_persists(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(estado, "BASE", tmp_path)
    estado.record("demo", {"key": "k1", "situation_id": "red_card", "answer_id": "listen", "player_id": 1,
                           "outlet_id": "sportv", "effects": {"player": 2}})
    state = estado.note_repercussion("demo", "k1", {"manchete": "x"})
    assert state["respostas"]["k1"]["repercussao"] == {"manchete": "x"}
    assert estado.load("demo")["respostas"]["k1"]["repercussao"]["manchete"] == "x"
