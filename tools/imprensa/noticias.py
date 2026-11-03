"""Caixa de entrada do FM06 aberto (só leitura) e a tradução de cada notícia em pauta da Sala.

Mapeado em 03/11 (docs/SALA_DE_IMPRENSA.md, §8.1): a caixa do humano é o NEWS_ITEM_ARRAY (vtable
0x010F6DD4) em [humano - 0x1E0], +4 dados, +8 quantidade. Cada notícia: vtable da classe (RTTI
..._NEWS, mapa em noticias_classes.json), +0x14 data (u16 dia, u16 ano do motor), +0x1C número de
série, byte +0x22 com o bit 0 = lida (conferido: abrir "Jhonnathan acusado de displicência" mudou só
esse byte, 0x10 -> 0x11). A pessoa fica num campo próprio de cada classe; aqui se procura o primeiro
ponteiro para jogador nos 0x80 bytes da notícia.
"""

from __future__ import annotations

import datetime as dt
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools" / "central"))

import leitor  # noqa: E402

ARRAY_VT, ARRAY_REL = 0x010F6DD4, -0x1E0
DATE, SERIAL, STATUS, READ_BIT = 0x14, 0x1C, 0x22, 0x01
UNREAD = -4                                                         # u32 antes da caixa: não lidas
CLASSES = {int(k, 16): v for k, v in json.loads((HERE / "noticias_classes.json").read_text(encoding="utf-8")).items()}

# classe da notícia -> situação do banco editorial (só as que têm jogador ou assunto claro)
SITUATION = {
    "MEDIA_PLAYER_FORM_NEWS": "poor_streak", "MOM_SUMMARY_NEWS": "match_star", "MOM_FORM_NEWS": "match_star",
    "RED_CARD_BAN_NEWS": "red_card", "ACCUMULATIVE_BAN_NEWS": "red_card",
    "INJURY_INJURED_NEWS": "new_injury", "PHYSIO_REPORT_NEWS_ITEM": "new_injury", "MEDIA_INJURY_NEWS": "new_injury",
    "BASIC_INJURY_NEWS": "new_injury", "QUIRKY_PLAYER_INJURY_NEWS": "new_injury",
    "INJURY_FULL_TRAINING_NEWS": "return_injury", "INJURY_LIGHT_TRAINING_NEWS": "rehab_training",
    "MEDIA_INJURY_CRISIS_NEWS": "fatigue",
    "CONTRACT_EXPIRES_SOON_NEWS": "renewal", "BASIC_CONTRACT_EXPIRING_NEWS": "renewal",
    "LOAN_CONTRACT_EXPIRES_SOON_NEWS": "loan",
    "MEDIA_TRANSFER_SPECULATION_NEWS": "transfer_interest", "TRANSFER_OFFER_NEWS": "transfer_interest",
    "TRANSFER_OFFER_REJECTED_NEWS": "bid_rejected", "BASIC_PLAYER_REQUESTS_LISTING_NEWS": "wants_leave",
    "MEDIA_PLAYER_MORALE_NEWS": "mental_pressure", "BASIC_MORALE_NEWS": "mental_pressure",
    "PLAYER_DISPUTE_NEWS": "player_conflict", "PLAYER_MISSED_TRAINING_NEWS_ITEM": "late_training",
    "PLAYER_AWOL_NEWS_ITEM": "unauthorized_absence", "MEDIA_PENALTY_MISS_NEWS": "missed_penalty",
    "PLAYER_FIRST_CAP_NEWS": "record", "PLAYER_SCORES_FIRST_INTERNATIONAL_GOAL_NEWS": "record",
    "MANAGER_VOTE_OF_CONFIDENCE_NEWS": "manager_pressure", "BASIC_MANAGER_UNDER_PRESSURE_NEWS": "manager_pressure",
    "MANAGER_ULTIMATUM_NEWS": "manager_pressure", "SUPPORTER_PROTEST_NEWS": "fan_protest",
}
LABEL = {
    "MEDIA_PLAYER_FORM_NEWS": "imprensa comenta a forma", "MOM_SUMMARY_NEWS": "melhor em campo",
    "MOM_FORM_NEWS": "melhor em campo seguidas vezes", "RED_CARD_BAN_NEWS": "suspensão",
    "ACCUMULATIVE_BAN_NEWS": "suspensão por cartões", "INJURY_INJURED_NEWS": "lesão",
    "PHYSIO_REPORT_NEWS_ITEM": "relatório do fisioterapeuta", "MEDIA_INJURY_NEWS": "imprensa comenta a lesão",
    "BASIC_INJURY_NEWS": "lesão", "QUIRKY_PLAYER_INJURY_NEWS": "lesão curiosa",
    "INJURY_FULL_TRAINING_NEWS": "liberado para treinar", "INJURY_LIGHT_TRAINING_NEWS": "treino leve após lesão",
    "MEDIA_INJURY_CRISIS_NEWS": "crise de lesões", "CONTRACT_EXPIRES_SOON_NEWS": "contrato perto do fim",
    "BASIC_CONTRACT_EXPIRING_NEWS": "contrato perto do fim", "LOAN_CONTRACT_EXPIRES_SOON_NEWS": "empréstimo perto do fim",
    "MEDIA_TRANSFER_SPECULATION_NEWS": "especulação de transferência", "TRANSFER_OFFER_NEWS": "proposta de transferência",
    "TRANSFER_OFFER_REJECTED_NEWS": "proposta recusada", "BASIC_PLAYER_REQUESTS_LISTING_NEWS": "pede para ser negociado",
    "MEDIA_PLAYER_MORALE_NEWS": "imprensa comenta a moral", "BASIC_MORALE_NEWS": "moral do jogador",
    "PLAYER_DISPUTE_NEWS": "desentendimento", "PLAYER_MISSED_TRAINING_NEWS_ITEM": "faltou ao treino",
    "PLAYER_AWOL_NEWS_ITEM": "sumiu do clube", "MEDIA_PENALTY_MISS_NEWS": "pênalti perdido",
    "PLAYER_FIRST_CAP_NEWS": "primeira convocação", "PLAYER_SCORES_FIRST_INTERNATIONAL_GOAL_NEWS": "primeiro gol pela seleção",
    "MANAGER_VOTE_OF_CONFIDENCE_NEWS": "voto de confiança da diretoria", "BASIC_MANAGER_UNDER_PRESSURE_NEWS": "técnico pressionado",
    "MANAGER_ULTIMATUM_NEWS": "ultimato ao técnico", "SUPPORTER_PROTEST_NEWS": "protesto da torcida",
}


def box(jogo: leitor.Jogo) -> tuple[int, int, int, int]:
    """Endereço da caixa (NEWS_ITEM_ARRAY), dados, quantidade e capacidade."""
    human = next(p for p in jogo.table(leitor.PEOPLE) if p and jogo.u32(p) == leitor.HUMAN_VT)
    array = human + ARRAY_REL
    vt, data, count, capacity = struct.unpack("<4I", jogo.raw(array, 16))
    if vt != ARRAY_VT or not count <= capacity <= 10000:
        raise RuntimeError("caixa de entrada não encontrada (NEWS_ITEM_ARRAY)")
    return array, data, count, capacity


def inbox(jogo: leitor.Jogo) -> list[dict]:
    array, data, count, _ = box(jogo)
    human = array - ARRAY_REL
    out = []
    for p in struct.unpack(f"<{count}I", jogo.raw(data, 4 * count)) if count else ():
        body = jogo.raw(p, 0x80)
        words = struct.unpack("<32I", body)
        day, year = struct.unpack_from("<HH", body, DATE)
        player = 0
        for w in words[1:]:                                        # 1º ponteiro para jogador
            if 0x01000000 < w < 0x7FFF0000 and w != human:
                try:
                    if jogo.u32(w) == leitor.PLAYER_VT:
                        player = jogo.u32(w + 0x14)
                        break
                except OSError:
                    continue
        kind = CLASSES.get(words[0], f"0x{words[0]:08X}")
        date = (dt.date(year + leitor.YEAR_SHIFT, 1, 1) + dt.timedelta(days=day)).isoformat() if 1950 <= year <= 2100 else None
        out.append({"serie": struct.unpack_from("<I", body, SERIAL)[0], "classe": kind, "data": date,
                    "lida": bool(body[STATUS] & READ_BIT), "jogador": player})
    return out


def exclusive(news: dict, squad: set[int], extra: frozenset[str] = frozenset()) -> bool:
    """Modo exclusivo: notícia da imprensa (MEDIA_*) com pauta no banco e jogador do elenco. `extra`
    acrescenta classes (teste: MOM_SUMMARY_NEWS chega a cada jogo)."""
    kind = news["classe"]
    return (kind.startswith("MEDIA_") or kind in extra) and kind in SITUATION and news["jogador"] in squad


def remove(jogo: leitor.Jogo, serial: int) -> dict:
    """Tira a notícia da caixa do jogo aberto (só a lista; o objeto fica na memória) e acerta o contador
    de não lidas. Conferido em 03/11 com tools/re/caixa_remover.py: some da caixa e continua fora
    depois de salvar e recarregar. Devolve o ponteiro, a posição e se estava lida."""
    sys.path.insert(0, str(HERE.parents[1] / "tools" / "re"))
    import chamada_remota as cr
    array, data, count, _ = box(jogo)
    items = list(struct.unpack(f"<{count}I", jogo.raw(data, 4 * count))) if count else []
    index = next((i for i, p in enumerate(items) if jogo.u32(p + SERIAL) == serial), None)
    if index is None:
        raise LookupError(f"notícia {serial} não está na caixa")
    item = items[index]
    read = bool(jogo.raw(item + STATUS, 1)[0] & READ_BIT)
    _, handle = cr.game()
    cr.poke(handle, array + 8, struct.pack("<I", count - 1))           # quantidade primeiro: sem duplicata
    cr.poke(handle, data, struct.pack(f"<{count}I", *(items[:index] + items[index + 1:]), 0))
    if not read:
        cr.poke(handle, array + UNREAD, struct.pack("<I", max(0, jogo.u32(array + UNREAD) - 1)))
    return {"ponteiro": item, "posicao": index, "lida_no_jogo": read, "caixa": array}


def situation_for(news: dict, player: dict | None) -> str | None:
    """Situação do banco para a notícia; a forma do jogador decide entre boa e má fase."""
    sid = SITUATION.get(news["classe"])
    if sid == "poor_streak" and player and player.get("form") and player["form"][-1] >= 7:   # último jogo
        return "match_star"
    return sid


def label(kind: str) -> str:
    return LABEL.get(kind, kind.removesuffix("_NEWS").removesuffix("_ITEM").replace("_", " ").lower())
