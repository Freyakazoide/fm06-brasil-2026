"""Tabelas de nomes do server_db.dat (primeiro nome, sobrenome, nome comum).

Cada tabela: u32 quantidade e, para cada nome,
    u8 0, u32 n, nome (UTF-16LE, n caracteres), 00 00, u16 uso, u32 nação, u32 índice, u32 UID
O índice é a posição na tabela (a pessoa cita o nome pelo índice) e "uso" é quantas
pessoas do banco têm o nome (confere em 96% dos nomes). A ordem é por nação e, dentro
dela, pelo uso.
"""

from __future__ import annotations

import struct
from collections import Counter
from dataclasses import dataclass, field

# começo do u32 quantidade de cada tabela no server_db 6.0.2 original
TABLES = {"first": 0x005F7416, "second": 0x0085C9F9, "common": 0x00DE5A49}


@dataclass
class Name:
    at: int          # posição do u8 0
    text: str
    uses: int
    nation: int
    index: int
    uid: int

    @property
    def size(self) -> int:
        return 1 + 4 + 2 * len(self.text) + 2 + 2 + 12


def read_table(data: bytes, start: int) -> tuple[list[Name], int]:
    """(nomes, posição logo depois da tabela)."""
    count = struct.unpack_from("<I", data, start)[0]
    at, names = start + 4, []
    for position in range(count):
        if data[at] != 0:
            raise ValueError(f"nomes: registro {position} sem 00 em 0x{at:X}")
        size = struct.unpack_from("<I", data, at + 1)[0]
        end = at + 5 + 2 * size
        if data[end:end + 2] != b"\0\0":
            raise ValueError(f"nomes: texto sem 00 00 em 0x{at:X}")
        uses, nation, index, uid = struct.unpack_from("<HIII", data, end + 2)
        if index != position:
            raise ValueError(f"nomes: índice {index} na posição {position}")
        names.append(Name(at, data[at + 5:end].decode("utf-16-le"), uses, nation, index, uid))
        at = end + 16
    return names, at


NEW_SHARE = 0.7              # parte do "uso" da nação que fica com os nomes da planilha
KINDS = {"prenome": "first", "sobrenome": "second", "apelido": "common"}
# o nome completo do jogador tem no máximo 2 palavras (pedido do usuário, 01/11): prenome e
# sobrenome de uma palavra só ("Pedro Antônio de Oliveira" não sai mais); apelido de até duas
MAX_WORDS = {"first": 1, "second": 1, "common": 2}


def _record(text: str, uses: int, nation: int, index: int, uid: int) -> bytes:
    return (b"\0" + struct.pack("<I", len(text)) + text.encode("utf-16-le") + b"\0\0"
            + struct.pack("<HIII", uses, nation, index, uid))


def locate(data: bytes, original: bytes) -> dict[str, int]:
    """Começo de cada tabela em ``data`` (o banco já mexido), achado pelos primeiros bytes
    da tabela no original: as outras mudanças não mexem nas tabelas de nomes."""
    found = {}
    for kind, start in TABLES.items():
        needle = original[start + 4:start + 68]          # sem a quantidade, que muda
        at = data.find(needle, max(0, start - 0x100000))
        if at < 0:
            raise ValueError(f"nomes: tabela {kind} não encontrada")
        found[kind] = at - 4
    return found


def cited(people: bytes, server: bytes) -> dict[str, Counter]:
    """Quantas pessoas do people_db citam cada índice de cada tabela (o "uso" do banco
    erra em 4%). ``server``: o banco com as tabelas de nomes no lugar (o original)."""
    from .comissao import NONE, PEOPLE_END, _PERSON_END, _names_before, name_tables

    tables = name_tables(server)
    out = {kind: Counter() for kind in TABLES}
    for match in _PERSON_END.finditer(people, 0, PEOPLE_END):
        index, uid = struct.unpack("<II", match.group(1) + match.group(2))
        if not (index < 2_000_000 and 0 < uid < 100_000_000):
            continue
        at = _names_before(people, match.start() + 5, tables, back=0x300)
        if at is None:
            continue
        first, second, common = struct.unpack_from("<III", people, at)
        out["first"][first] += 1
        out["second"][second] += 1
        if common != NONE:
            out["common"][common] += 1
    return out


@dataclass
class Plan:
    edits: dict[str, list[tuple[int, int, bytes]]] = field(default_factory=dict)  # (posição, tamanho, registro)
    placed: int = 0             # nomes novos no lugar de um nome que ninguém cita
    boosted: int = 0            # nomes da planilha que a nação já tinha
    dropped: list[str] = field(default_factory=list)   # novos sem vaga no bloco da nação


def plan(data: bytes, wanted: dict[tuple[str, int], dict[str, int]], starts: dict[str, int] | None = None,
         citations: dict[str, Counter] | None = None) -> Plan:
    """wanted: (tabela, nação) -> {nome: peso 1..100}.

    Cada nação é um bloco seguido na tabela, e o jogo sorteia dentro do bloco: nome posto no
    fim da tabela (como até 01/11) deixava o bloco do Brasil "comprido" e os regens saíam com
    nomes do Chile (a nação seguinte) e com o nome de índice 0 (Mohamed Alamosi). Agora:

    - nome novo ocupa, dentro do bloco, o lugar de um nome da nação que nenhuma pessoa cita
      (``citations``; os compostos primeiro, depois os de menor uso). Índice e UID ficam;
      sem vaga, o nome não entra (vai em ``dropped``, os de menor peso primeiro);
    - a soma do "uso" da nação fica a do original: os nomes da planilha somam NEW_SHARE dela
      (pelo peso), os compostos ficam com 0 e os outros dividem o resto na proporção de hoje
      (os de uso pequeno podem ir a 0: continuam no banco para quem tem o nome).
    """
    starts = starts or TABLES
    citations = citations or {}
    result = Plan()
    for kind in ("first", "second", "common"):
        names, _ = read_table(data, starts[kind])
        cites = citations.get(kind, Counter())
        uses = {n.index: n.uses for n in names}
        texts: dict[int, str] = {}
        for (table, nation), weights in sorted(wanted.items()):
            if table != kind or not weights:
                continue
            block = [n for n in names if n.nation == nation]
            total = sum(n.uses for n in block)
            by_text = {n.text.casefold(): n for n in block}
            listed = {text.casefold() for text in weights}
            compound = {n.index for n in block if len(n.text.split()) > MAX_WORDS[kind]}
            free = sorted((n for n in block if n.text.casefold() not in listed and not cites[n.index]),
                          key=lambda n: (n.index not in compound, n.uses, -n.index))
            new = sorted((t for t in weights if t.casefold() not in by_text), key=lambda t: (-weights[t], t))
            result.dropped += [f"{t} ({kind}, nação {nation})" for t in new[len(free):]]
            chosen: dict[int, str] = {}                 # índice -> nome da planilha
            for text in weights:
                if text.casefold() in by_text:
                    chosen[by_text[text.casefold()].index] = text
                    result.boosted += 1
            for slot, text in zip(free, new):
                chosen[slot.index] = text
                texts[slot.index] = text
                result.placed += 1
            if not total or not chosen:
                continue
            share = round(total * NEW_SHARE)
            scale = share / sum(weights[t] for t in chosen.values())
            for index, text in chosen.items():
                uses[index] = min(65535, max(1, round(weights[text] * scale)))
            rest = [n for n in block if n.index not in chosen]
            for n in rest:
                if n.index in compound:
                    uses[n.index] = 0
            others = [n for n in rest if n.index not in compound]
            left = total - sum(uses[i] for i in chosen)
            base = sum(n.uses for n in others)
            if others and base:
                for n in others:
                    uses[n.index] = min(65535, round(n.uses * left / base))   # pode ir a 0: fica, mas não é sorteado
            extra = sum(uses[n.index] for n in block) - total      # o arredondamento fecha a soma
            ranked = sorted(block, key=lambda n: -uses[n.index])
            if extra < 0:
                uses[ranked[0].index] = min(65535, uses[ranked[0].index] - extra)
            while extra > 0 and any(uses[n.index] > 1 for n in ranked):   # tira 1 dos mais usados
                for n in ranked:
                    if extra and uses[n.index] > 1:
                        uses[n.index] -= 1
                        extra -= 1
        edits = []
        for n in names:
            text = texts.get(n.index, n.text)
            if text != n.text or uses[n.index] != n.uses:
                edits.append((n.at, n.size, _record(text, uses[n.index], n.nation, n.index, n.uid)))
        result.edits[kind] = edits
    return result


def apply(data: bytes, changes: Plan, starts: dict[str, int] | None = None) -> bytes:
    """Troca os registros no lugar (o tamanho do nome muda; a quantidade e os índices não)."""
    out = bytearray(data)
    edits = sorted((e for kind in changes.edits.values() for e in kind), reverse=True)
    for at, size, record in edits:                      # de trás para frente: as posições não mudam
        out[at:at + size] = record
    return bytes(out)


def load_sheet(path) -> dict[tuple[str, int], dict[str, int]]:
    """data/modelos/nomes_regens.xlsx -> (tabela, código da nação) -> {nome: peso}."""
    import openpyxl

    from .people_contracts import NATION_CODES

    wanted: dict[tuple[str, int], dict[str, int]] = {}
    rows = openpyxl.load_workbook(path, read_only=True)["Nomes"].iter_rows(values_only=True)
    header = [str(h or "") for h in next(rows)]
    col = {h: i for i, h in enumerate(header)}
    for row in rows:
        nation = NATION_CODES.get(str(row[col["nacao"]] or "").strip())
        kind = KINDS.get(str(row[col["tipo"]] or "").strip().casefold())
        text = str(row[col["nome"]] or "").strip()
        if nation is None or kind is None or not text or len(text) > 40:
            continue
        if len(text.split()) > MAX_WORDS[kind]:        # nome completo com no máximo 2 palavras
            continue
        weight = row[col["peso"]]
        weight = int(weight) if str(weight or "").strip().isdigit() else 50
        wanted.setdefault((kind, nation), {})[text] = max(1, min(100, weight))
    return wanted


class Filler:
    """Nome brasileiro de hoje para quem sobra num clube de 2026 com o nome de 2005 (sorteado
    pelos pesos da planilha; o mesmo UID tem sempre o mesmo nome)."""

    NICKNAME_CHANCE = 0.2

    def __init__(self, wanted: dict[tuple[str, int], dict[str, int]], nation: int = 0xBD):
        self.first = wanted.get(("first", nation), {})
        self.second = wanted.get(("second", nation), {})
        self.common = wanted.get(("common", nation), {})

    def __bool__(self) -> bool:
        return bool(self.first and self.second)

    def name(self, uid: int) -> tuple[str, str, str]:
        """(primeiro, comum, sobrenome) para o CHANGE_PLAYER_NAME."""
        import random

        rng = random.Random(uid)

        def pick(weights: dict[str, int]) -> str:
            names = sorted(weights)
            return rng.choices(names, weights=[weights[n] for n in names])[0]

        first, second = pick(self.first), pick(self.second)
        common = pick(self.common) if self.common and rng.random() < self.NICKNAME_CHANCE else ""
        return first, common, second
