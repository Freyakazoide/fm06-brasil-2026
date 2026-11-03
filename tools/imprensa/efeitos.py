"""Efeito da resposta no FM06 aberto (docs/SALA_DE_IMPRENSA.md, §8.7): por enquanto só a moral.

Moral do jogador: u8 em UID-184, de 1 a 20 (reverse/fmm/player_live_layout.json, CONFIRMED: diff
manual Saviola 20 -> 19; o leitor da Central lê o mesmo campo). Travas: ±4 por resposta, ±6 por
semana do jogo para o mesmo jogador, valor final entre 1 e 20, UID conferido e valor antigo relido
logo antes de gravar. Escrita pelo handle de chamada_remota (o mesmo das habilidades da Central).
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "central"), str(ROOT / "tools" / "re")]

MORALE_REL, LOW, HIGH = -184, 1, 20
PER_ANSWER, PER_WEEK = 4, 6


def week(date: str) -> tuple[int, int]:
    return dt.date.fromisoformat(date).isocalendar()[:2]


def allowed(delta: int, player_id: int, date: str, history: list[dict]) -> int:
    """O quanto ainda cabe: limite por resposta e o que já foi aplicado nesta semana do jogo."""
    delta = max(-PER_ANSWER, min(PER_ANSWER, delta))
    used = sum(h["delta"] for h in history if h["player_id"] == player_id and week(h["data"]) == week(date))
    if delta > 0:
        return max(0, min(delta, PER_WEEK - used))
    return min(0, max(delta, -PER_WEEK - used))


def preview(morale: int, delta: int) -> int:
    return max(LOW, min(HIGH, morale + delta))


def apply_morale(player_id: int, delta: int) -> dict:
    """Grava a moral nova no jogo aberto. Devolve antes/depois, ou erro sem escrever nada."""
    import chamada_remota as cr
    import leitor
    jogo = leitor.Jogo()
    target = next((r for r in jogo.table(leitor.PEOPLE)
                   if r and jogo.u32(r) == leitor.PLAYER_VT and jogo.u32(r + 0x14) == player_id), None)
    if not target:
        return {"erro": "jogador não encontrado no jogo aberto"}
    at = target + 0x14 + MORALE_REL
    before = jogo.raw(at, 1)[0]
    if not LOW <= before <= HIGH:
        return {"erro": f"moral fora da escala ({before}); nada gravado"}
    after = preview(before, delta)
    if after == before:
        return {"antes": before, "depois": after}
    _, handle = cr.game()
    if jogo.raw(at, 1)[0] != before or jogo.u32(target + 0x14) != player_id:
        return {"erro": "o jogo mudou o valor agora; nada gravado"}
    cr.poke(handle, at, bytes([after]))
    if jogo.raw(at, 1)[0] != after:
        return {"erro": "a escrita não pegou"}
    return {"antes": before, "depois": after}
