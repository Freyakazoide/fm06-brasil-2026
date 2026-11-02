"""Personalidade dos jovens na Central externa (só leitura).

Os 8 traços ocultos do FM06 ficam no objeto PData do jogador ([R+200], conferido em 200 jogadores),
logo depois do UID (live_player.PERSONALITY_REL), de 1 a 20. A Central não mostra os números crus como
verdade absoluta: é a leitura da comissão, com rótulos e alertas. No FM, Profissionalismo, Ambição e
Determinação (atributo) pesam no quanto o jovem se aproxima do potencial.
"""

from __future__ import annotations

PT = {"Adaptability": "Adaptabilidade", "Ambition": "Ambição", "Loyalty": "Lealdade", "Pressure": "Pressão",
      "Professional": "Profissionalismo", "Sportsmanship": "Desportivismo", "Temperament": "Temperamento",
      "Controversy": "Polêmica"}


def profile(traits: dict[str, int], determination: int) -> str:
    pro, amb = traits.get("Professional", 10), traits.get("Ambition", 10)
    if pro >= 18 and determination >= 15:
        return "Modelo de profissional"
    if pro >= 15 and amb >= 15:
        return "Profissional ambicioso"
    if pro >= 15:
        return "Profissional"
    if amb >= 16:
        return "Ambicioso"
    if traits.get("Pressure", 10) >= 16:
        return "Frio sob pressão"
    if pro <= 6:
        return "Displicente"
    if traits.get("Temperament", 10) <= 5:
        return "Temperamental"
    if traits.get("Controversy", 10) >= 15:
        return "Polêmico"
    return "Equilibrado"


def growth(traits: dict[str, int], determination: int) -> dict:
    """0..100: quanto a personalidade ajuda a chegar ao potencial."""
    score = (traits.get("Professional", 10) * 0.45 + traits.get("Ambition", 10) * 0.25 + determination * 0.30) / 20 * 100
    level = "alta" if score >= 70 else "média" if score >= 50 else "baixa"
    return {"nota": round(score), "nivel": level}


def alerts(traits: dict[str, int], determination: int) -> list[dict]:
    out = []
    add = lambda kind, text: out.append({"tipo": kind, "texto": text})
    pro, amb = traits.get("Professional", 10), traits.get("Ambition", 10)
    if pro >= 15:
        add("bom", "Muito profissional: cuida do corpo e treina sério. Tende a evoluir mais rápido.")
    elif pro <= 8:
        add("risco", "Pouco profissional: risco de estagnar. Um mentor experiente no elenco ajuda.")
    if amb >= 15:
        add("bom", "Ambicioso: quer jogar em alto nível. Pode pedir para sair se não tiver espaço.")
    elif amb <= 6:
        add("risco", "Pouca ambição: pode se acomodar.")
    if traits.get("Pressure", 10) <= 8:
        add("atencao", "Sente a pressão: evite jogá-lo de cara em decisões.")
    if traits.get("Temperament", 10) <= 6:
        add("atencao", "Temperamento difícil: tende a levar cartões e brigar.")
    if traits.get("Controversy", 10) >= 15:
        add("atencao", "Polêmico: pode criar problema na imprensa e no vestiário.")
    if traits.get("Adaptability", 10) >= 15:
        add("bom", "Adapta-se fácil: bom candidato a empréstimo, até fora do país.")
    elif traits.get("Adaptability", 10) <= 6:
        add("atencao", "Adapta-se mal: empréstimo para longe pode atrapalhar.")
    if traits.get("Loyalty", 10) >= 16:
        add("bom", "Leal ao clube: renovação tende a ser tranquila.")
    if determination <= 8:
        add("risco", "Determinação baixa: desiste fácil quando as coisas apertam.")
    return out


def analyse(traits: dict[str, int], attributes: dict[str, int]) -> dict:
    determination = attributes.get("Determination", 10)
    return {"tracos": {PT[k]: v for k, v in traits.items()}, "perfil": profile(traits, determination),
            "evolucao": growth(traits, determination), "alertas": alerts(traits, determination)}
