from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools" / "imprensa"), str(ROOT / "tools" / "re")]

import banco  # noqa: E402
import noticias  # noqa: E402
import ponte  # noqa: E402

SITUATIONS = {item["id"]: item for item in banco.bank()}
PLAYERS = [{"id": 7, "name": "Henrique"}, {"id": 8, "name": "Mailson"}]


def news(serie: int, classe: str, **extra) -> dict:
    return {"serie": serie, "classe": classe, "data": "2026-08-12", "lida": False, "jogador": 7, "resposta": -1, **extra}


def test_kind_of_each_news() -> None:
    assert noticias.kind_of("RED_CARD_BAN_NEWS") == "expulsao"
    assert noticias.kind_of("PHYSIO_REPORT_NEWS_ITEM") == "lesao"
    assert noticias.kind_of("INJURY_FULL_TRAINING_NEWS") == "lesao"
    assert noticias.kind_of("MEDIA_INJURY_NEWS") == "imprensa"
    assert noticias.kind_of("MOM_SUMMARY_NEWS") == "imprensa"


def test_only_news_with_a_situation_reach_the_agenda() -> None:
    assert noticias.on_the_agenda(news(1, "RED_CARD_BAN_NEWS"), {7})
    assert not noticias.on_the_agenda(news(1, "RED_CARD_BAN_NEWS"), {8})        # outro clube
    assert not noticias.on_the_agenda(news(1, "TEAM_FORM_NEWS"), {7})           # fica só no jogo


def test_only_waiting_news_of_a_known_kind_offers_buttons() -> None:
    assert [o["id"] for o in noticias.options(news(1067, "RED_CARD_BAN_NEWS", resposta=-3))] == [1, 2]
    assert noticias.options(news(1067, "RED_CARD_BAN_NEWS", resposta=1)) == []
    assert noticias.options(news(1042, "PHYSIO_REPORT_NEWS_ITEM", resposta=-3)) == []   # ainda no jogo


def test_text_key_changes_with_the_reply() -> None:
    assert noticias.text_key(news(1067, "RED_CARD_BAN_NEWS")) == "1067:RED_CARD_BAN_NEWS:2026-08-12"
    assert noticias.text_key(news(1067, "RED_CARD_BAN_NEWS", resposta=-3)) != noticias.text_key(news(1067, "RED_CARD_BAN_NEWS", resposta=1))


def test_captures_from_a_newer_save_are_hidden() -> None:
    caps = [news(1036, "MOM_SUMMARY_NEWS", data="2026-08-09"), news(1027, "PRE_MATCH_ODDS_NEWS", data="2026-08-05")]
    assert [n["serie"] for n in noticias.current(caps, "2026-08-05")] == [1027]
    assert len(noticias.current(caps, None)) == 2


def test_decision_comes_first_with_text_and_buttons() -> None:
    ban = news(1067, "RED_CARD_BAN_NEWS", resposta=-3)
    press = news(1070, "MOM_SUMMARY_NEWS", jogador=8)
    texts = {noticias.text_key(ban): {"manchete": "Henrique suspenso", "corpo": "Um jogo."}}
    out = ponte.news_candidates([press, ban], set(), PLAYERS, SITUATIONS, dt.date(2026, 8, 13), texts)
    first = max(out, key=lambda c: c[0])[4]
    assert first["news_kind"] == "expulsao" and first["news_waiting"] and first["news_headline"] == "Henrique suspenso"
    assert [o["id"] for o in first["news_options"]] == [1, 2]


def test_news_screen_opens_the_page_only_with_a_decision_waiting() -> None:
    import servidor
    other, news_screen = 0x63736670, servidor.NEWS_SECTION
    w = servidor.ScreenWatcher("http://x/")
    assert not w.step(news_screen, 5, 1000.0)                                     # 1ª leitura: só a base
    assert not w.step(news_screen, 6, 1002.0, wanted=False)                       # nada esperando
    w.step(other, 7, 1003.0)
    assert w.step(news_screen, 8, 1004.0, wanted=True)
    w.step(other, 9, 1020.0)
    w.last_poll = 1030.0
    assert not w.step(news_screen, 10, 1033.0, wanted=True)                       # página já aberta


def test_park_code_runs_the_job_on_the_main_thread() -> None:
    import laco
    code = laco.cave_code(0x30000000)
    assert code.startswith(laco.SIGNATURE)
    assert bytes.fromhex("6A00B800010030FFD0") in code and code[laco.CODE:].count(laco.ORIGINAL) == 1


def test_reply_code_calls_slot_22_with_apply_flag() -> None:
    import responder_noticia as r
    code = r.reply_code(0x11223344, 0x55667788)
    assert bytes.fromhex("6A01 6888776655 B944332211 8B01 FF5058") in code
