"""Codificação dos campos vivos de jogador do FM06 6.0.2.

Este módulo não toca no processo. Ele converte valores "como o jogo mostra"
nos bytes que o jogo guarda na memória e monta a lista de escritas que o
script ``scripts/live_player_editor.py`` aplica.

Objetos (assinatura de 20 bytes imediatamente antes do UID):

    Player   456 bytes
    PData     36 bytes
    Playing  112 bytes

Atributos em Playing (validado com as fichas do Saviola e do Zidane):

    ABSOLUTE  memória = 5 * valor (+0..4); exibido = memória // 5
    RELATIVE  byte com sinal; exibido = min(20, (memória + base(CA)) // 5)
    DIRECT    posições, escala 1..20
"""

from __future__ import annotations

import datetime as dt
import json
import struct
import unicodedata
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FMM_DIR = ROOT / "reverse" / "fmm"


SIGNATURES = {
    "Player": (0x010F1034, 0x010F1020, 0x010F0FF8, 0x010F0FEC, 0x010F0FD8),
    "PData": (0x010B697C, 0x010B6968, 0x010B6940, 0x010B6934, 0x010B6920),
    "Playing": (0x010BA73C, 0x010BA72C, 0x010BA704, 0x010BA6F8, 0x010BA6E4),
}

# Quantos bytes ler antes e depois do UID para cobrir o objeto inteiro.
OBJECT_SPAN = {
    "Player": (224, 456 - 224),
    "PData": (20, 36 - 20),
    "Playing": (20, 112 - 20),
}


def signature_needle(kind: str, uid: int) -> bytes:
    return struct.pack("<5I", *SIGNATURES[kind]) + struct.pack("<I", uid)


# ------------------------------------------------------------------
# Campos simples
# ------------------------------------------------------------------

@dataclass(frozen=True)
class Field:
    obj: str
    rel: int
    fmt: str
    low: int
    high: int


PLAYER_FIELDS = {
    "ca": Field("Player", -204, "<H", 1, 200),
    "pa": Field("Player", -202, "<H", 1, 200),
    "height": Field("Player", -76, "<H", 100, 250),
    "weight": Field("Player", -78, "<H", 30, 150),
    "home_reputation": Field("Player", -210, "<H", 0, 10000),
    "current_reputation": Field("Player", -208, "<H", 0, 10000),
    "world_reputation": Field("Player", -206, "<H", 0, 10000),
}

BORN_REL = 52

PERSONALITY = (
    "Adaptability", "Ambition", "Loyalty", "Pressure",
    "Professional", "Sportsmanship", "Temperament", "Controversy",
)
PERSONALITY_REL = 8

PREFERRED_MOVES_REL = -48
PREFERRED_MOVES_COUNT = 48


# ------------------------------------------------------------------
# Atributos Playing
# ------------------------------------------------------------------

RELATIVE_FMM_INDEXES = set(range(0, 10)) | set(range(14, 21)) | set(range(43, 51))
DIRECT_FMM_INDEXES = set(range(54, 79))

PT_ALIASES = {
    "cabeceamento": "Heading",
    "cantos": "Corner",
    "cruzamentos": "Crossing",
    "desarme": "Tackling",
    "finalizacao": "Finishing",
    "finta": "Dribbling",
    "lancam. longos": "Throwing",
    "lancamentos longos": "Throwing",
    "livres": "Set Pieces",
    "marcacao": "Marking",
    "marcacao penalties": "Penalty",
    "passe": "Passing",
    "primeiro toque": "First Touch",
    "remates longe": "Long Shots",
    "tecnica": "Technique",
    "agressividade": "Aggression",
    "antecipacao": "Anticipation",
    "bravura": "Bravery",
    "compostura": "Composure",
    "concentracao": "Concentration",
    "criatividade": "Creativity",
    "decisoes": "Decision",
    "determinacao": "Determination",
    "influencia": "Influence",
    "instinto": "Flair",
    "posicionamento": "Positioning",
    "sem bola": "Off the ball",
    "trabalho equipa": "Team work",
    "indice trabalho": "Work rate",
    "aceleracao": "Acceleration",
    "agilidade": "Agility",
    "balance": "Balance",
    "cond. fis. natural": "Natural fit.",
    "condicao fisica natural": "Natural fit.",
    "forca": "Strength",
    "impulsao": "Jumping",
    "resistencia": "Stamina",
    "velocidade": "Pace",
}


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.casefold().split())


@dataclass(frozen=True)
class Attribute:
    fmm_index: int
    name: str
    rel: int
    kind: str  # ABSOLUTE | RELATIVE | DIRECT


def load_attributes(layout_path: Path | None = None) -> dict[str, Attribute]:
    """Atributos indexados por nome normalizado (inglês e português)."""
    path = layout_path or FMM_DIR / "playing_attributes_layout.json"
    fields = json.loads(path.read_text(encoding="utf-8"))["fields"]
    by_name: dict[str, Attribute] = {}
    for item in fields:
        index = item["fmm_index"]
        if index in DIRECT_FMM_INDEXES:
            kind = "DIRECT"
        elif index in RELATIVE_FMM_INDEXES:
            kind = "RELATIVE"
        else:
            kind = "ABSOLUTE"
        attribute = Attribute(index, item["field"], item["relative_to_playing_uid"], kind)
        by_name[_norm(item["field"])] = attribute
    for alias, english in PT_ALIASES.items():
        by_name[_norm(alias)] = by_name[_norm(english)]
    return by_name


def relative_base(ca: int) -> int:
    """Base da escala relativa ao CA.

    Ajustada em dois pontos: CA 160 -> 84 (Saviola), CA 185 -> 97 (Zidane).
    Provisória: confirmar com mais jogadores.
    """
    return (ca + 9) // 2


def decode_attribute(attribute: Attribute, raw: int, ca: int) -> int:
    if attribute.kind == "DIRECT":
        return raw
    if attribute.kind == "ABSOLUTE":
        return raw // 5
    signed = raw - 256 if raw > 127 else raw
    return max(0, min(20, (signed + relative_base(ca)) // 5))


def encode_attribute(attribute: Attribute, value: int, ca: int) -> int:
    """Valor exibido (1..20) -> byte. Mira o meio da faixa para tolerar
    pequenos erros na base."""
    if not 1 <= value <= 20:
        raise ValueError(f"{attribute.name}: {value} fora de 1..20")
    if attribute.kind == "DIRECT":
        return value
    if attribute.kind == "ABSOLUTE":
        return 5 * value + 2
    signed = 5 * value - relative_base(ca) + 2
    if not -128 <= signed <= 127:
        raise ValueError(f"{attribute.name}: {value} não cabe com CA {ca}")
    return signed & 0xFF


# ------------------------------------------------------------------
# Preferred Moves
# ------------------------------------------------------------------

def load_moves(layout_path: Path | None = None) -> dict[str, int]:
    path = layout_path or FMM_DIR / "preferred_moves_layout.json"
    moves = json.loads(path.read_text(encoding="utf-8"))["moves"]
    by_name: dict[str, int] = {}
    for move in moves:
        by_name[_norm(move["move_name"])] = move["fmm_index"]
        if move.get("visible_portuguese"):
            by_name[_norm(move["visible_portuguese"])] = move["fmm_index"]
    return by_name


def move_index(move: int | str, moves: dict[str, int]) -> int:
    if isinstance(move, int):
        index = move
    else:
        key = _norm(move)
        if key not in moves:
            raise KeyError(f"Preferred move desconhecido: {move!r}")
        index = moves[key]
    if not 0 <= index < PREFERRED_MOVES_COUNT:
        raise ValueError(f"Preferred move fora de 0..47: {index}")
    return index


# ------------------------------------------------------------------
# Datas
# ------------------------------------------------------------------

def encode_date(date: dt.date) -> bytes:
    day_of_year = (date - dt.date(date.year, 1, 1)).days
    return struct.pack("<HH", day_of_year, date.year)


def decode_date(raw: bytes) -> dt.date:
    day_of_year, year = struct.unpack("<HH", raw)
    return dt.date(year, 1, 1) + dt.timedelta(days=day_of_year)


def shift_years(date: dt.date, years: int) -> dt.date:
    try:
        return date.replace(year=date.year + years)
    except ValueError:  # 29/02 em ano não bissexto
        return date.replace(year=date.year + years, day=28)


# ------------------------------------------------------------------
# Plano de escrita
# ------------------------------------------------------------------

@dataclass
class Write:
    obj: str
    rel: int
    old: bytes
    new: bytes
    label: str


class LivePlayer:
    """Visão de um jogador a partir dos bytes dos três objetos.

    ``blocks[kind]`` contém o objeto inteiro; ``uid_at[kind]`` é a posição
    do UID dentro do bloco.
    """

    def __init__(self, uid: int, blocks: dict[str, bytes], uid_at: dict[str, int]):
        self.uid = uid
        self.blocks = {kind: bytearray(data) for kind, data in blocks.items()}
        self.uid_at = dict(uid_at)
        self.attributes = load_attributes()
        self.moves = load_moves()

    def unique_attributes(self) -> list[Attribute]:
        unique = {a.fmm_index: a for a in self.attributes.values()}
        return [unique[i] for i in sorted(unique)]

    def read(self, obj: str, rel: int, size: int) -> bytes:
        start = self.uid_at[obj] + rel
        return bytes(self.blocks[obj][start:start + size])

    def _set(self, obj: str, rel: int, data: bytes) -> None:
        start = self.uid_at[obj] + rel
        self.blocks[obj][start:start + len(data)] = data

    def get(self, name: str) -> int:
        field = PLAYER_FIELDS[name]
        return struct.unpack(field.fmt, self.read(field.obj, field.rel, struct.calcsize(field.fmt)))[0]

    def attribute_value(self, name: str) -> int:
        attribute = self.attributes[_norm(name)]
        raw = self.read("Playing", attribute.rel, 1)[0]
        return decode_attribute(attribute, raw, self.get("ca"))

    def born(self) -> dt.date:
        return decode_date(self.read("Player", BORN_REL, 4))

    def move_active(self, index: int) -> bool:
        byte = self.read("Player", PREFERRED_MOVES_REL + index // 8, 1)[0]
        return bool(byte >> (index % 8) & 1)

    def summary(self) -> dict:
        return {
            "uid": self.uid,
            **{name: self.get(name) for name in PLAYER_FIELDS},
            "born": self.born().isoformat(),
            "personality": {
                name: self.read("PData", PERSONALITY_REL + i, 1)[0]
                for i, name in enumerate(PERSONALITY)
            },
            "attributes": {
                attribute.name: self.attribute_value(attribute.name)
                for attribute in self.unique_attributes()
            },
            "preferred_moves": [i for i in range(PREFERRED_MOVES_COUNT) if self.move_active(i)],
        }

    def plan(self, spec: dict, year_shift: int = 0, keep_display: bool = True) -> list[Write]:
        """Monta as escritas para ``spec`` sem tocar no processo."""
        writes: list[Write] = []

        def put(obj: str, rel: int, data: bytes, label: str) -> None:
            old = self.read(obj, rel, len(data))
            if old != data:
                writes.append(Write(obj, rel, old, data, label))
                self._set(obj, rel, data)

        old_ca = self.get("ca")
        new_ca = int(spec.get("ca", old_ca))

        # Valores relativos dependem do CA: guarda o que o jogo mostra
        # antes de trocar o CA para poder reescrever depois.
        explicit = {
            self.attributes[_norm(k)].fmm_index
            for k in spec.get("attributes", {})
            if _norm(k) in self.attributes
        }
        preserved = {}
        if keep_display and new_ca != old_ca:
            for attribute in self.unique_attributes():
                if attribute.kind == "RELATIVE" and attribute.fmm_index not in explicit:
                    preserved[attribute.name] = self.attribute_value(attribute.name)

        for name, field in PLAYER_FIELDS.items():
            if name in spec:
                value = int(spec[name])
                if not field.low <= value <= field.high:
                    raise ValueError(f"{name}: {value} fora de {field.low}..{field.high}")
                put(field.obj, field.rel, struct.pack(field.fmt, value), name)

        if "birth_date" in spec:
            date = shift_years(dt.date.fromisoformat(spec["birth_date"]), year_shift)
            put("Player", BORN_REL, encode_date(date), f"born {date.isoformat()}")

        # Desloca o byte pela diferença das bases: mantém exato o valor
        # interno (byte + base), não só o valor exibido.
        shift = relative_base(old_ca) - relative_base(new_ca)
        for name, value in preserved.items():
            attribute = self.attributes[_norm(name)]
            raw = self.read("Playing", attribute.rel, 1)[0]
            signed = max(-128, min(127, (raw - 256 if raw > 127 else raw) + shift))
            put("Playing", attribute.rel, bytes([signed & 0xFF]),
                f"{attribute.name} (mantém {value} com CA {new_ca})")

        for name, value in spec.get("attributes", {}).items():
            key = _norm(name)
            if key not in self.attributes:
                raise KeyError(f"Atributo desconhecido: {name!r}")
            attribute = self.attributes[key]
            put("Playing", attribute.rel, bytes([encode_attribute(attribute, int(value), new_ca)]),
                f"{attribute.name} = {value}")

        for name, value in spec.get("positions", {}).items():
            attribute = self.attributes[_norm(name)]
            if attribute.kind != "DIRECT":
                raise ValueError(f"{name} não é posição")
            put("Playing", attribute.rel, bytes([encode_attribute(attribute, int(value), new_ca)]),
                f"posição {attribute.name} = {value}")

        for name, value in spec.get("personality", {}).items():
            matches = [i for i, p in enumerate(PERSONALITY) if _norm(p) == _norm(name)]
            if not matches:
                raise KeyError(f"Personalidade desconhecida: {name!r}")
            if not 1 <= int(value) <= 20:
                raise ValueError(f"{name}: {value} fora de 1..20")
            put("PData", PERSONALITY_REL + matches[0], bytes([int(value)]), f"{PERSONALITY[matches[0]]} = {value}")

        moves = spec.get("preferred_moves", {})
        for action, flag in (("add", True), ("remove", False)):
            for move in moves.get(action, []):
                index = move_index(move, self.moves)
                rel = PREFERRED_MOVES_REL + index // 8
                byte = self.read("Player", rel, 1)[0]
                mask = 1 << (index % 8)
                byte = byte | mask if flag else byte & ~mask
                put("Player", rel, bytes([byte]), f"move {index} {'+' if flag else '-'}")

        return writes
