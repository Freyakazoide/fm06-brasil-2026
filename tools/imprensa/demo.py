"""Contexto inteiramente fictício para desenvolver a Sala de Imprensa sem o FM06."""

from __future__ import annotations

import datetime as dt

import banco
import veiculos


PLAYERS = [
    {
        "id": 2000007988,
        "name": "Afonso Guedes",
        "short_name": "Guedes",
        "age": 16,
        "position": "Meia central",
        "number": 28,
        "morale": 11,
        "form": [6.1, 6.3, 5.9, 6.6, 6.2],
        "stats": {"matches": 13, "goals": 2, "assists": 4, "rating": 6.34, "minutes": 738},
        "personality": {"ambition": 16, "professionalism": 14, "pressure": 8, "temperament": 12, "loyalty": 15, "controversy": 5},
        "status": "Jovem de alto potencial",
    },
    {
        "id": 2000008014,
        "name": "Rafael Venâncio",
        "short_name": "Venâncio",
        "age": 18,
        "position": "Goleiro",
        "number": 31,
        "morale": 16,
        "form": [7.2, 7.0, 7.7, 6.9, 8.1],
        "stats": {"matches": 18, "goals": 0, "assists": 0, "rating": 7.18, "minutes": 1620},
        "personality": {"ambition": 12, "professionalism": 17, "pressure": 15, "temperament": 15, "loyalty": 13, "controversy": 3},
        "status": "Titular em ascensão",
    },
    {
        "id": 2000008071,
        "name": "Diego Rodrigues",
        "short_name": "Rodrigues",
        "age": 20,
        "position": "Zagueiro",
        "number": 4,
        "morale": 7,
        "form": [5.8, 6.0, 6.1, 5.7, 6.3],
        "stats": {"matches": 22, "goals": 1, "assists": 0, "rating": 6.02, "minutes": 1811},
        "personality": {"ambition": 10, "professionalism": 11, "pressure": 6, "temperament": 7, "loyalty": 12, "controversy": 13},
        "status": "Sob pressão",
    },
]


AGENDA_BLUEPRINTS = [
    ("poor_streak", "ge", 0, "agora", True),
    ("training_star", "sportv", 1, "hoje · 18:30", False),
    ("transfer_interest", "lance", 1, "amanhã · 09:00", False),
    ("player_conflict", "radio-itatiaia", 2, "amanhã · 12:15", False),
    ("derby", "placar", 0, "quinta · 14:00", False),
    ("youth_comparison", "cazetv", 0, "sexta · 11:30", False),
    ("renewal", "o-globo", 1, "sexta · 17:00", False),
]


def payload() -> dict:
    situations = {item["id"]: item for item in banco.bank()}
    outlets = {item["id"]: item for item in veiculos.load_outlets()}
    agenda = []
    for index, (situation_id, outlet_id, player_index, when, active) in enumerate(AGENDA_BLUEPRINTS):
        situation = situations[situation_id]
        outlet = outlets.get(outlet_id, next(iter(outlets.values())))
        journalist = outlet["journalists"][index % len(outlet["journalists"])]
        agenda.append({
            "id": f"press-{index + 1:03d}", "key": f"demo-{index + 1:03d}",
            "situation_id": situation_id,
            "outlet_id": outlet["id"],
            "journalist_id": journalist["id"],
            "player_id": PLAYERS[player_index]["id"],
            "when": when,
            "active": active,
            "status": "em andamento" if active else "agendada",
            "headline": situation["title"],
            "urgency": situation["urgency"],
        })
    return {
        "schema_version": 1,
        "mode": "demo",
        "info": {
            "date": dt.date(2026, 8, 4).isoformat(),
            "club": "Figueirense", "career": "demo",
            "rival": "Avaí",
            "competition": "Campeonato Brasileiro",
            "manager": "Seu treinador",
            "fact": "não existe acordo assinado",
            "notice": "Demonstração local: nenhuma escolha é gravada no FM06.",
        },
        "players": PLAYERS,
        "outlets": list(outlets.values()),
        "situations": list(situations.values()),
        "agenda": agenda,
        "bank_stats": banco.stats(),
    }

