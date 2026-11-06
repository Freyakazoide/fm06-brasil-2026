"""Central de Notícias (docs/SALA_DE_IMPRENSA.md, §8.9): a caixa do jogo e as notícias tiradas dela
numa lista só, separadas pelo módulo que vai cuidar de cada uma.

A categoria vem da classe (slot 10 da vtable, tools/imprensa/noticias_categorias.json); o texto, do
cache que o observador enche com a função do próprio jogo (texto_noticia.py); "pede resposta" vem do
campo +0x20 (noticias.REPLY: -2/-3/-4 esperando escolha, >= 0 já respondida).
"""

from __future__ import annotations

import json
from pathlib import Path

import noticias

HERE = Path(__file__).resolve().parent
CATEGORIES = {name: info["categoria_nome"]
              for name, info in json.loads((HERE / "noticias_categorias.json").read_text(encoding="utf-8")).items()}
MODULES = [("imprensa", "Sala de Imprensa", {"Imprensa"}), ("medico", "Departamento Médico", {"Lesões"}),
           ("transferencias", "Transferências", {"Transf.", "Contratos"}), ("geral", "Geral", None)]
WAITING = {-2, -3, -4}


def text_key(news: dict) -> str:
    """Chave do texto guardado: a série se repete quando um save mais antigo é carregado, então vai
    junto com a classe e a data."""
    return f"{news['serie']}:{news['classe']}:{news.get('data')}"


def current(captures: list[dict], today: str | None) -> list[dict]:
    """Capturadas que existem neste save: as de data depois da data do jogo vieram de outra linha do
    tempo (save mais novo, depois recarregado um mais antigo)."""
    return [n for n in captures if not today or not n.get("data") or n["data"] <= today]


def module_of(category: str | None) -> str:
    return next(key for key, _, cats in MODULES if cats is None or category in cats)


def item(news: dict, text: dict | None, read: frozenset[str] = frozenset()) -> dict:
    """`read`: abertas na Central. Na capturada só isso conta: o jogo abre sozinho a 1ª notícia do dia e
    a marca como lida antes de ela sair da caixa."""
    category = CATEGORIES.get(news["classe"])
    reply = news.get("resposta", noticias.NO_REPLY)
    text = text or {}
    return {"serie": news["serie"], "classe": news["classe"], "assunto": noticias.label(news["classe"]),
            "categoria": category or "Outras", "modulo": module_of(category), "data": news.get("data"),
            "chave": text_key(news),
            "lida": text_key(news) in read if news.get("exclusiva") else bool(news.get("lida")),
            "jogador": news.get("jogador") or None,
            "pendente": reply in WAITING, "respondida": reply >= 0,
            "onde": "central" if news.get("exclusiva") else "jogo",
            "manchete": news.get("manchete") or text.get("manchete"), "corpo": news.get("corpo") or text.get("corpo")}


def items(inbox: list[dict], captures: list[dict], texts: dict[str, dict], read: frozenset[str] = frozenset()) -> list[dict]:
    """Caixa do jogo + capturadas (a capturada que ainda aparece na caixa conta uma vez), mais nova primeiro."""
    seen = {n["serie"] for n in inbox}
    every = list(inbox) + [n for n in captures if n["serie"] not in seen]
    out = [item(n, texts.get(text_key(n)), read) for n in every]
    return sorted(out, key=lambda n: (n["data"] or "", n["serie"]), reverse=True)


def payload(inbox: list[dict], captures: list[dict], texts: dict[str, dict], info: dict,
            read: frozenset[str] = frozenset()) -> dict:
    news = items(inbox, captures, texts, read)
    modules = [{"id": key, "nome": name, "total": sum(n["modulo"] == key for n in news),
                "nao_lidas": sum(n["modulo"] == key and not n["lida"] for n in news),
                "pendentes": sum(n["modulo"] == key and n["pendente"] for n in news)} for key, name, _ in MODULES]
    return {"info": info, "modulos": modules, "noticias": news,
            "sem_texto": sum(n["manchete"] is None and n["onde"] == "jogo" for n in news)}
