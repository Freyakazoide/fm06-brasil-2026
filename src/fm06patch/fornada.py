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


# ---------------------------------------------------------------------------
# Código no jogo (patch fornada_base): todo ano, no dia da data/modelos/fornada_config.csv, N
# garotos em cada clube de país jogável (no mod, o Brasil) com time de juniores e elenco até 100.
# Cada garoto: molde (0xA47930), bloco PLAYING_DATA novo (0x7B9670) com um dos modelos
# embutidos (sorteado pelo gerador do jogo, 0xC4E1F0), tabela do banco, criação 0x77BEF0,
# movimentos preferidos e contrato 0x779B40 — o mesmo que tools/re/chamada_remota.py faz.
# ---------------------------------------------------------------------------
CONFIG = ROOT / "data" / "modelos" / "fornada_config.csv"
DAILY_CALL = 0x007813B9           # call 0x775950 no método diário do REGENERATION_MANAGER
DAILY_TARGET = 0x00775950         # (data) ret 4
TODAY_DAY, TODAY_YEAR = 0x014EAB38, 0x014EAB3A      # dia do ano (base 0) e ano do motor
CLUBS, NATIONS_PLAYABLE, CLUB_NATION = 0x014EAA30, 0xFF, 0xDC
PLAYING_TABLE, MANAGER, RNG = 0x014EAA6C, 0x0132C108, 0x014EC000
HAS_YOUTH_TEAM, SQUAD_SIZE = 0x00A28E70, 0x009DDF30
TEMPLATE_NEW, ALLOC, PLAYING_NEW, SET_PLAYING = 0x00A47930, 0x00A3BB00, 0x007B9670, 0x00A3EF40
CREATE, CONTRACT, RANDOM = 0x0077BEF0, 0x00779B40, 0x00C4E1F0
PLAYING_FIRST, PLAYING_LAST = 8, 86                 # cópia do modelo: UID do bloco + 8 .. + 86
# base do clube no potencial (ficha C14): q = base (CLUB+0xE1) + captação (CLUB+0xE0), de 2 a 40,
# notas que a diretoria e a regulação das finanças sobem com investimento (0xA289A0). Com chance
# de q/2 % o garoto é uma "joia": PA no mínimo 120 + sorteio até 2q; senão PA + (q − 20) / 2.
# PA entre 40 e 200; o CA não passa do PA.
CLUB_YOUTH, CLUB_RECRUITMENT = 0xE1, 0xE0
PLAYER_CA, PLAYER_PA = -0xB8, -0xB6                 # u16, do começo da assinatura (UID − 204/202)
GEM_BASE, PA_MIN, PA_MAX = 120, 40, 200
# peneira (ficha C14): na segunda data da configuração, cada clube com captação c tem chance de
# 5c - 25 % (c 10 -> 25 %, 15 -> 50 %, 20 -> 75 %) de ganhar 1 garoto de PA no mínimo
# 140 + sorteio até 40 + c (máximo 200): investir em captação traz meninos bons.
SIEVE_BASE, SIEVE_SPREAD = 140, 41
RECORD = 88                                         # 79 bytes do bloco, 1 livre, 6 de movimentos
TEMPLATES = 256


@dataclass(frozen=True)
class Config:
    day: int            # fornada: dia do ano (base 0)
    per_club: int
    sieve_day: int      # peneira: dia do ano (base 0)


def load_config(path: Path = CONFIG) -> Config:
    import datetime as dt

    row = next(csv.DictReader(path.open(encoding="utf-8-sig")))
    day_of = lambda d, m: dt.date(2006, int(m), int(d)).timetuple().tm_yday - 1    # ano do motor
    return Config(day_of(row["dia"], row["mes"]), int(row["quantidade"]),
                  day_of(row["peneira_dia"], row["peneira_mes"]))


def template_table(types: list[Type] | None = None, count: int = TEMPLATES, seed: int = 2026) -> bytes:
    """Os modelos embutidos: o tipo sai pelo peso, então o sorteio uniforme no jogo respeita
    as chances da planilha."""
    types = types or load_types()
    rng = random.Random(seed)
    out = bytearray()
    for _ in range(count):
        model = build(pick(types, rng), rng)
        record = bytearray(RECORD)
        for rel, value in model.playing.items():
            record[rel - PLAYING_FIRST] = value
        record[80:80 + MOVES_BYTES] = model.moves
        out += record
    return bytes(out)


class _Code:
    """Montador com rótulos (saltos sempre em 32 bits)."""

    def __init__(self, base: int):
        self.base, self.code, self.labels, self.fixups = base, bytearray(), {}, []

    def raw(self, hexa: str | bytes) -> "_Code":
        self.code += bytes.fromhex(hexa) if isinstance(hexa, str) else hexa
        return self

    def u32(self, value: int) -> "_Code":
        self.code += (value & 0xFFFFFFFF).to_bytes(4, "little")
        return self

    def call(self, target: int) -> "_Code":
        self.code += b"\xE8" + (target - (self.base + len(self.code) + 5)).to_bytes(4, "little", signed=True)
        return self

    def jump(self, opcode: str, label: str) -> "_Code":
        self.raw(opcode)
        self.fixups.append((len(self.code), label))
        self.code += bytes(4)
        return self

    def label(self, name: str) -> "_Code":
        self.labels[name] = len(self.code)
        return self

    def done(self) -> bytes:
        for at, name in self.fixups:
            self.code[at:at + 4] = (self.labels[name] - (at + 4)).to_bytes(4, "little", signed=True)
        return bytes(self.code)


def hook_code(base: int, events: list[tuple[int, int, int]]) -> bytes:
    """events: (dia do ano, rotina, onde guarda o último ano em que rodou)."""
    a = _Code(base)
    a.raw("56 8BF1 FF742408").call(DAILY_TARGET)                  # a chamada original (ret 4)
    for n, (day, routine, last_year) in enumerate(events):
        a.raw("0FB705").u32(TODAY_DAY).raw("3D").u32(day).jump("0F85", f"prox{n}")
        a.raw("0FB705").u32(TODAY_YEAR).raw("3B05").u32(last_year).jump("0F84", f"prox{n}")
        a.raw("A3").u32(last_year).call(routine)                  # uma vez por ano
        a.label(f"prox{n}")
    a.raw("5E C20400")
    return a.done()


def _club_loop(a: _Code, body) -> None:
    """Para cada clube de país jogável com time de juniores e elenco até 100: ebx = clube,
    [ebp-8] = nação; body(a) monta o que fazer e pode saltar para "prox"."""
    a.raw("55 8BEC 83EC10 53 56 57 33FF")                         # edi = índice do clube
    a.label("laco").raw("A1").u32(CLUBS).raw("8B4004 3B7808").jump("0F8D", "fim")
    a.raw("8B4004 8B1CB8 85DB").jump("0F84", "prox")             # ebx = clube
    a.raw("8B83").u32(CLUB_NATION).raw("85C0").jump("0F84", "prox")
    a.raw("80B8").u32(NATIONS_PLAYABLE).raw("00").jump("0F84", "prox")   # só país jogável
    a.raw("8945F8 8BCB").call(HAS_YOUTH_TEAM).raw("84C0").jump("0F84", "prox")
    a.raw("6A00 8BCB").call(SQUAD_SIZE).raw("663D6400").jump("0F8F", "prox")  # elenco > 100
    body(a)
    a.label("prox").raw("47").jump("E9", "laco")
    a.label("fim").raw("5F 5E 5B 8BE5 5D C3")


def all_clubs_code(base: int, make_youth: int, per_club: int) -> bytes:
    a = _Code(base)

    def body(a: _Code) -> None:
        a.raw("C745F4").u32(per_club)
        a.label("garoto").raw("FF75F8 53").call(make_youth).raw("FF4DF4").jump("0F85", "garoto")

    _club_loop(a, body)
    return a.done()


def sieve_code(base: int, make_youth: int) -> bytes:
    """A peneira: chance de 5c - 25 % por clube (c = captação) de 1 garoto de PA alto."""
    a = _Code(base)

    def body(a: _Code) -> None:
        a.raw("0FB683").u32(CLUB_RECRUITMENT).raw("8945F4")      # [ebp-0xC] = captação
        a.raw("8D0480 83E819").jump("0F8E", "prox").raw("8945F0")   # [ebp-0x10] = 5c - 25
        a.raw("6A64 B9").u32(RNG).call(RANDOM).raw("3B45F0").jump("0F8D", "prox")
        a.raw("FF75F8 53").call(make_youth).raw("85C0").jump("0F84", "prox").raw("8BF0")
        a.raw("8B45F4 83C0").raw(bytes([SIEVE_SPREAD])).raw("50 B9").u32(RNG).call(RANDOM)
        a.raw("05").u32(SIEVE_BASE).raw("3D").u32(PA_MAX).jump("0F8E", "teto").raw("B8").u32(PA_MAX)
        a.label("teto").raw("0FB78E").u32(PLAYER_PA).raw("3BC1").jump("0F8E", "prox")
        a.raw("668986").u32(PLAYER_PA)                                  # PA = o maior

    _club_loop(a, body)
    return a.done()


def make_youth_code(base: int, templates: int, count: int) -> bytes:
    """stdcall(clube, nação) -> o garoto (0 se falhou)."""
    a = _Code(base)
    a.raw("55 8BEC 81EC10040000 53 56 57 8B7D08 8B5D0C")         # edi = clube, ebx = nação
    a.raw("6A01 8D8D00FCFFFF").call(TEMPLATE_NEW)                 # molde em [ebp-0x400]
    a.raw("6A70").call(ALLOC).raw("83C404 8BF0 85F6").jump("0F84", "fim")
    a.raw("8BCE").call(PLAYING_NEW)
    a.raw("68").u32(count).raw("B9").u32(RNG).call(RANDOM)        # eax = modelo sorteado
    a.raw("69C0").u32(RECORD).raw("05").u32(templates).raw("8985F0FBFFFF 33C9")
    a.label("copia").raw("8A1408 88540E1C 41 83F94F").jump("0F82", "copia")   # 79 bytes
    a.raw("8B15").u32(PLAYING_TABLE).raw("8B4A04 8B01 56 FF10 894618")          # tabela, índice
    a.raw("56 8D8D00FCFFFF").call(SET_PLAYING)
    a.raw("53 6A00 8D8500FCFFFF 50 B9").u32(MANAGER).call(CREATE)
    a.raw("8BF0 85F6").jump("0F84", "fim")
    a.raw("8B85F0FBFFFF 33C9")
    a.label("mov").raw("8A540850 08540EE4 41 83F906").jump("0F82", "mov")      # OR nos 48 bits
    # base e captação do clube no potencial
    a.raw("0FB687").u32(CLUB_YOUTH).raw("0FB68F").u32(CLUB_RECRUITMENT).raw("03C1 8985F4FBFFFF")
    a.raw("6A64 B9").u32(RNG).call(RANDOM).raw("03C0 3B85F4FBFFFF").jump("0F8D", "ajuste")
    a.raw("8B85F4FBFFFF 03C0 40 50 B9").u32(RNG).call(RANDOM)            # joia: 120 + sorteio(2q+1)
    a.raw("05").u32(GEM_BASE).raw("0FB78E").u32(PLAYER_PA)
    a.raw("3BC1").jump("0F8E", "pronto").jump("E9", "limites")
    a.label("ajuste").raw("8B85F4FBFFFF 83E814 D1F8 0FB78E").u32(PLAYER_PA).raw("03C1")   # PA + (q - 20) / 2
    a.label("limites").raw("3D").u32(PA_MAX).jump("0F8E", "max").raw("B8").u32(PA_MAX)
    a.label("max").raw("83F8").raw(bytes([PA_MIN])).jump("0F8D", "min").raw("B8").u32(PA_MIN)
    a.label("min").raw("668986").u32(PLAYER_PA)
    a.raw("0FB78E").u32(PLAYER_CA).raw("3BC8").jump("0F8E", "pronto")
    a.raw("668986").u32(PLAYER_CA)                                          # CA <= PA
    a.label("pronto").raw("57 8B16 8BCE FF92").u32(0x278).raw("50 B9").u32(MANAGER).call(CONTRACT)
    a.raw("8BC6")                                                    # devolve o garoto (0 se falhou)
    a.label("fim").raw("5F 5E 5B 8BE5 5D C20800")
    return a.done()


def exe_swaps(data: bytes):
    from .exe_cave import SECTION_VA, off, sec_off, section_swaps, u32
    from .exe_patches import Swap

    hook, all_clubs, make_youth = SECTION_VA + 0x7000, SECTION_VA + 0x7080, SECTION_VA + 0x7140
    last_year, last_sieve, table = SECTION_VA + 0x7300, SECTION_VA + 0x7304, SECTION_VA + 0x7400
    sieve = SECTION_VA + 0xCC00                                          # depois dos 256 modelos
    cfg = load_config()
    parts = [(hook, hook_code(hook, [(cfg.day, all_clubs, last_year), (cfg.sieve_day, sieve, last_sieve)])),
             (all_clubs, all_clubs_code(all_clubs, make_youth, cfg.per_club)),
             (make_youth, make_youth_code(make_youth, table, TEMPLATES)),
             (table, template_table()),
             (sieve, sieve_code(sieve, make_youth))]
    limits = [all_clubs, make_youth, last_year, sieve, SECTION_VA + 0x10000]   # cada parte até a seguinte
    for (start, code), limit in zip(parts, limits):
        if start + len(code) > limit:
            raise ValueError(f"fornada: código em 0x{start:X} invade 0x{limit:X}")
    swaps = list(section_swaps(data))
    swaps += [Swap(sec_off(start), bytes(len(code)), code) for start, code in parts]
    old = b"\xE8" + u32(DAILY_TARGET - (DAILY_CALL + 5))
    swaps.append(Swap(off(DAILY_CALL), old, b"\xE8" + u32(hook - (DAILY_CALL + 5))))
    return tuple(swaps)
