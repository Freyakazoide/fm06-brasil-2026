"""Estado externo da carreira na Sala de Imprensa (docs/SALA_DE_IMPRENSA.md, §8.6).

Só arquivos em workspace/imprensa/<carreira>/: eventos.jsonl (só anexado, auditoria) e estado.json
(respostas dadas e somas: relação com cada jogador, credibilidade com cada veículo, elenco, torcida,
diretoria, resposta ao treino). Nada vai para o FM06. Os efeitos vêm da simulação da página e são
limitados a ±4 por resposta (§8.7).
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "workspace" / "imprensa"
EFFECTS = ("player", "squad", "fans", "board", "media", "training")
LIMIT = 4


def save_id(club: str, team_uid: int | None) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", club.lower()).strip("-") or "clube"
    return f"{slug}-{team_uid}" if team_uid else slug


def folder(career: str) -> Path:
    if not re.fullmatch(r"[a-z0-9-]{1,80}", career):
        raise ValueError("carreira inválida")
    return BASE / career


def empty() -> dict:
    return {"respostas": {}, "relacao": {}, "credibilidade": {}, "elenco": 0, "torcida": 0, "diretoria": 0,
            "treino": {}}


def load(career: str) -> dict:
    path = folder(career) / "estado.json"
    try:
        return {**empty(), **json.loads(path.read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        return empty()


def record(career: str, entry: dict) -> dict:
    """Grava uma resposta dada. Uma pauta (chave) só recebe uma resposta."""
    for field in ("key", "situation_id", "answer_id", "player_id", "outlet_id"):
        if entry.get(field) in (None, ""):
            raise ValueError(f"falta {field}")
    state = load(career)
    key = str(entry["key"])
    if key in state["respostas"]:
        raise ValueError("esta pauta já foi respondida")
    effects = {name: max(-LIMIT, min(LIMIT, int(entry.get("effects", {}).get(name, 0)))) for name in EFFECTS}
    player, outlet = str(entry["player_id"]), str(entry["outlet_id"])
    when = dt.datetime.now().isoformat(timespec="seconds")
    state["respostas"][key] = {"situation_id": entry["situation_id"], "answer_id": entry["answer_id"],
                               "player_id": entry["player_id"], "outlet_id": entry["outlet_id"],
                               "question": int(entry.get("question", 0)), "data_jogo": entry.get("date"),
                               "news_serial": entry.get("news_serial"), "effects": effects, "gravado": when}
    state["relacao"][player] = state["relacao"].get(player, 0) + effects["player"]
    state["treino"][player] = state["treino"].get(player, 0) + effects["training"]
    state["credibilidade"][outlet] = state["credibilidade"].get(outlet, 0) + effects["media"]
    state["elenco"] += effects["squad"]
    state["torcida"] += effects["fans"]
    state["diretoria"] += effects["board"]
    target = folder(career)
    target.mkdir(parents=True, exist_ok=True)
    with (target / "eventos.jsonl").open("a", encoding="utf-8") as log:
        log.write(json.dumps({"tipo": "resposta", "key": key, **state["respostas"][key]}, ensure_ascii=False) + "\n")
    (target / "estado.json").write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    return state
