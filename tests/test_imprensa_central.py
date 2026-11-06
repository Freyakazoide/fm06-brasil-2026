from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "imprensa"))

import central  # noqa: E402
import estado  # noqa: E402


def news(serie: int, classe: str, **extra) -> dict:
    return {"serie": serie, "classe": classe, "data": "2026-08-12", "lida": False, "jogador": 0, "resposta": -1, **extra}


def test_module_follows_game_category() -> None:
    assert central.module_of("Imprensa") == "imprensa"
    assert central.module_of("Lesões") == "medico"
    assert central.module_of("Transf.") == "transferencias" and central.module_of("Contratos") == "transferencias"
    assert central.module_of("Mensagens") == "geral" and central.module_of(None) == "geral"


def test_items_merge_inbox_captures_and_texts() -> None:
    inbox = [news(1042, "PHYSIO_REPORT_NEWS_ITEM", resposta=-3, lida=True), news(1043, "PHYSIO_REPORT_NEWS_ITEM"),
             news(995, "PHYSIO_REPORT_NEWS_ITEM", resposta=10, data="2026-07-30")]
    captures = [news(1036, "MOM_SUMMARY_NEWS", exclusiva=True, manchete="Breno em forma", corpo="..."),
                news(1043, "PHYSIO_REPORT_NEWS_ITEM", exclusiva=True)]            # ainda na caixa: conta uma vez
    texts = {"1042:PHYSIO_REPORT_NEWS_ITEM:2026-08-12:-3": {"manchete": "Gustagol informa sobre Zé Carlos", "corpo": "costela"},
             "1043:TEAM_FORM_NEWS:2026-08-12": {"manchete": "de outro save", "corpo": "x"}}   # mesma série, outra notícia
    out = central.items(inbox, captures, texts)
    assert [n["serie"] for n in out] == [1043, 1042, 1036, 995]
    by = {n["serie"]: n for n in out}
    assert by[1042]["pendente"] and by[1042]["manchete"].startswith("Gustagol") and by[1042]["modulo"] == "medico"
    assert by[995]["respondida"] and not by[995]["pendente"]
    assert by[1036]["onde"] == "central" and by[1036]["manchete"] == "Breno em forma"
    assert by[1043]["onde"] == "jogo" and by[1043]["manchete"] is None


def test_payload_counts_per_module() -> None:
    value = central.payload([news(1, "PHYSIO_REPORT_NEWS_ITEM", resposta=-3), news(2, "TEAM_FORM_NEWS", lida=True)], [], {}, {})
    medico = next(m for m in value["modulos"] if m["id"] == "medico")
    assert medico == {"id": "medico", "nome": "Departamento Médico", "total": 1, "nao_lidas": 1, "pendentes": 1}
    assert value["sem_texto"] == 2


def test_texts_cache(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(estado, "BASE", tmp_path)
    estado.add_texts("demo", {"7:A:x": {"manchete": "a", "corpo": "b"}})
    estado.add_texts("demo", {"8:B:y": {"manchete": "c", "corpo": "d"}})
    assert set(estado.texts("demo")) == {"7:A:x", "8:B:y"}


def test_captures_from_a_newer_save_are_hidden() -> None:
    caps = [news(1036, "MOM_SUMMARY_NEWS", data="2026-08-09"), news(1027, "PRE_MATCH_ODDS_NEWS", data="2026-08-05")]
    assert [n["serie"] for n in central.current(caps, "2026-08-05")] == [1027]
    assert len(central.current(caps, None)) == 2


def test_news_screen_opens_the_page_once() -> None:
    import servidor
    other, news_screen = 0x63736670, servidor.NEWS_SECTION
    w = servidor.ScreenWatcher("http://x/noticias")
    assert not w.step(news_screen, 5, 1000.0)                      # 1ª leitura: só a base
    assert not w.step(other, 6, 1001.0)                             # outra tela
    assert w.step(news_screen, 7, 1002.0)                           # entrou em Notícias
    assert not w.step(news_screen, 7, 1003.0)                       # continua nela
    w.step(other, 8, 1020.0)
    assert w.step(news_screen, 9, 1021.0)                           # voltou, sem página aberta
    w.last_poll = 1030.0
    w.step(other, 10, 1032.0)
    assert not w.step(news_screen, 11, 1033.0)                      # página já aberta


def test_captured_news_is_read_only_in_the_central(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(estado, "BASE", tmp_path)
    news_item = news(1037, "MEDIA_COMMENT_NEWS_ITEM", exclusiva=True, lida=True)     # o jogo abriu sozinho
    assert central.items([], [news_item], {})[0]["lida"] is False
    key = central.text_key(news_item)
    estado.add_read("demo", key)
    estado.add_read("demo", key)
    assert estado.reads("demo") == [key]
    assert central.items([], [news_item], {}, frozenset(estado.reads("demo")))[0]["lida"] is True
    in_game = news(1016, "MATCH_SUMMARY_NEWS", lida=True)
    assert central.items([in_game], [], {})[0]["lida"] is True                       # na caixa: vale o jogo


def test_medical_groups_by_player_and_puts_decisions_first() -> None:
    import medico
    items = central.items([news(1042, "PHYSIO_REPORT_NEWS_ITEM", jogador=7, resposta=-3),
                           news(1021, "INJURY_FULL_TRAINING_NEWS", jogador=8, data="2026-08-03", lida=True),
                           news(1000, "INJURY_INJURED_NEWS", jogador=8, data="2026-07-20", lida=True),
                           news(1, "TEAM_FORM_NEWS")], [], {})
    value = medico.payload(items, [{"id": 8, "short_name": "Mailson", "morale": 6}], {})
    assert [p["id"] for p in value["jogadores"]] == [7, 8] and value["pendentes"] == 1
    assert value["jogadores"][0]["situacao"] == "Decisão pendente" and not value["jogadores"][0]["no_elenco"]
    mailson = value["jogadores"][1]
    assert mailson["situacao"] == "Liberado" and len(mailson["noticias"]) == 2 and mailson["nome"] == "Mailson"


def test_text_is_read_again_after_the_reply() -> None:
    waiting, answered = news(1067, "RED_CARD_BAN_NEWS", resposta=-3), news(1067, "RED_CARD_BAN_NEWS", resposta=1)
    assert central.text_key(news(1067, "RED_CARD_BAN_NEWS")) == "1067:RED_CARD_BAN_NEWS:2026-08-12"
    assert central.text_key(waiting) != central.text_key(answered)


def test_reply_code_calls_slot_22_with_apply_flag() -> None:
    sys.path.insert(0, str(ROOT / "tools" / "re"))
    import responder_noticia as r
    code = r.reply_code(0x11223344, 0x55667788)
    assert bytes.fromhex("6A01 6888776655 B944332211 8B01 FF5058") in code
    assert code.endswith(bytes.fromhex("33C0C20400"))


def test_only_waiting_news_of_a_known_kind_offers_buttons() -> None:
    waiting = central.item(news(1067, "RED_CARD_BAN_NEWS", resposta=-3), None)
    assert [o["id"] for o in waiting["opcoes"]] == [1, 2] and waiting["pendente"]
    assert central.item(news(1067, "RED_CARD_BAN_NEWS", resposta=1), None)["opcoes"] == []
    assert central.item(news(1042, "PHYSIO_REPORT_NEWS_ITEM", resposta=-3), None)["opcoes"] == []   # ainda no jogo


def test_park_code_runs_the_job_on_the_main_thread() -> None:
    sys.path.insert(0, str(ROOT / "tools" / "re"))
    import laco
    code = laco.cave_code(0x30000000)
    assert code.startswith(laco.SIGNATURE)
    assert bytes.fromhex("6A00B800013030FFD0") in code and code[laco.CODE:].count(laco.ORIGINAL) == 1
    assert code.endswith(((laco.RESUME_AT - (0x30000000 + len(code))) & 0xFFFFFFFF).to_bytes(4, "little"))
