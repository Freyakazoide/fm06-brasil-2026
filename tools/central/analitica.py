"""Indicadores explicáveis da Central de Desenvolvimento.

Os cálculos usam apenas a opinião da comissão e os atributos já lidos. Eles não são
notas nativas do FM06 nem revelam CA/PA: servem para ordenar trabalho e explicar decisões.
"""

from __future__ import annotations


def confidence(judge: int) -> dict[str, int | str]:
    """Faixa simples para a qualidade do avaliador (atributo do FM em 1..20)."""
    if judge >= 16:
        label = "Alta"
    elif judge >= 12:
        label = "Média"
    else:
        label = "Baixa"
    return {"nivel": label, "avaliador": judge}


def _best_role(adjunto: dict) -> dict:
    rows = adjunto.get("mapa_posicoes") or adjunto.get("posicoes") or []
    target = adjunto.get("alvo")
    return next((row for row in rows if row.get("pos") == target), rows[0] if rows else {})


def readiness(hab: int, moral: int, adjunto: dict) -> int:
    """Indicador 0..100: opinião atual, encaixe na posição-alvo e moral."""
    role = _best_role(adjunto)
    role_score = float(role.get("nota", 0)) / 20 * 100
    morale_score = max(0, min(20, moral)) / 20 * 100
    return round(0.60 * hab * 10 + 0.30 * role_score + 0.10 * morale_score)


def phase(age: int, team: str, hab: int, pot: int, ready: int) -> str:
    if team == "Principal" or ready >= 72:
        return "Pronto para minutos"
    if pot >= 8 and age >= 18:
        return "Prioridade"
    if hab >= 5 or age >= 17:
        return "Transição"
    return "Formação"


def attention(age: int, hab: int, pot: int, ready: int, adjunto: dict) -> int:
    """Urgência 0..100; alto potencial ainda distante e mudança de posição pesam mais."""
    potential_gap = max(0, pot - hab) * 10
    age_pressure = max(0, age - 16) * 7
    position_change = 15 if adjunto.get("nova_posicao") else 0
    ready_bonus = 10 if ready >= 65 else 0
    return min(100, round(0.55 * potential_gap + age_pressure + position_change + ready_bonus))


def analyse_player(*, age: int, team: str, hab: int, pot: int, moral: int,
                   adjunto: dict, ability_judge: int, potential_judge: int) -> dict:
    ready = readiness(hab, moral, adjunto)
    current_phase = phase(age, team, hab, pot, ready)
    role = _best_role(adjunto)
    alerts = []
    if adjunto.get("nova_posicao"):
        alerts.append({"tipo": "posicao", "nivel": "atenção",
                       "texto": f"Avaliar treino de nova posição: {adjunto['nova_posicao']}."})
    if pot - hab >= 3:
        alerts.append({"tipo": "potencial", "nivel": "oportunidade",
                       "texto": "Há uma distância grande entre capacidade atual e potencial percebido."})
    if age >= 18 and team != "Principal" and ready >= 60:
        alerts.append({"tipo": "caminho", "nivel": "decisão",
                       "texto": "Está perto de precisar de minutos em nível mais alto."})
    if moral <= 8:
        alerts.append({"tipo": "moral", "nivel": "risco",
                       "texto": "Moral baixa pode atrapalhar o plano de desenvolvimento."})
    return {
        "prontidao": ready,
        "fase": current_phase,
        "prioridade": attention(age, hab, pot, ready, adjunto),
        "funcao_alvo": role.get("nome", adjunto.get("alvo", "—")),
        "nota_funcao": role.get("nota"),
        "nota_funcao_futura": role.get("futuro"),
        "confianca_habilidade": confidence(ability_judge),
        "confianca_potencial": confidence(potential_judge),
        "alertas": alerts,
        "metodologia": "Indicador interno: 60% habilidade da comissão, 30% encaixe e 10% moral.",
    }
