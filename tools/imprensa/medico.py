"""Departamento Médico (docs/SALA_DE_IMPRENSA.md, §8.10): as notícias de lesão da Central, por jogador.

A situação vem da última notícia do jogador, não do estado da lesão no jogo (esse campo ainda não foi
lido). Responder ao fisioterapeuta continua no jogo: notícia pendente só é destacada aqui.
"""

from __future__ import annotations

STATUS = {"INJURY_FULL_TRAINING_NEWS": ("Liberado", "good"), "INJURY_LIGHT_TRAINING_NEWS": ("Treino leve", "warn"),
          "INJURY_INJURED_NEWS": ("Lesionado", "bad"), "PHYSIO_REPORT_NEWS_ITEM": ("Com o fisioterapeuta", "bad"),
          "INJURY_SUMMARY_NEWS": ("Em acompanhamento", "warn"), "MEDIA_INJURY_NEWS": ("Na imprensa", "warn"),
          "MEDIA_INJURY_CRISIS_NEWS": ("Na imprensa", "warn"), "BUST_UP_RESPONSE_NEWS": ("Em acompanhamento", "warn")}


def player_row(uid: int, news: list[dict], roster: dict[int, dict]) -> dict:
    latest, player = news[0], roster.get(uid, {})
    label, tone = (("Decisão pendente", "pending") if any(n["pendente"] for n in news)
                   else STATUS.get(latest["classe"], ("Em acompanhamento", "warn")))
    return {"id": uid, "nome": player.get("short_name") or latest["manchete"] or f"Jogador {uid}",
            "nome_completo": player.get("name"), "posicao": player.get("position"), "idade": player.get("age"),
            "moral": player.get("morale"), "time": player.get("team"), "no_elenco": bool(player),
            "situacao": label, "tom": tone, "ultima": latest["data"], "noticias": news,
            "pendentes": sum(n["pendente"] for n in news), "nao_lidas": sum(not n["lida"] for n in news)}


def payload(news: list[dict], roster: list[dict], info: dict) -> dict:
    """`news`: itens da Central (central.items), mais novos primeiro."""
    by_uid, people = {}, {p["id"]: p for p in roster}
    medical = [n for n in news if n["modulo"] == "medico"]
    for item in medical:
        if item["jogador"]:
            by_uid.setdefault(item["jogador"], []).append(item)
    players = [player_row(uid, items, people) for uid, items in by_uid.items()]
    players.sort(key=lambda p: (not p["pendentes"], not p["no_elenco"], p["tom"] == "good", -p["nao_lidas"]))
    return {"info": info, "jogadores": players, "sem_jogador": [n for n in medical if not n["jogador"]],
            "pendentes": sum(p["pendentes"] for p in players)}
