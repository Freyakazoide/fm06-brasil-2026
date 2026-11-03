"""Notícia de repercussão depois da resposta (docs/SALA_DE_IMPRENSA.md, §8.8).

Monta, a partir da resposta gravada (estado.json), uma matéria do veículo que perguntou: manchete,
trecho da declaração, reação do jogador, do elenco, credibilidade do treinador com o veículo e o
follow-up. Determinística: a mesma resposta gera sempre o mesmo texto (semente = chave da pauta).
Só fica na Sala (estado.json/eventos.jsonl); a notícia na caixa de entrada do FM06 é outro passo.
"""

from __future__ import annotations

import hashlib
import re

# manchetes por tom da resposta; {club}, {player}, {subject} e {outlet} são preenchidos
HEADLINES = {
    "apoio": ("{club} fecha com {player}: \"Ele tem nossa confiança\"",
              "Técnico do {club} sai em defesa de {player}",
              "{player} ganha respaldo público no {club}"),
    "cobranca": ("Técnico cobra {player} publicamente após {subject}",
                 "\"Precisa reagir\": {club} sobe o tom com {player}",
                 "{player} na mira: cobrança aberta no {club}"),
    "tensao": ("Coletiva tensa: técnico do {club} rebate críticas sobre {subject}",
               "{club} parte para o confronto e esquenta o debate sobre {player}",
               "Resposta dura do técnico vira assunto no {club}"),
    "neutro": ("{club} define posição sobre {subject}",
               "Técnico do {club} comenta {subject} e evita polêmica",
               "\"Vamos analisar com calma\": {club} trata {subject} internamente"),
}
WARM = {"acolhedora", "positiva", "entusiasmada", "segura", "cuidadosa", "confiante", "construtiva", "convincente"}
HARD = {"firme", "exigente", "confrontadora"}


def _pick(options: tuple[str, ...], seed: str) -> str:
    return options[int.from_bytes(hashlib.blake2s(seed.encode("utf-8"), digest_size=4).digest(), "little") % len(options)]


def fill(text: str, context: dict) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: str(context.get(m.group(1), m.group(0))), text)


def mood(intention: dict) -> str:
    if intention["risk"] == "alto" or intention["tone"] in {"provocativa", "defensiva", "direta"} and intention["effects"]["media"] < 0:
        return "tensao"
    if intention["tone"] in HARD:
        return "cobranca"
    if intention["tone"] in WARM:
        return "apoio"
    return "neutro"


def player_reaction(name: str, delta: int, morale: dict | None) -> str:
    if delta >= 3:
        text = f"{name} gostou do respaldo e comentou com os companheiros que se sente valorizado."
    elif delta >= 1:
        text = f"{name} recebeu bem a fala do treinador."
    elif delta == 0:
        text = f"{name} não demonstrou reação; para ele, o assunto segue no dia a dia."
    elif delta >= -2:
        text = f"{name} não gostou de ver o assunto tratado em público."
    else:
        text = f"{name} ficou incomodado e a relação com o treinador ficou estremecida."
    if morale and "antes" in morale and morale["depois"] != morale["antes"]:
        text += f" (moral no jogo: {morale['antes']} → {morale['depois']})"
    return text


def squad_reaction(delta: int) -> str:
    if delta >= 2:
        return "O vestiário aprovou a postura; lideranças elogiaram a forma de conduzir o caso."
    if delta == 1:
        return "No elenco, a fala foi vista como coerente."
    if delta == 0:
        return "O elenco não se manifestou."
    return "Parte do elenco achou a exposição desnecessária."


def credibility(outlet: str, delta: int, total: int) -> str:
    move = "ganhou" if delta > 0 else "perdeu" if delta < 0 else "manteve"
    level = ("boa" if total >= 3 else "razoável" if total >= 0 else "abalada" if total >= -3 else "ruim")
    return f"Com {outlet}, o treinador {move} credibilidade; a relação está {level} ({total:+d})."


def build(key: str, answer: dict, intention: dict, situation: dict, player: dict, outlet: dict,
          context: dict, state: dict) -> dict:
    """Matéria de repercussão da resposta `key` (já gravada em `state`)."""
    effects = answer["effects"]
    name = player.get("short_name") or player.get("name") or "o jogador"
    ctx = {**context, "player": name, "subject": situation["title"].lower(), "outlet": outlet["name"]}
    kind = mood(intention)
    extras = []
    if effects["fans"]:
        extras.append("A torcida " + ("aprovou a fala nas redes." if effects["fans"] > 0 else "reagiu mal nas redes."))
    if effects["board"]:
        extras.append("A diretoria " + ("gostou do tom." if effects["board"] > 0 else "não gostou da exposição."))
    return {
        "veiculo": outlet["id"], "veiculo_nome": outlet["name"], "tom": kind,
        "manchete": fill(_pick(HEADLINES[kind], key), ctx),
        "trecho": fill(intention["text"], ctx),
        "jogador": player_reaction(name, effects["player"], answer.get("moral")),
        "elenco": squad_reaction(effects["squad"]),
        "credibilidade": credibility(outlet["name"], effects["media"], state["credibilidade"].get(outlet["id"], 0)),
        "outros": extras,
        "follow_up": {"pergunta": fill(intention["follow_up"], ctx), "status": "pendente"},
    }
