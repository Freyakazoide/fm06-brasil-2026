"""Dados demonstrativos para desenvolver a interface com o FM06 fechado."""

from __future__ import annotations

import datetime as dt

import adjunto
import analitica
import personalidade
from leitor import POSITIONS


def _player(uid: int, name: str, age: int, team: str, position: str, hab: int, pot: int,
            moral: int, highlights: dict[str, int]) -> dict:
    values = {name: 9 for name in adjunto.PT}
    values.update({direct: 1 for direct in POSITIONS.values()})
    values.update({"Left foot": 8, "Right foot": 18, POSITIONS[position]: 18, **highlights})
    future = {key: min(20, value + (3 if value < 15 else 2)) for key, value in values.items()}
    assistant = adjunto.analyse(values, future)
    analysis = analitica.analyse_player(age=age, team=team, hab=hab, pot=pot, moral=moral,
                                        adjunto=assistant, ability_judge=14, potential_judge=17)
    return {
        "uid": uid, "nome": name, "apelido": name.split()[-1], "idade": age,
        "nascimento": f"{2026-age}-03-12", "time": team, "ca": 0, "pa": 0,
        "hab": hab, "pot": pot, "altura": 178, "peso": 72, "moral": moral,
        "condicao_raw": 4000, "ritmo_raw": 7080, "cansaco_raw": 0,
        "valor_pedido_raw": 1250000, "numero": uid * 7 % 98 + 1, "salario_raw": 40, "salario_mes": 790,
        "contrato_inicio": "2025-06-20", "contrato_fim": "2027-12-31",
        "estatisticas": {"jogos": uid * 3, "banco": 2, "gols": uid, "assistencias": 1, "melhor_em_campo": 1,
                         "amarelos": 1, "vermelhos": 0, "nota": 6.4 + uid / 10, "passes_pct": 74.5,
                         "desarmes_jogo": 1.6, "chutes_alvo_pct": 48.0, "forma": [7, 6, 6, 7, 6],
                         "nao_oficiais": {"jogos": 12 + uid, "banco": 4, "gols": uid % 4, "assistencias": 2, "melhor_em_campo": 1,
                                          "vermelhos": 0, "amarelos": 1, "minutos": 1310, "nota": 6.4 + uid / 20, "passes_pct": 68.2},
                         "por_competicao": {"Liga": {"jogos": uid * 2, "banco": 1, "gols": uid // 2, "assistencias": 1, "minutos": 900, "nota": 6.6},
                                            "Copa": {"jogos": uid, "banco": 1, "gols": 1, "assistencias": 0, "minutos": 410, "nota": 6.9}}}, "reputacao": {"local": 1200, "atual": 900, "mundial": 100},
        "internacional": {"jogos": 0, "gols": 0, "sub21_jogos": 2, "sub21_gols": 0},
        "pe_preferido": assistant["pe_preferido"], "posicoes": [position],
        "familiaridades": {short: values[direct] for short, direct in POSITIONS.items()},
        "movimentos": ["Vem para dentro", "Tenta fazer passes longos"], "movimentos_idx": [39, 43],
        "atributos": values, "futuro": future, "nivel": "jogador de Série A",
        "adjunto": assistant, "analise": analysis,
        "personalidade": personalidade.analyse({"Adaptability": 9 + uid % 7, "Ambition": 8 + uid % 9, "Loyalty": 12,
                                                "Pressure": 7 + uid % 10, "Professional": 6 + uid * 3 % 14, "Sportsmanship": 14,
                                                "Temperament": 5 + uid % 12, "Controversy": 4 + uid % 13}, values),
        "comparacao": adjunto.compare({"uid": uid, "adjunto": assistant, "atributos": values, "futuro": future},
                                      [{"uid": 99, "nome": "Breno Lima", "apelido": "Breno", "idade": 27, "numero": 5, "hab": 5,
                                        "atributos": {k: v + 2 for k, v in values.items()},
                                        "familiaridades": {short: 18 for short in POSITIONS},
                                        "estatisticas": {"jogos": 15, "gols": 3, "assistencias": 2, "nota": 6.67, "passes_pct": 76.8}}]),
    }


def payload() -> dict:
    players = [
        _player(1, "Afonso Guedes", 16, "Sub-20", "M C", 4, 8, 16,
                {"Passing": 15, "Creativity": 15, "Decision": 13, "Technique": 14}),
        _player(2, "Rafael Venâncio", 17, "Sub-20", "GR", 5, 7, 12,
                {"Goalkeeper": 18, "Handling": 15, "Reflexes": 16, "One on one": 14}),
        _player(3, "Diego Rodrigues", 18, "B", "DC", 6, 8, 9,
                {"Tackling": 15, "Marking": 14, "Heading": 16, "Strength": 15}),
        _player(4, "Toninho Silva", 18, "Principal", "MA C", 7, 8, 17,
                {"Passing": 16, "Creativity": 16, "Technique": 15, "First Touch": 14}),
    ]
    history = {}
    for player in players:
        history[str(player["uid"])] = [
            {"data": "2026-05-04", "hab": max(0, player["hab"] - 1), "pot": player["pot"],
             "tec": 9.8, "men": 10.4, "fis": 10.8},
            {"data": "2026-08-04", "hab": player["hab"], "pot": player["pot"],
             "tec": 10.5, "men": 11.0, "fis": 11.2},
        ]
    return {"schema_version": 2, "info": {"data": dt.date(2026, 8, 4).isoformat(), "time_uid": 301306,
            "avaliador_hab": 14, "avaliador_pot": 17}, "jovens": players, "historico": history}
