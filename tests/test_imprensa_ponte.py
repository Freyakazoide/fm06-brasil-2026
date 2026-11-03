from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "imprensa"))
sys.path.insert(0, str(ROOT / "tools" / "central"))

import ponte  # noqa: E402


def central_players() -> list[dict]:
    import importlib.util
    spec = importlib.util.spec_from_file_location("central_demo", ROOT / "tools" / "central" / "demo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.payload()["jovens"]


def test_contract_shape_from_central_players() -> None:
    data = ponte.payload(central_players(), today=dt.date(2026, 8, 4), club="Figueirense")
    assert data["mode"] == "jogo" and data["players"]
    for p in data["players"]:
        assert {"id", "name", "short_name", "age", "position", "morale", "form", "stats", "personality", "status"} <= set(p)
        assert set(p["personality"]) == set(ponte.TRAITS)
        assert {"matches", "goals", "assists", "rating", "minutes"} <= set(p["stats"])


def test_agenda_uses_real_triggers_one_topic_per_player() -> None:
    data = ponte.payload(central_players(), today=dt.date(2026, 8, 4), club="Figueirense")
    ids = {s["id"] for s in data["situations"]}
    players = {p["id"] for p in data["players"]}
    outlets = {o["id"]: o for o in data["outlets"]}
    assert data["agenda"], "a demo da Central deve disparar algum gatilho"
    assert len({a["player_id"] for a in data["agenda"]}) == len(data["agenda"])
    for item in data["agenda"]:
        assert item["situation_id"] in ids and item["player_id"] in players and item["reason"]
        assert item["journalist_id"] in {j["id"] for j in outlets[item["outlet_id"]]["journalists"]}
    assert sum(a["active"] for a in data["agenda"]) == 1


def test_triggers_follow_the_data() -> None:
    base = {"uid": 1, "nome": "Teste Silva", "idade": 18, "moral": 5, "pot": 9, "time": "Sub-20",
            "contrato_fim": "2026-10-01", "estatisticas": {"jogos": 0, "banco": 0, "forma": [5, 6, 6, 6, 5]}}
    found = {t[0] for t in ponte.triggers(base, ponte.player(base), dt.date(2026, 8, 4))}
    assert {"poor_match", "poor_streak", "loan", "renewal", "mental_pressure", "youth_comparison"} <= found
    calm = dict(base, moral=15, pot=4, contrato_fim="2029-12-31", estatisticas={"jogos": 10, "banco": 0, "forma": [7, 7, 7, 7, 7]})
    assert not {t[0] for t in ponte.triggers(calm, ponte.player(calm), dt.date(2026, 8, 4))}


def test_read_news_becomes_the_current_topic() -> None:
    players = central_players()
    uid = players[0]["uid"]
    news = [{"serie": 965, "classe": "MEDIA_PLAYER_FORM_NEWS", "data": "2026-07-23", "lida": True, "jogador": uid},
            {"serie": 900, "classe": "MEDIA_PLAYER_FORM_NEWS", "data": "2026-07-20", "lida": True, "jogador": 999999}]
    data = ponte.payload(players, today=dt.date(2026, 8, 4), club="Figueirense", news=news)
    first = data["agenda"][0]
    assert first["active"] and first["news_serial"] == 965 and first["player_id"] == uid
    assert "notícia lida no jogo (23/07)" in first["reason"]
    assert all(a.get("news_serial") != 900 for a in data["agenda"])        # jogador de outro clube


def test_form_news_reads_the_last_game() -> None:
    import noticias
    item = {"classe": "MEDIA_PLAYER_FORM_NEWS"}
    assert noticias.situation_for(item, {"form": [7.0, 7.0, 7.0, 6.0, 5.0]}) == "poor_streak"
    assert noticias.situation_for(item, {"form": [5.0, 6.0, 6.0, 7.0, 8.0]}) == "match_star"
    assert noticias.situation_for({"classe": "RED_CARD_BAN_NEWS"}, None) == "red_card"
    assert noticias.situation_for({"classe": "TESTE_DESCONHECIDO"}, None) is None


def test_agenda_uses_only_real_news_when_there_are_any() -> None:
    players = central_players()
    a, b = players[0]["uid"], players[1]["uid"]
    inbox = [{"serie": 10, "classe": "RED_CARD_BAN_NEWS", "data": "2026-08-01", "lida": False, "jogador": a},
             {"serie": 11, "classe": "INJURY_INJURED_NEWS", "data": "2026-08-02", "lida": True, "jogador": b},
             {"serie": 3, "classe": "RED_CARD_BAN_NEWS", "data": "2026-06-01", "lida": True, "jogador": b}]   # velha
    data = ponte.payload(players, today=dt.date(2026, 8, 4), club="Figueirense", inbox=inbox, news=[inbox[0]])
    assert [x["key"] for x in data["agenda"]] == ["noticia-10", "noticia-11"]     # a recém-lida primeiro
    assert data["agenda"][0]["when"] == "agora" and data["agenda"][1]["status"] == "lida no jogo"
    assert "ainda não aberta" in data["agenda"][0]["reason"]
    assert not any(x["key"].startswith("2026") for x in data["agenda"])          # sem gatilho inventado
