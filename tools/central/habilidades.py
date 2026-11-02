"""Plano de habilidades da Central externa: movimentos preferidos aprendidos com treino.

O FM06 guarda os 48 movimentos preferidos como bits no jogador (6 bytes em UID-48, ver
reverse/fmm/preferred_moves_layout.json), mas não tem treino para aprendê-los. A Central cria essa
mecânica: o plano conta semanas pela data do jogo; quando o tempo fecha e os requisitos de atributo
estão cumpridos, o servidor grava o bit (e apaga o movimento oposto, se houver).
"""

from __future__ import annotations

import datetime as dt

# índice do bit -> (nome, requisitos {atributo: mínimo}, opostos)
CATALOG: dict[int, tuple[str, dict[str, int], tuple[int, ...]]] = {
    8: ("Chuta de longe", {"Long Shots": 12, "Technique": 10}, (24,)),
    9: ("Chuta com força", {"Long Shots": 10, "Strength": 11}, (10,)),
    10: ("Bate colocado", {"Finishing": 12, "Composure": 11}, (9,)),
    11: ("Chute com efeito", {"Technique": 13, "Long Shots": 11}, ()),
    42: ("Chuta de primeira", {"Finishing": 12, "Technique": 12}, ()),
    12: ("Dribla o goleiro", {"Dribbling": 12, "Composure": 12}, (21,)),
    21: ("Encobre o goleiro", {"Technique": 13, "Finishing": 11, "Flair": 11}, (12,)),
    3: ("Entra na área", {"Off the ball": 12, "Finishing": 10}, (31, 33)),
    13: ("Joga na linha do impedimento", {"Off the ball": 13, "Pace": 13, "Anticipation": 11}, (33,)),
    4: ("Abre pelos lados", {"Off the ball": 11, "Pace": 12}, ()),
    5: ("Chega à frente sempre", {"Stamina": 13, "Work rate": 13}, (33,)),
    18: ("Joga de costas para o gol", {"Strength": 13, "First Touch": 11}, ()),
    19: ("Vem buscar o jogo", {"Passing": 11, "Team work": 11}, ()),
    20: ("Faz tabelas", {"Passing": 12, "Off the ball": 11, "First Touch": 11}, ()),
    22: ("Dita o ritmo", {"Passing": 13, "Decision": 13, "Composure": 12}, ()),
    43: ("Lançamentos longos", {"Passing": 13, "Creativity": 12}, (6,)),
    47: ("Inverte o jogo", {"Passing": 13, "Creativity": 12}, ()),
    6: ("Joga simples", {"Passing": 11, "Decision": 11}, (7, 43)),
    44: ("Gosta da bola no pé", {"First Touch": 12, "Technique": 11}, ()),
    0: ("Conduz pela esquerda", {"Dribbling": 12, "Pace": 12, "Left foot": 13}, ()),
    1: ("Conduz pela direita", {"Dribbling": 12, "Pace": 12, "Right foot": 13}, ()),
    2: ("Conduz pelo meio", {"Dribbling": 12, "Pace": 11, "Balance": 11}, ()),
    39: ("Corta para dentro", {"Dribbling": 12, "Agility": 11}, (40,)),
    40: ("Vai à linha", {"Crossing": 12, "Pace": 12}, (39,)),
    27: ("Toca e passa no corredor", {"Pace": 14, "Acceleration": 13, "Dribbling": 11}, ()),
    35: ("Tenta jogadas de efeito", {"Flair": 13, "Technique": 12}, ()),
    46: ("Dribla em sequência", {"Dribbling": 14, "Flair": 12, "Agility": 12}, ()),
    14: ("Usa a parte de fora do pé", {"Technique": 14, "Flair": 12}, ()),
    36: ("Tenta faltas de longe", {"Set Pieces": 13, "Long Shots": 11}, ()),
    45: ("Bate falta com força", {"Set Pieces": 11, "Long Shots": 12}, ()),
    15: ("Marca em cima", {"Marking": 12, "Aggression": 10, "Work rate": 11}, ()),
    38: ("Não dá carrinho", {"Tackling": 11, "Positioning": 11, "Decision": 10}, (37,)),
}

# nomes como o jogo mostra (tela Posições > Movimentos Preferidos, conferido 02/11) para os que não
# estão no catálogo e cuja tradução do layout estava errada
GAME_NAMES = {32: "Sai jogando sob pressão", 37: "Dá carrinho", 38: "Não dá carrinho"}


def move_name(index: int, fallback: str) -> str:
    return CATALOG[index][0] if index in CATALOG else GAME_NAMES.get(index, fallback)


PT = {"Tackling": "Desarme", "Positioning": "Posicionamento", "Long Shots": "Chutes Longe", "Technique": "Técnica", "Strength": "Força", "Finishing": "Finalização",
      "Composure": "Compostura", "Dribbling": "Finta", "Flair": "Instinto", "Off the ball": "Sem Bola",
      "Pace": "Velocidade", "Anticipation": "Antecipação", "Stamina": "Resistência", "Work rate": "Índice Trabalho",
      "First Touch": "Primeiro Toque", "Passing": "Passe", "Team work": "Trabalho Equipe", "Decision": "Decisões",
      "Creativity": "Criatividade", "Left foot": "Pé esquerdo", "Right foot": "Pé direito", "Balance": "Balance",
      "Agility": "Agilidade", "Crossing": "Cruzamentos", "Acceleration": "Aceleração", "Set Pieces": "Livres",
      "Marking": "Marcação", "Aggression": "Agressividade", "Determination": "Determinação", "Bravery": "Bravura"}


def weeks_needed(attributes: dict[str, int], age: int) -> int:
    """6..20 semanas: Determinação alta e idade baixa aprendem mais rápido."""
    weeks = 14 - (attributes.get("Determination", 10) - 10) * 0.6 - max(0, 21 - age) * 0.5
    return int(max(6, min(20, round(weeks))))


def missing(attributes: dict[str, int], index: int) -> list[tuple[str, int, int]]:
    return [(PT.get(a, a), attributes.get(a, 0), need) for a, need in CATALOG[index][1].items()
            if attributes.get(a, 0) < need]


def fit(attributes: dict[str, int], index: int) -> float:
    """0..1: quanto o jogador já cumpre os requisitos (para ordenar sugestões)."""
    req = CATALOG[index][1]
    return round(sum(min(1, attributes.get(a, 0) / need) for a, need in req.items()) / len(req), 3)


def catalog_for(attributes: dict[str, int], known: list[int]) -> list[dict]:
    rows = []
    for index, (name, req, opposite) in CATALOG.items():
        if index in known:
            continue
        rows.append({"idx": index, "nome": name, "aptidao": fit(attributes, index),
                     "requisitos": [(PT.get(a, a), attributes.get(a, 0), need) for a, need in req.items()],
                     "opostos": [CATALOG[o][0] if o in CATALOG else str(o) for o in opposite if o in known]})
    return sorted(rows, key=lambda r: -r["aptidao"])


def evaluate(plan: dict, today: str, attributes: dict[str, int], age: int, known: list[int]) -> dict:
    """Situação do plano ativo de um jogador."""
    index = plan["idx"]
    start = dt.date.fromisoformat(plan["inicio"])
    weeks = (dt.date.fromisoformat(today) - start).days / 7
    need = plan.get("semanas") or weeks_needed(attributes, age)
    lacking = missing(attributes, index)
    done = index in known
    return {"idx": index, "nome": CATALOG[index][0], "inicio": plan["inicio"], "semanas": need,
            "semanas_feitas": round(max(0.0, weeks), 1), "progresso": int(min(100, max(0, weeks / need * 100))),
            "faltando": lacking, "pronto": not done and weeks >= need and not lacking, "aprendido": done}


# Sugestões do adjunto: encaixe nos requisitos (60%) + utilidade na posição-alvo (40%).
ATT, WING = {"PL", "MA C", "MA D", "MA E"}, {"MA D", "MA E", "M D", "M E", "AD", "AE"}
MID, DEF = {"MD", "M C", "MA C"}, {"DC", "DD", "DE", "MD"}
USEFUL = {
    **{i: ATT | {"M C"} for i in (8, 9, 10, 11, 42)},
    **{i: {"PL", "MA C"} for i in (12, 21, 18)},
    3: {"PL", "MA C", "MA D", "MA E"}, 13: {"PL", "MA D", "MA E"}, 4: WING | {"PL"}, 5: WING | MID,
    **{i: MID | {"MA C"} for i in (19, 20, 22, 43, 47, 6, 44)},
    **{i: WING | {"MA C", "PL"} for i in (0, 1, 2, 39, 40, 27, 35, 46, 14)},
    36: ATT | MID | WING, 45: ATT | MID | WING, 15: DEF, 38: DEF | {"M C"},
}


def suggest(attributes: dict[str, int], known: list[int], target: str, limit: int = 3) -> list[dict]:
    if target == "GR":
        return []
    rows = []
    for index, (name, req, _) in CATALOG.items():
        if index in known or target not in USEFUL.get(index, set()):
            continue
        score = 0.6 * fit(attributes, index) + 0.4
        best = sorted(req, key=lambda a: -attributes.get(a, 0))[:2]
        lacking = missing(attributes, index)
        reason = (f"já tem {', '.join(f'{PT.get(a, a)} {attributes.get(a, 0)}' for a in best)}"
                  + (f"; precisa chegar a {', '.join(f'{n} {m}' for n, _, m in lacking)}" if lacking else ""))
        rows.append({"idx": index, "nome": name, "nota": round(score, 3), "pronto": not lacking, "motivo": reason})
    return sorted(rows, key=lambda r: (-r["pronto"], -r["nota"]))[:limit]
