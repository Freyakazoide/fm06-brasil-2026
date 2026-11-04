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
    texts = {"1042:PHYSIO_REPORT_NEWS_ITEM:2026-08-12": {"manchete": "Gustagol informa sobre Zé Carlos", "corpo": "costela"},
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
