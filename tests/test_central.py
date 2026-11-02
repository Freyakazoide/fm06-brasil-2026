from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "central"))

import adjunto  # noqa: E402
import analitica  # noqa: E402


def player_attributes() -> dict[str, int]:
    values = {name: 10 for _, direct, weights in adjunto.PROFILES.values() for name in (*weights, direct)}
    values.update({"Att. M.L.": 16, "Left foot": 18, "Right foot": 8, "Dribbling": 16,
                   "Pace": 16, "Acceleration": 15, "Crossing": 13, "Off the ball": 14})
    return values


def test_adjunto_exposes_complete_position_map_and_foot() -> None:
    values = player_attributes()
    future = {name: min(20, value + 2) for name, value in values.items()}
    result = adjunto.analyse(values, future)
    assert result["pe_preferido"] == "esquerdo"
    assert len(result["mapa_posicoes"]) == len(adjunto.PROFILES) - 1  # todos os perfis de linha
    assert result["pontos_fortes"]
    assert result["alvo"]


def test_analytics_is_bounded_and_explainable() -> None:
    result = analitica.analyse_player(
        age=18, team="Sub-20", hab=5, pot=9, moral=14,
        adjunto={"alvo": "MA E", "nova_posicao": "MA E", "mapa_posicoes": [
            {"pos": "MA E", "nome": "ponta esquerda", "nota": 14.0, "futuro": 17.0}
        ]}, ability_judge=14, potential_judge=17)
    assert 0 <= result["prontidao"] <= 100
    assert 0 <= result["prioridade"] <= 100
    assert result["fase"] == "Prioridade"
    assert result["confianca_habilidade"]["nivel"] == "Média"
    assert result["confianca_potencial"]["nivel"] == "Alta"
    assert result["alertas"]
