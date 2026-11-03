"""Ponte de leitura FM06 -> Sala de Imprensa (docs/SALA_DE_IMPRENSA.md, §7 e §8.5).

Só leitura. Reaproveita o leitor da Central (tools/central/leitor.py), sem repetir offsets, e entrega o
mesmo contrato do demo.py: jogadores normalizados e uma agenda montada por gatilhos reais. Os gatilhos
cobrem só o que a Central já lê (forma, estatísticas, contrato, moral, personalidade, idade); clássico,
lesão, vestiário e mercado ficam de fora até haver fonte no jogo.

A função `payload` recebe os jogadores no formato da Central (dicionários), para ser testada sem o jogo.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import sys
from dataclasses import asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools" / "central"))

import adjunto  # noqa: E402
import banco  # noqa: E402
import veiculos  # noqa: E402

TRAITS = {"ambition": "Ambição", "professionalism": "Profissionalismo", "pressure": "Pressão",
          "temperament": "Temperamento", "loyalty": "Lealdade", "controversy": "Polêmica"}
SLOTS = ["agora", "hoje · 18:30", "amanhã · 09:00", "amanhã · 12:15", "quinta · 14:00", "sexta · 11:30",
         "sexta · 17:00", "sábado · 10:00"]
# meio preferido por situação (§8.4): pós-jogo em TV e rádio, mercado em site, perfil em revista/jornal
MEDIUM = {"match_star": "tv", "poor_match": "tv", "poor_streak": "site", "red_card": "radio",
          "senior_debut": "tv", "loan": "site", "few_minutes": "site", "renewal": "site",
          "mental_pressure": "jornal", "stagnation": "jornal", "youth_comparison": "revista"}


def position_name(codes: list[str]) -> str:
    for code in codes:
        if code in adjunto.PROFILES:
            return adjunto.PROFILES[code][0].capitalize()
    return codes[0] if codes else "—"


def season(stats: dict) -> tuple[dict, bool]:
    """Estatística da temporada no formato do contrato; oficiais se houver, senão as não oficiais."""
    games = (stats.get("jogos") or 0) + (stats.get("banco") or 0)
    source, unofficial = stats, False
    if not games and (stats.get("nao_oficiais") or {}).get("jogos", 0) + (stats.get("nao_oficiais") or {}).get("banco", 0):
        source, unofficial = stats["nao_oficiais"], True
    return {"matches": (source.get("jogos") or 0) + (source.get("banco") or 0), "goals": source.get("gols") or 0,
            "assists": source.get("assistencias") or 0, "rating": source.get("nota") or 0,
            "minutes": source.get("minutos") or 0, "unofficial": unofficial}, unofficial


def player(j: dict) -> dict:
    stats, unofficial = season(j.get("estatisticas") or {})
    traits = (j.get("personalidade") or {}).get("tracos") or {}
    return {
        "id": j["uid"], "name": j["nome"], "short_name": j.get("apelido") or j["nome"].split()[-1],
        "age": j["idade"], "position": position_name(j.get("posicoes") or []), "number": j.get("numero"),
        "morale": j.get("moral", 0), "form": [float(v) for v in (j.get("estatisticas") or {}).get("forma") or []],
        "stats": stats, "personality": {key: traits.get(name, 10) for key, name in TRAITS.items()},
        "status": status(j, stats, unofficial), "team": j.get("time", ""),
    }


def status(j: dict, stats: dict, unofficial: bool) -> str:
    if j.get("moral", 10) <= 7:
        return "Moral baixa"
    if unofficial:
        return f"Destaque do {j.get('time', 'time')}" if stats["rating"] >= 6.8 else f"Jogando pelo {j.get('time', 'time')}"
    if j["idade"] <= 19 and stats["matches"]:
        return "Jovem já no time de cima"
    return "Titular em ascensão" if stats["rating"] >= 6.8 else "Elenco principal"


def triggers(j: dict, p: dict, today: dt.date) -> list[tuple[str, int, str]]:
    """(situação, peso, motivo) que os dados reais deste jogador disparam."""
    out = []
    form, st = p["form"], j.get("estatisticas") or {}
    official = (st.get("jogos") or 0) + (st.get("banco") or 0)
    # hipótese: Pfrm traz a nota mais recente primeiro (como a aba Forma do jogo)
    if form and form[0] >= 8:
        out.append(("match_star", 80, f"nota {form[0]:.0f} no último jogo"))
    if form and form[0] <= 5:
        out.append(("poor_match", 60, f"nota {form[0]:.0f} no último jogo"))
    if len(form) >= 5 and sum(v < 6.5 for v in form) >= 3 and sum(form) / len(form) < 6.3:
        out.append(("poor_streak", 70, "três notas abaixo de 6,5 nos últimos cinco jogos"))
    if (st.get("vermelhos") or 0) > 0:
        out.append(("red_card", 40, f"{st['vermelhos']} vermelho(s) na temporada"))
    if j["idade"] <= 19 and 1 <= official <= 3:
        out.append(("senior_debut", 75, f"{official} jogo(s) oficial(is) aos {j['idade']} anos"))
    if j["idade"] >= 18 and not official and j.get("time") not in (None, "", "Principal"):
        out.append(("loan", 45, f"sem jogos oficiais, joga pelo {j.get('time')}"))
    end = j.get("contrato_fim")
    if end and dt.date.fromisoformat(end) - today <= dt.timedelta(days=180):
        out.append(("renewal", 65, f"contrato até {dt.date.fromisoformat(end):%d/%m/%Y}"))
    if j.get("moral", 10) <= 7:
        out.append(("mental_pressure", 55, f"moral {j.get('moral')}/20"))
    growth = ((j.get("personalidade") or {}).get("evolucao") or {}).get("nivel")
    if growth == "baixa" and j["idade"] <= 21:
        out.append(("stagnation", 35, "personalidade aponta risco de estagnar"))
    if j["idade"] <= 19 and j.get("pot", 0) >= 8:
        out.append(("youth_comparison", 50, f"potencial {j['pot'] / 2:.1f} estrelas"))
    return out


def pick(seed: str, items: list) -> object:
    return items[int(hashlib.sha1(seed.encode()).hexdigest(), 16) % len(items)]


def outlet_for(situation_id: str, club: str, outlets: list[dict], seed: str) -> dict:
    """§8.4: veículo do clube, depois da cidade (não há cidade do clube ainda), depois nacional por meio."""
    local = [o for o in outlets if club in o["clubs"]]
    if local:
        return pick(seed, local)
    national = [o for o in outlets if o["scope"] == "pais"]
    medium = [o for o in national if o["medium"] == MEDIUM.get(situation_id)]
    return pick(seed, medium or national)


def payload(jovens: list[dict], *, today: dt.date, club: str, limit: int = 7) -> dict:
    situations = {item["id"]: item for item in banco.bank()}
    outlets = veiculos.load_outlets()
    players = [player(j) for j in jovens]
    candidates = []
    for j, p in zip(jovens, players):
        for situation_id, weight, reason in triggers(j, p, today):
            if situation_id in situations:
                candidates.append((weight, situation_id, p, reason))
    candidates.sort(key=lambda c: (-c[0], c[2]["name"]))
    agenda, used = [], set()
    for weight, situation_id, p, reason in candidates:
        if p["id"] in used or len(agenda) >= limit:                 # um assunto por jogador
            continue
        used.add(p["id"])
        seed = f"{today}:{situation_id}:{p['id']}"
        outlet = outlet_for(situation_id, club, outlets, seed)
        situation = situations[situation_id]
        index = len(agenda)
        agenda.append({
            "id": f"press-{index + 1:03d}", "situation_id": situation_id, "outlet_id": outlet["id"],
            "journalist_id": pick(seed, outlet["journalists"])["id"], "player_id": p["id"],
            "when": SLOTS[index % len(SLOTS)], "active": index == 0,
            "status": "em andamento" if index == 0 else "agendada", "headline": situation["title"],
            "urgency": situation["urgency"], "reason": reason, "weight": weight,
        })
    shown = {a["player_id"] for a in agenda}
    roster = [p for p in players if p["id"] in shown] + [p for p in players if p["id"] not in shown]
    return {
        "schema_version": 1, "mode": "jogo",
        "info": {"date": today.isoformat(), "club": club, "rival": "o próximo adversário",
                 "competition": "a temporada", "manager": "Seu treinador", "fact": "nada foi oficializado",
                 "notice": "Dados lidos do FM06 aberto (só leitura): nenhuma escolha é gravada no jogo."},
        "players": roster, "outlets": outlets, "situations": list(situations.values()), "agenda": agenda,
        "bank_stats": banco.stats(),
    }


def live_payload(club: str) -> dict:
    """Lê o elenco inteiro do clube humano no jogo aberto (todos os times, todas as idades)."""
    import leitor
    jovens, info = leitor.jovens(max_age=99)
    year, month, day = (int(x) for x in info["data"].split("-"))
    return payload([asdict(j) for j in jovens], today=dt.date(year, month, day), club=club)
