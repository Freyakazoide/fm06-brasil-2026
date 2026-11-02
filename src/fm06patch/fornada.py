"""Modelos de jogador para a fornada de base (ficha C14).

O regen do FM06 herda o "perfil" do bloco de atributos (PLAYING_DATA) do aposentado: atributos
técnicos e mentais guardados em relação ao CA, posições, pés. A criação (0x77BEF0) só sorteia
físicos e alguns mentais, e o CA sai das posições. A fornada não tem aposentado: cada garoto
recebe um modelo sorteado de data/modelos/fornada_tipos.csv, gravado no bloco antes da criação.

Planilha (uma linha por tipo de jogador):

- peso: chance relativa do tipo;
- posicoes: códigos detalhados com a nota (DC:20 DD:12); as gerais (zagueiro, meia...) e os
  lados saem delas, como o jogo guarda; a principal fica 20, as outras variam ±2;
- pes: D/E/A com as chances (destro, canhoto, os dois bons);
- fortes / fracos: atributos (nomes do layout reverse/fmm/playing_attributes_layout.json ou os
  apelidos em português do live_player) acima ou abaixo da média do jogador;
- traits: movimentos preferidos possíveis (reverse/fmm/preferred_moves_layout.json), separados
  por "|"; o garoto ganha 0 a 3 deles.

Codificação no bloco, a partir do UID do bloco (bloco+0x14): posições direto (1–20); atributos
"relativos" como byte com sinal em unidades de 1/5 de ponto, em relação ao CA; "absolutos" como
5 × nota + 2 (live_player.encode_attribute). Movimentos preferidos: 48 bits no jogador
(UID − 48).
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass, field
from pathlib import Path

from .live_player import (DIRECT_FMM_INDEXES, RELATIVE_FMM_INDEXES, _norm, load_attributes, load_moves,
                          move_index)

ROOT = Path(__file__).resolve().parents[2]
SHEET = ROOT / "data" / "modelos" / "fornada_tipos.csv"

# código -> (posição detalhada, geral, lado), deslocamentos a partir do UID do bloco
GENERAL = {"GR": 8, "LIB": 9, "D": 10, "DM": 11, "M": 12, "MO": 13, "AT": 14, "ALA": 15, "LIVRE": 16}
RIGHT, LEFT, CENTER = 17, 18, 19
DETAILED = {
    "DE": (20, "D", LEFT), "DC": (21, "D", CENTER), "DD": (22, "D", RIGHT), "MDC": (23, "DM", CENTER),
    "ME": (24, "M", LEFT), "MC": (25, "M", CENTER), "MD": (26, "M", RIGHT),
    "MOE": (27, "MO", LEFT), "MOC": (28, "MO", CENTER), "MOD": (29, "MO", RIGHT),
    "PL": (30, "AT", CENTER), "ALE": (31, "ALA", LEFT), "ALD": (32, "ALA", RIGHT),
}
POSITION_RELS = range(8, 33)
LEFT_FOOT, RIGHT_FOOT = "Left foot", "Right foot"
GOALKEEPING = set(range(43, 51))                   # relativos de goleiro (Handling...)
OUTFIELD_TECH = set(range(0, 10))
PHYSICAL = {32, 33, 34, 35, 36, 37, 40}
# absolutos sem sorteio na criação: (mínimo, máximo) normal
ABSOLUTE_RANGE = {10: (3, 11), 11: (3, 11), 12: (3, 11), 13: (2, 9),          # bolas paradas
                  21: (4, 14), 22: (3, 12), 23: (2, 10), 24: (5, 15), 25: (6, 15), 26: (4, 14),
                  27: (5, 15), 28: (5, 14), 29: (6, 17), 30: (7, 15), 31: (7, 16),
                  38: (1, 8), 39: (7, 16), 51: (2, 10), 52: (1, 5), 53: (1, 5)}
PHYSICAL_RANGE = (6, 14)
MOVES_BYTES = 6


@dataclass
class Type:
    name: str
    weight: int
    positions: dict[str, int]
    feet: dict[str, int]
    strong: list[str]
    weak: list[str]
    traits: list[str]

    @property
    def goalkeeper(self) -> bool:
        return "GR" in self.positions


@dataclass
class Template:
    type: str
    playing: dict[int, int] = field(default_factory=dict)     # deslocamento do UID do bloco -> byte
    moves: bytes = bytes(MOVES_BYTES)
    foot: str = "D"
    traits: list[str] = field(default_factory=list)


def _words(text: str, attrs) -> list[str]:
    """Nomes de atributo separados por espaço; nomes com espaço ("Long Shots") casam primeiro."""
    names = sorted({a.name for a in attrs.values()} | set(attrs), key=len, reverse=True)
    out, rest = [], f" {_norm(text)} "
    for name in names:
        key = f" {_norm(name)} "
        while key in rest:
            out.append(attrs[_norm(name)].name)
            rest = rest.replace(key, " ", 1)
    if rest.strip():
        raise ValueError(f"atributo desconhecido na planilha: {rest.strip()!r}")
    return out


def load_types(path: Path = SHEET) -> list[Type]:
    attrs = load_attributes()
    types = []
    for row in csv.DictReader(path.open(encoding="utf-8-sig")):
        positions = {}
        for item in row["posicoes"].split():
            code, rating = item.split(":")
            if code not in DETAILED and code not in GENERAL:
                raise ValueError(f"{row['tipo']}: posição {code} desconhecida")
            positions[code] = int(rating)
        feet = {item[0]: int(item[1:]) for item in row["pes"].split()}
        traits = [t.strip() for t in row["traits"].split("|") if t.strip()]
        types.append(Type(row["tipo"], int(row["peso"]), positions, feet, _words(row["fortes"], attrs),
                          _words(row["fracos"], attrs), traits))
    return types


def _absolute(value: int) -> int:
    return 5 * max(1, min(20, value)) + 2


def build(kind: Type, rng: random.Random) -> Template:
    attrs = {a.fmm_index: a for a in load_attributes().values()}
    by_name = {a.name: a for a in attrs.values()}
    strong = {by_name[n].fmm_index for n in kind.strong}
    weak = {by_name[n].fmm_index for n in kind.weak}
    out = Template(kind.name)
    # posições: principal 20, as outras ±2; gerais e lados = maior nota do grupo
    main = max(kind.positions, key=kind.positions.get)
    ratings = {rel: 1 for rel in POSITION_RELS}
    for code, rating in kind.positions.items():
        value = rating if code == main else max(8, min(19, rating + rng.randint(-2, 2)))
        if code in GENERAL:
            ratings[GENERAL[code]] = max(ratings[GENERAL[code]], value)
            ratings[CENTER] = max(ratings[CENTER], value)
            continue
        rel, general, side = DETAILED[code]
        ratings[rel] = value
        ratings[GENERAL[general]] = max(ratings[GENERAL[general]], value)
        ratings[side] = max(ratings[side], value)
    out.playing.update(ratings)
    # pés
    foot = rng.choices(list(kind.feet), list(kind.feet.values()))[0]
    good, bad = rng.randint(15, 20), rng.randint(4, 11)
    left, right = {"D": (bad, good), "E": (good, bad), "A": (rng.randint(13, 18), rng.randint(14, 19))}[foot]
    out.playing[by_name[LEFT_FOOT].rel], out.playing[by_name[RIGHT_FOOT].rel] = _absolute(left), _absolute(right)
    out.foot = foot
    # atributos relativos ao CA: ruído, fortes e fracos; goleiro x linha
    versatile = len(kind.positions) >= 3
    for index, attr in attrs.items():
        if index in DIRECT_FMM_INDEXES or attr.name in (LEFT_FOOT, RIGHT_FOOT):
            continue
        if index in RELATIVE_FMM_INDEXES:
            offset = round(rng.gauss(0, 6))
            if index in strong:
                offset += rng.randint(10, 22)
            elif index in weak:
                offset -= rng.randint(12, 25)
            if index in GOALKEEPING and not kind.goalkeeper:
                offset = -rng.randint(30, 40)
            elif index in OUTFIELD_TECH and kind.goalkeeper and index not in strong:
                offset -= rng.randint(10, 20)
            out.playing[attr.rel] = max(-100, min(100, offset)) & 0xFF
            continue
        low, high = PHYSICAL_RANGE if index in PHYSICAL else ABSOLUTE_RANGE.get(index, (0, 0))
        if not high:
            continue
        if index in (52, 53, 51) and kind.goalkeeper:          # saída, soco, excentricidade
            low, high = 6, 15
        value = rng.randint(low, high)
        if index in strong:
            value = max(value, rng.randint(13, 18))
        elif index in weak:
            value = min(value, rng.randint(2, 7))
        if index == 28 and versatile:                            # versatilidade: várias posições
            value = max(value, rng.randint(11, 17))
        out.playing[attr.rel] = _absolute(value)
    # movimentos preferidos: 0 a 3 dos do tipo
    moves = load_moves()
    count = rng.choices([0, 1, 2, 3], [35, 35, 20, 10])[0]
    picked = rng.sample(kind.traits, min(count, len(kind.traits)))
    bits = bytearray(MOVES_BYTES)
    for name in picked:
        index = move_index(name, moves)
        bits[index // 8] |= 1 << (index % 8)
    out.moves, out.traits = bytes(bits), picked
    return out


def pick(types: list[Type], rng: random.Random) -> Type:
    return rng.choices(types, [t.weight for t in types])[0]
