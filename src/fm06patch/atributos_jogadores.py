"""Atributos, posições, personalidade, CA/PA e dados pessoais dos jogadores direto no people_db.dat.

Engenharia reversa do fm.exe 6.0.2 em docs/reversing/rea-atributos.md. Todo registro do
people_db termina em (u32 índice, u32 UID): os dados vêm antes.

    T2 (PData)   [u8 0][8 bytes personalidade][índice][UID]                 17 bytes
    T3 (Playing) [u8 0][79 bytes 1-20][u8][índice][UID]                     89 bytes
                 0-24 posições, 25-78 atributos (storage_index de
                 reverse/fmm/playing_attributes_layout.json); 0 = o jogo sorteia
    A  (pessoa)  [u32 índice][u8 tipo 2][u16 rep. casa][u16 rep. atual][u16 rep. mundo]
                 [u16 CA][u16 PA] ... +38 u16 peso, +40 u16 altura ... nomes, u16 dia do ano,
                 u16 ano, 00, u32 nação ... [índice][UID]

No New Game o jogo converte os 79 bytes (0x008E69C0): relativos (25-48 menos 33; 77; 78)
cru = trunc((10*f - CA)/2), absolutos cru = 5*f; e soma um delta igual nos atributos que
pesam no CA (0x008CDE50, pesos por posição em reverse/fmm/pesos_posicoes.json) até a média
ponderada ficar em 0,05*CA + 6. O CA e o PA vêm do arquivo. Depois, toda vez que esse ajuste
roda de novo (abrir a ficha), o jogo tira o bônus do treino do clube, ajusta e devolve o
bônus: o saldo é de +1 a +3 internos em todos os atributos com peso (TREINO_ESPERADO).

Por isso o CA gravado não é o da planilha: é o CA par mais perto dele com o qual o ajuste do
New Game desce os atributos ALVO_AJUSTE pontos internos; depois do treino eles ficam no meio
da faixa de cada valor e a ficha mostra a planilha (com folga de 1 ponto para cada lado).
"""

from __future__ import annotations

import datetime as dt
import json
import re
import struct
from dataclasses import dataclass, field
from pathlib import Path

from fm06patch import comissao
from fm06patch.live_player import PERSONALITY, _norm, encode_date, load_attributes, shift_years

ROOT = Path(__file__).resolve().parents[2]
LAYOUT = ROOT / "reverse" / "fmm" / "playing_attributes_layout.json"
WEIGHTS = ROOT / "reverse" / "fmm" / "pesos_posicoes.json"

T2_SIZE, T3_SIZE = 17, 89
PLAYER = 2                          # tipo do registro A de jogador
CA_AT, PA_AT, REP_AT = 7, 9, 1      # a partir do byte de tipo
WEIGHT_AT, HEIGHT_AT = 38, 40
REP_SCALE = 50                      # reputação no arquivo = memória / 50 (0x00A41C40)
POSITIONS = set(range(25))
RELATIVE = (set(range(25, 49)) - {33}) | {77, 78}
ALVO_AJUSTE = -3                    # pontos internos que o ajuste do New Game deve descer
TREINO_ESPERADO = 2                 # saldo típico do treino (1 a 3 nos testes de 25/10)
CA_FAIXA = 40                       # procura o CA até 40 pontos da planilha

# fim da parte comum do registro A: u16 ano, 00 00 00, u32 índice, u32 UID, u32 próximo índice, u8 tipo
_END = re.compile(rb"[\x6c-\xe0]\x07\x00\x00\x00(....)(....)(....)([\x00-\x0f])", re.S)


# ------------------------------------------------------------------
# Tabelas
# ------------------------------------------------------------------

@dataclass(frozen=True)
class Tables:
    t2: int                         # início do 1º registro (byte de tipo)
    t3: int
    a_end: int                      # o u32 com o total da T2 (fim da tabela A)
    n2: int
    n3: int


def _fixed_table(people: bytes, count: int, size: int, lo: int) -> int:
    """Início da tabela de registros fixos: u32 total seguido de registros com índice 0, 1, 2..."""
    needle = struct.pack("<I", count)
    at = people.find(needle, lo)
    while at >= 0:
        start = at + 4
        if all(struct.unpack_from("<I", people, start + size * i + size - 8)[0] == i for i in (0, 1, 2, count - 1)):
            return start
        at = people.find(needle, at + 1)
    raise ValueError(f"tabela de {count} registros de {size} bytes não achada")


def tables(people: bytes) -> Tables:
    _, n2, n3 = struct.unpack_from("<3I", people, 9)
    t2 = _fixed_table(people, n2, T2_SIZE, 0x1D)
    t3 = _fixed_table(people, n3, T3_SIZE, t2 + T2_SIZE * n2)
    return Tables(t2, t3, t2 - 4, n2, n3)


def index_fixed(people: bytes, start: int, count: int, size: int) -> dict[int, int]:
    """UID -> início do registro (byte de tipo)."""
    return {struct.unpack_from("<I", people, start + size * i + size - 4)[0]: start + size * i for i in range(count)}


def person_records(people: bytes, a_end: int) -> dict[int, tuple[int, int]]:
    """UID -> (byte de tipo, fim do registro = depois do UID) na tabela A."""
    out = {}
    start = 0x1D
    for match in _END.finditer(people, 0x1D, a_end):
        index, uid = struct.unpack("<II", match.group(1) + match.group(2))
        if not (index < 2_000_000 and 0 < uid < 100_000_000):
            continue
        end = match.start() + 13
        out[uid] = (start, end)
        start = end + 4             # pula o u32 do próximo índice
    return out


# ------------------------------------------------------------------
# Atributos: os 79 bytes e o modelo do jogo
# ------------------------------------------------------------------

def storage_index() -> dict[int, int]:
    """fmm_index -> posição nos 79 bytes."""
    fields = json.loads(LAYOUT.read_text(encoding="utf-8"))["fields"]
    return {item["fmm_index"]: item["storage_index"] for item in fields}


def t3_values(spec: dict, old: bytes) -> bytes:
    """Os 79 bytes do jogador: os do arquivo com as posições e os atributos do spec por cima."""
    attributes, storage = load_attributes(), storage_index()
    out = bytearray(old)
    for group in ("positions", "attributes"):
        for name, value in spec.get(group, {}).items():
            key = _norm(name)
            if key not in attributes:
                raise KeyError(f"{spec.get('name')}: atributo desconhecido {name!r}")
            if not 1 <= int(value) <= 20:
                raise ValueError(f"{spec.get('name')}: {name} = {value} fora de 1..20")
            out[storage[attributes[key].fmm_index]] = int(value)
    return bytes(out)


@dataclass(frozen=True)
class Weights:
    rows: list[list[int]]           # 15 posições x 79 atributos
    position_map: list[int]         # posição -> índice do byte de posição

    @classmethod
    def load(cls, path: Path = WEIGHTS) -> "Weights":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(data["pesos"], data["mapa_posicoes"])


def convert(values: bytes | list[int], ca: int) -> list[int]:
    """0x008E69C0 sem os sorteios (f = 20 em atributo-chave, f = 1 fora da posição)."""
    raw = []
    for i, f in enumerate(values):
        if i in POSITIONS:
            raw.append(f)
        elif i in RELATIVE:
            raw.append(int(max(-250, min(250, 10 * f - ca)) / 2))
        else:
            raw.append((5 * f + 128) % 256 - 128)
    return raw


def weights_for(raw: list[int], weights: Weights) -> list[float]:
    """0x00A9A390: peso de cada atributo pelas posições com nota >= 10."""
    w, total = [0.0] * 79, 0
    for p, row in enumerate(weights.rows):
        rating = raw[weights.position_map[p]]
        if rating < 10:
            continue
        total += rating - 10
        for i in range(25, 79):
            x = float(row[i])
            if x == 0.0:            # pé mais fraco vale 5
                if i == 49 and not (raw[49] == 100 and raw[50] < 100):
                    x = 5.0
                elif i == 50 and raw[50] != 100:
                    x = 5.0
                else:
                    continue
            w[i] += (rating - 10) * x * 0.1
    if total > 10:
        w = [x / (total * 0.1) for x in w]
    return [x * x if x > 1.0 else x for x in w]


def fit(raw: list[int], w: list[float], ca: int) -> list[int]:
    """0x008CDE50 (parâmetro 1): delta igual nos atributos com peso até a média ponderada
    (escala 0-20) ficar em 0,05*CA + 6; repete enquanto |delta| > 2, no máximo 10 vezes."""
    raw, target = list(raw), ca * 0.05 + 6.0
    if not any(w):
        return raw
    for _ in range(10):
        total = weighted = 0.0
        for i in range(79):
            if w[i]:
                v = (2 * raw[i] + ca) * 0.1 if i in RELATIVE else raw[i] * 0.2
                total += w[i]
                weighted += min(20.0, max(0.0, v)) * w[i]
        x = (target - weighted / total) * 5
        delta = int(x - 0.5) if x < 0 else int(x + 0.5)
        if delta == 0:
            break
        for i in range(79):
            if w[i]:
                low, high = (-125, 125) if i in RELATIVE else (1, 100)
                raw[i] = max(low, min(high, raw[i] + delta))
        if abs(delta) <= 2:
            break
    return raw


def shown(i: int, raw: int, ca: int) -> int:
    """O número da ficha (0x00A3D720 na escala 1-100 e 0x00A3CB50)."""
    if i in POSITIONS:
        return raw
    v = min(100, int(5 * max(1.0, (2 * raw + ca) * 0.1 + 0.5))) if i in RELATIVE else raw
    return max(1, min(20, int((v + 2) * 0.2)))


def game_shift(values: bytes | list[int], ca: int, weights: Weights, w: list[float] | None = None) -> int | None:
    """Quanto o ajuste do New Game move os atributos com peso (None se não há peso). Os pesos
    dependem só das posições e dos pés, não do CA: ``w`` evita recalcular."""
    raw = convert(values, ca)
    w = w if w is not None else weights_for(raw, weights)
    moved = fit(raw, w, ca)
    diffs = sorted(moved[i] - raw[i] for i in range(25, 79) if w[i])
    return diffs[len(diffs) // 2] if diffs else None


def expected_sheet(values: bytes | list[int], ca: int, weights: Weights, training: int = TREINO_ESPERADO) -> list[int]:
    """A ficha prevista: conversão, ajuste do New Game e o saldo do treino nos atributos com peso."""
    raw = convert(values, ca)
    w = weights_for(raw, weights)
    final = fit(raw, w, ca)
    final = [v + (training if w[i] else 0) if i >= 25 else v for i, v in enumerate(final)]
    return [shown(i, v, ca) for i, v in enumerate(final)]


def choose_ca(values: bytes | list[int], ca_sheet: int, weights: Weights) -> tuple[int, int | None]:
    """(CA, deslocamento do ajuste): o CA par mais perto do da planilha com deslocamento
    ALVO_AJUSTE; senão o que chega mais perto dele. Cada ponto de CA sobe o alvo do ajuste
    0,05 na escala 0-20 (0,25 ponto interno): procura em volta da estimativa."""
    w = weights_for(convert(values, ca_sheet), weights)
    first = game_shift(values, ca_sheet, weights, w)
    if first is None:
        return ca_sheet, None
    guess = ca_sheet + 4 * (ALVO_AJUSTE - first)
    best = None
    for ca in range(max(2, guess - 12, ca_sheet - CA_FAIXA), min(200, guess + 12, ca_sheet + CA_FAIXA) + 1):
        shift = game_shift(values, ca, weights, w)
        key = (abs(shift - ALVO_AJUSTE), ca % 2, abs(ca - ca_sheet))
        if best is None or key < best[0]:
            best = (key, ca, shift)
    return (best[1], best[2]) if best else (ca_sheet, first)


# ------------------------------------------------------------------
# Plano e gravação
# ------------------------------------------------------------------

@dataclass
class Change:
    uid: int
    name: str
    ca_sheet: int
    ca: int
    pa: int
    shift: int | None
    writes: list[tuple[int, bytes, str]] = field(default_factory=list)   # (posição, bytes, rótulo)
    warnings: list[str] = field(default_factory=list)


def _names_block(people: bytes, start: int, end: int, name_tables) -> int | None:
    """Posição do bloco de nomes (u32 x3, u32 tamanho + nome) do registro; o nascimento vem depois."""
    return comissao._names_before(people, end - 14, name_tables, back=end - start)


def plan(people: bytes, server: bytes, players: list[dict], year_shift: int = 0,
         weights: Weights | None = None) -> list[Change]:
    weights = weights or Weights.load()
    tab = tables(people)
    t2, t3 = index_fixed(people, tab.t2, tab.n2, T2_SIZE), index_fixed(people, tab.t3, tab.n3, T3_SIZE)
    records = person_records(people, tab.a_end)
    name_tables = comissao.name_tables(server)
    changes = []
    for spec in players:
        uid = spec["uid"]
        change = Change(uid, spec.get("name", ""), int(spec["ca"]), int(spec["ca"]), int(spec["pa"]), None)
        changes.append(change)
        if uid not in records or uid not in t3:
            change.warnings.append("sem registro de jogador no people_db")
            continue
        start, end = records[uid]
        if people[start] != PLAYER:
            change.warnings.append(f"registro A tipo {people[start]} (não é jogador comum); fica como está")
            continue
        values = t3_values(spec, people[t3[uid] + 1:t3[uid] + 80])
        change.writes.append((t3[uid] + 1, values, "atributos e posições"))
        change.ca, change.shift = choose_ca(values, change.ca_sheet, weights)
        change.pa = max(int(spec["pa"]), change.ca)
        if change.shift != ALVO_AJUSTE:
            change.warnings.append(f"ajuste do New Game {change.shift} (o alvo é {ALVO_AJUSTE}): a ficha pode sair ±1")
        reps = [spec.get(k) for k in ("home_reputation", "current_reputation", "world_reputation")]
        if all(r is not None for r in reps):
            reps = [max(1, min(200, round(int(r) / REP_SCALE))) for r in reps]
            change.writes.append((start + REP_AT, struct.pack("<3H", *reps), "reputações"))
        change.writes.append((start + CA_AT, struct.pack("<HH", change.ca, change.pa), "CA e PA"))
        if spec.get("weight") and spec.get("height"):
            change.writes.append((start + WEIGHT_AT, struct.pack("<HH", int(spec["weight"]), int(spec["height"])),
                                  "peso e altura"))
        if "personality" in spec:
            change.writes.append((t2[uid] + 1, bytes(int(spec["personality"][k]) for k in PERSONALITY),
                                  "personalidade"))
        names = _names_block(people, start, end, name_tables)
        if names is None:
            change.warnings.append("bloco de nomes não achado: nascimento e nação ficam como estão")
            continue
        size = struct.unpack_from("<I", people, names + 12)[0]
        born = names + 16 + 2 * size + (2 if size else 0)
        if spec.get("birth_date"):
            date = shift_years(dt.date.fromisoformat(spec["birth_date"]), year_shift)
            change.writes.append((born, encode_date(date), f"nascimento {date.isoformat()}"))
        if spec.get("nationality_code") is not None:
            change.writes.append((born + 5, struct.pack("<I", int(spec["nationality_code"])), "nação"))
    return changes


def apply(people: bytes, changes: list[Change]) -> bytes:
    out = bytearray(people)
    for change in changes:
        for at, data, _ in change.writes:
            out[at:at + len(data)] = data
    return bytes(out)
