"""Treinador adjunto da Central externa: melhor posição pelos atributos e foco de treino.

Tudo é opinião calculada a partir dos atributos lidos do jogo (leitor.py); nada é escrito no jogo.

- Perfis de posição: pesos de 1 a 3 nos atributos que importam em cada posição (estilo FM). A nota da
  posição é a média ponderada (0..20), agora e no futuro do olheiro; nos lados, o pé daquele lado pesa.
- Posições naturais: as que o jogo já dá (valor DIRECT 15+). Sugestão de nova posição quando uma
  posição não natural tem nota perto ou acima da melhor natural.
- Foco de treino: lacuna entre o jogador e um alvo (o futuro do olheiro, no mínimo 12) nos atributos
  da melhor posição, somada por categoria de treino do FM06.
"""

from __future__ import annotations

PT = {
    "Heading": "Cabeceio", "Corner": "Cantos", "Long Shots": "Chutes Longe", "Crossing": "Cruzamentos",
    "Tackling": "Desarme", "Finishing": "Finalização", "Dribbling": "Finta", "Throwing": "Lançam. Longos",
    "Set Pieces": "Livres", "Marking": "Marcação", "Penalty": "Penáltis", "Passing": "Passe",
    "First Touch": "Primeiro Toque", "Technique": "Técnica", "Aggression": "Agressividade",
    "Anticipation": "Antecipação", "Bravery": "Bravura", "Composure": "Compostura",
    "Concentration": "Concentração", "Creativity": "Criatividade", "Decision": "Decisões",
    "Determination": "Determinação", "Influence": "Influência", "Flair": "Instinto",
    "Positioning": "Posicionamento", "Off the ball": "Sem Bola", "Team work": "Trabalho Equipe",
    "Work rate": "Índice Trabalho", "Acceleration": "Aceleração", "Agility": "Agilidade",
    "Balance": "Balance", "Natural fit.": "Cond. Fís. Natural", "Strength": "Força", "Jumping": "Impulsão",
    "Stamina": "Resistência", "Pace": "Velocidade", "Handling": "Jogo de Mãos", "Reflexes": "Reflexos",
    "One on one": "Um contra Um", "Aer ability": "Alcance Aéreo", "Cmd of area": "Comando de Área",
    "Communiction": "Comunicação", "Kicking": "Pontapé", "Rushing out": "Saídas", "Punch": "Socar",
    "Long throws": "Lançamentos",
}

# posição exibida -> (nome, atributo DIRECT do jogo, pesos)
PROFILES = {
    "GR": ("goleiro", "Goalkeeper", {"Reflexes": 3, "Handling": 3, "One on one": 2, "Aer ability": 2,
                                      "Cmd of area": 2, "Positioning": 2, "Communiction": 1, "Kicking": 1,
                                      "Agility": 2, "Concentration": 1, "Decision": 1, "Jumping": 1}),
    "DC": ("zagueiro", "Center Def.", {"Tackling": 3, "Marking": 3, "Heading": 3, "Positioning": 3, "Jumping": 2,
                                        "Strength": 2, "Anticipation": 2, "Bravery": 1, "Concentration": 1,
                                        "Decision": 1, "Pace": 1}),
    "DD": ("lateral direito", "Right Def.", {"Tackling": 2, "Marking": 2, "Positioning": 2, "Pace": 3,
                                             "Acceleration": 2, "Stamina": 2, "Crossing": 2, "Work rate": 2,
                                             "Anticipation": 1, "Team work": 1}),
    "DE": ("lateral esquerdo", "Left Def.", {"Tackling": 2, "Marking": 2, "Positioning": 2, "Pace": 3,
                                              "Acceleration": 2, "Stamina": 2, "Crossing": 2, "Work rate": 2,
                                              "Anticipation": 1, "Team work": 1}),
    "AD": ("ala direito", "Wing B.R.", {"Pace": 3, "Acceleration": 2, "Stamina": 3, "Crossing": 3, "Work rate": 2,
                                         "Dribbling": 2, "Tackling": 1, "Off the ball": 1, "Team work": 1}),
    "AE": ("ala esquerdo", "Wing B.L.", {"Pace": 3, "Acceleration": 2, "Stamina": 3, "Crossing": 3, "Work rate": 2,
                                          "Dribbling": 2, "Tackling": 1, "Off the ball": 1, "Team work": 1}),
    "MD": ("volante", "Def. C.M.", {"Tackling": 3, "Positioning": 3, "Anticipation": 2, "Marking": 2, "Passing": 2,
                                     "Work rate": 2, "Stamina": 2, "Team work": 2, "Decision": 2, "Strength": 1}),
    "M C": ("meio-campista", "Mid. Center", {"Passing": 3, "Decision": 3, "Team work": 2, "Work rate": 2,
                                              "Stamina": 2, "First Touch": 2, "Technique": 1, "Creativity": 1,
                                              "Tackling": 1, "Off the ball": 1}),
    "M D": ("meia pela direita", "Mid. Right", {"Crossing": 3, "Pace": 2, "Stamina": 2, "Dribbling": 2, "Passing": 2,
                                                "Work rate": 2, "Off the ball": 1, "Acceleration": 1, "Technique": 1}),
    "M E": ("meia pela esquerda", "Mid. Left", {"Crossing": 3, "Pace": 2, "Stamina": 2, "Dribbling": 2, "Passing": 2,
                                                "Work rate": 2, "Off the ball": 1, "Acceleration": 1, "Technique": 1}),
    "MA C": ("meia atacante", "Att. M.C.", {"Passing": 3, "Creativity": 3, "Technique": 2, "First Touch": 2,
                                             "Dribbling": 2, "Off the ball": 2, "Flair": 2, "Long Shots": 1,
                                             "Decision": 1, "Composure": 1}),
    "MA D": ("ponta direita", "Att. M.R.", {"Dribbling": 3, "Pace": 3, "Acceleration": 2, "Crossing": 2, "Technique": 2,
                                             "Flair": 1, "Off the ball": 2, "Finishing": 1, "Agility": 1}),
    "MA E": ("ponta esquerda", "Att. M.L.", {"Dribbling": 3, "Pace": 3, "Acceleration": 2, "Crossing": 2, "Technique": 2,
                                              "Flair": 1, "Off the ball": 2, "Finishing": 1, "Agility": 1}),
    "PL": ("centroavante", "Att. Center", {"Finishing": 3, "Off the ball": 3, "Composure": 2, "First Touch": 2,
                                            "Heading": 2, "Pace": 2, "Acceleration": 2, "Strength": 1, "Dribbling": 1}),
}

# categorias de treino do FM06 (tela Treino) e os atributos que cada uma puxa
TRAINING = {
    "Força": ("Strength", "Jumping"),
    "Aeróbico": ("Stamina", "Pace", "Acceleration", "Agility", "Balance", "Natural fit."),
    "Goleiro": ("Handling", "Reflexes", "One on one", "Aer ability", "Cmd of area", "Kicking", "Rushing out",
                "Punch", "Communiction"),
    "Tático": ("Decision", "Positioning", "Anticipation", "Off the ball", "Team work", "Concentration", "Work rate"),
    "Controlo Bola": ("Dribbling", "First Touch", "Technique", "Flair"),
    "Defensivo": ("Tackling", "Marking", "Heading"),
    "Ofensivo": ("Passing", "Crossing", "Creativity"),
    "Finalização": ("Finishing", "Long Shots", "Composure"),
    "Bolas Paradas": ("Corner", "Set Pieces", "Penalty", "Throwing", "Long throws"),
}


RIGHT, LEFT = {"DD", "AD", "M D", "MA D"}, {"DE", "AE", "M E", "MA E"}


def score(values: dict[str, int], weights: dict[str, int], short: str = "") -> float:
    """Média ponderada; nas posições de lado, o pé daquele lado pesa (pé fraco perde até 15%)."""
    base = sum(values.get(a, 0) * w for a, w in weights.items()) / sum(weights.values())
    foot = "Right foot" if short in RIGHT else "Left foot" if short in LEFT else None
    if foot:
        base *= 0.85 + 0.15 * min(values.get(foot, 20), 20) / 20
    return round(base, 1)


def analyse(atributos: dict[str, int], futuro: dict[str, int]) -> dict:
    keeper = atributos.get("Goalkeeper", 0) >= 15
    rows = []
    for short, (name, direct, weights) in PROFILES.items():
        if (short == "GR") != keeper:
            continue                                    # goleiro só como goleiro, e vice-versa
        rows.append({
            "pos": short, "nome": name, "nota": score(atributos, weights, short), "futuro": score(futuro, weights, short),
            "natural": atributos.get(direct, 0) >= 15, "familiaridade": atributos.get(direct, 0),
            "destaques": [(PT[a], atributos.get(a, 0)) for a in sorted(weights, key=lambda a: -atributos.get(a, 0) * weights[a])[:3]],
        })
    rows.sort(key=lambda r: (-r["futuro"], -r["nota"]))
    best = rows[0]
    natural = [r for r in rows if r["natural"]]
    best_natural = max(natural, key=lambda r: r["futuro"]) if natural else None
    if best["natural"] or (best_natural and best["futuro"] < best_natural["futuro"] + 0.5):
        target = best_natural or best
        advice = (f"O adjunto mantém ele como {target['nome']}: é a posição dele e onde mais pode render "
                  f"({', '.join(f'{n} {v}' for n, v in target['destaques'])}).")
        new_position = None
    else:
        target = best
        advice = (f"O adjunto sugere treinar ele como {best['nome']} ({best['pos']}): tem "
                  f"{', '.join(f'{n} {v}' for n, v in best['destaques'])}. No futuro renderia "
                  f"{best['futuro']} ali" + (f", contra {best_natural['futuro']} como {best_natural['nome']}." if best_natural else "."))
        new_position = best["pos"]
    weights = PROFILES[target["pos"]][2]
    gaps: dict[str, list[tuple[str, int, int, float]]] = {}
    for attr, w in weights.items():
        goal = max(12, futuro.get(attr, 0))
        gap = (goal - atributos.get(attr, 0)) * w
        if gap <= 0:
            continue
        for category, attrs in TRAINING.items():
            if attr in attrs:
                gaps.setdefault(category, []).append((PT[attr], atributos.get(attr, 0), goal, gap))
    focus = sorted(gaps.items(), key=lambda kv: -sum(g[3] for g in kv[1]))[:3]
    strongest = sorted(weights, key=lambda a: -atributos.get(a, 0) * weights[a])[:4]
    weakest = sorted(weights, key=lambda a: atributos.get(a, 0) * weights[a])[:4]
    left, right = atributos.get("Left foot", 0), atributos.get("Right foot", 0)
    preferred_foot = "ambos" if min(left, right) >= 15 else "esquerdo" if left > right else "direito"
    return {
        "posicoes": rows[:4], "mapa_posicoes": rows, "sugestao": advice,
        "nova_posicao": new_position, "alvo": target["pos"], "alvo_nome": target["nome"],
        "pe_preferido": preferred_foot,
        "pontos_fortes": [(PT[a], atributos.get(a, 0)) for a in strongest],
        "pontos_fracos": [(PT[a], atributos.get(a, 0)) for a in weakest],
        "treino": [{"categoria": c, "atributos": [(n, v, g) for n, v, g, _ in sorted(items, key=lambda i: -i[3])[:3]]}
                   for c, items in focus],
    }


def compare(young: dict, principal: list[dict]) -> dict | None:
    """O jovem contra o dono da posição-alvo dele no time principal: entre os que têm a posição como
    natural (15+), o que mais jogou (desempate: nota na posição)."""
    target = (young.get("adjunto") or {}).get("alvo")
    if target not in PROFILES:
        return None
    name, direct, weights = PROFILES[target]
    rivals = [p for p in principal if p["uid"] != young["uid"] and p["familiaridades"].get(target, 0) >= 15]
    if not rivals:
        return {"pos": target, "funcao": name, "titular": None}
    rival = max(rivals, key=lambda p: ((p.get("estatisticas") or {}).get("jogos", 0), score(p["atributos"], weights, target)))
    keys = sorted(weights, key=lambda a: -weights[a])[:8]
    rows = [{"nome": PT[a], "peso": weights[a], "jovem": young["atributos"].get(a, 0),
             "futuro": young["futuro"].get(a, young["atributos"].get(a, 0)), "titular": rival["atributos"].get(a, 0)}
            for a in keys]
    now, future, theirs = (score(young["atributos"], weights, target), score(young["futuro"], weights, target),
                           score(rival["atributos"], weights, target))
    gap = round(theirs - now, 1)
    if now >= theirs:
        verdict = f"Já rende tanto quanto o titular como {name}. Merece minutos no principal."
    elif future >= theirs:
        verdict = f"Hoje está {gap} pontos abaixo, mas a projeção passa o titular ({future} contra {theirs})."
    else:
        verdict = f"Está {gap} pontos abaixo do titular e a projeção não alcança ({future} contra {theirs})."
    return {"pos": target, "funcao": name, "nota_jovem": now, "nota_futuro": future, "nota_titular": theirs,
            "veredito": verdict, "atributos": rows,
            "titular": {k: rival.get(k) for k in ("uid", "nome", "apelido", "idade", "numero", "hab")}
            | {"estatisticas": rival.get("estatisticas") or {}}}
