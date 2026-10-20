"""Textos do lang_db.dat em português do Brasil (glossário de data/modelos/traducao_ptbr.xlsx).

O lang_db tem uma seção por idioma: no começo do arquivo, u32 quantidade? e a lista
(u32 idioma, u32 posição) a partir de 0x12; o português de Portugal é o idioma 0x13
(0x014AB8CD..0x01795075). Cada texto é u32 tamanho (em caracteres), UTF-16LE, 00 00.

Na seção ficam nomes de clubes e cidades e os textos traduzidos (prêmios, lesões,
fases, descrições de jornal). Só mudam os textos que não aparecem igual em nenhum outro
idioma: nome próprio ("Presidente Prudente (SP)", "Grupo Desportivo de Chaves") é igual
em todos, texto traduzido não. Como em nomes_fases, o arquivo não muda de tamanho: o
texto novo tem de caber no antigo e é completado com espaços.

As frases das telas ("Utilizado num sistema de rotatividade do plantel") não ficam no
lang_db.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass

PORTUGUESE = 0x13
_TEXT = re.compile(rb"([\x01-\xff])\x00\x00\x00((?:[^\x00]\x00|[\x00-\xff][\x01-\xff])+?)\x00\x00", re.S)

# termos do glossário que não servem nos textos do lang_db
SKIP = {
    "partida", "Partida",      # "perna partida" é perna quebrada
    "mão", "Mão",              # "mão partida"; "Primeira Mão" fica com o nomes_fases
    "Marcador", "marcador",    # "Melhor Marcador" é artilheiro (EXTRA), não placar
    "campeonato nacional", "Campeonato nacional",   # vale para todos os países
}
# trocas que o glossário não tem (ou tem com outro sentido), no contexto do lang_db
EXTRA = {
    "Melhor Marcador": "Artilheiro", "Melhores Marcadores": "Artilheiros",
    "melhor marcador": "artilheiro", "melhores marcadores": "artilheiros",
    "Eliminatória": "Fase", "Eliminatórias": "Fases", "eliminatória": "fase",
    "dos Adeptos": "da Torcida",
}
# "equipa" -> "time" muda o gênero: o artigo e o adjetivo antes também mudam
_MASCULINE = {"a": "o", "uma": "um", "da": "do", "na": "no", "pela": "pelo", "à": "ao",
              "antiga": "antigo", "nova": "novo", "esta": "este", "essa": "esse", "sua": "seu",
              "minha": "meu", "nossa": "nosso", "primeira": "primeiro"}
_GENDER_SWAP = {"equipa", "equipas"}


@dataclass
class Change:
    at: int          # posição do texto (depois do u32 tamanho)
    old: str
    new: str


def sections(data: bytes) -> dict[int, tuple[int, int]]:
    """idioma -> (início, fim) da seção."""
    found, at = [], 0x12
    while True:
        language, start = struct.unpack_from("<II", data, at)
        if not 0x50 < start < len(data) or (found and start <= found[-1][1]):
            break
        found.append((language, start))
        at += 8
    ends = [start for _, start in found[1:]] + [len(data)]
    return {language: (start, end) for (language, start), end in zip(found, ends)}


def texts(data: bytes, start: int, end: int) -> list[tuple[int, str]]:
    out = []
    for match in _TEXT.finditer(data, start, end):
        body = match.group(2)
        if len(body) != 2 * match.group(1)[0]:
            continue
        try:
            text = body.decode("utf-16-le")
        except UnicodeDecodeError:
            continue
        if text.isprintable():
            out.append((match.start(2), text))
    return out


def _cased(source: str, target: str) -> str:
    if source.isupper() and len(source) > 1:
        return target.upper()
    if source[:1].isupper():
        return target[:1].upper() + target[1:]
    return target


class Glossary:
    """pt_pt -> pt_br (palavras e expressões, as mais longas primeiro, palavra inteira)."""

    def __init__(self, terms: dict[str, str], short: dict[str, str] | None = None):
        self.terms = {k: v for k, v in terms.items() if k not in SKIP}
        self.terms.update(EXTRA)
        self.short = short or {}
        self.folded = {}
        for key, value in self.terms.items():
            self.folded.setdefault(key.casefold(), value)
        keys = sorted(self.terms, key=len, reverse=True)
        self.pattern = re.compile(r"(?<!\w)(" + "|".join(re.escape(k) for k in keys) + r")(?!\w)", re.I)

    def _value(self, found: str, short: bool) -> str:
        if found in self.terms:
            value = self.terms[found]
            key = found
        else:
            value = _cased(found, self.folded[found.casefold()])
            key = next((k for k in self.terms if k.casefold() == found.casefold()), found)
        if short and key in self.short:
            return _cased(found, self.short[key])
        return value

    def translate(self, text: str, short: bool = False) -> str | None:
        """Texto traduzido, ou None se não dá para traduzir com segurança."""
        pieces, last = [], 0
        for match in self.pattern.finditer(text):
            found = match.group(1)
            word = found.casefold()
            new = self._value(found, short)
            before = text[last:match.start()]
            if word in _GENDER_SWAP:
                if text[match.end():].startswith(" <%"):        # adjetivo de nacionalidade no feminino
                    return None
                head = re.search(r"(\w+)(\s+)$", before)
                if head and head.group(1).casefold() in _MASCULINE:
                    before = (before[:head.start()] + _cased(head.group(1), _MASCULINE[head.group(1).casefold()])
                              + head.group(2))
            pieces += [before, new]
            last = match.end()
        if not pieces:
            return text
        return "".join(pieces) + text[last:]


def plan(data: bytes, glossary: Glossary, phrases: dict[str, str] | None = None) -> tuple[list[Change], list[str]]:
    """Textos a trocar e os que não couberam."""
    phrases = phrases or {}
    bounds = sections(data)
    others: set[str] = set()
    for language, (start, end) in bounds.items():
        if language != PORTUGUESE:
            others.update(text for _, text in texts(data, start, end))
    changes, too_long = [], []
    for at, old in texts(data, *bounds[PORTUGUESE]):
        if old in others:
            continue
        new = phrases.get(old) or glossary.translate(old)
        if new is None or new == old:
            continue
        if len(new) > len(old):
            new = glossary.translate(old, short=True)
            if new is None or new == old:
                continue
            if len(new) > len(old):
                too_long.append(f"{old} -> {new}")
                continue
        changes.append(Change(at, old, new))
    return changes, too_long


def apply(data: bytes, changes: list[Change]) -> bytes:
    out = bytearray(data)
    for change in changes:
        out[change.at:change.at + 2 * len(change.old)] = change.new.ljust(len(change.old)).encode("utf-16-le")
    return bytes(out)


def load_sheet(path) -> tuple[Glossary, dict[str, str]]:
    import openpyxl

    book = openpyxl.load_workbook(path, read_only=True)
    terms, short = {}, {}
    for row in book["Glossario"].iter_rows(min_row=2, values_only=True):
        pt_pt, pt_br = (row[0] or "").strip(), (row[1] or "").strip()
        if pt_pt and pt_br:
            terms[pt_pt] = pt_br
            if row[4] and str(row[4]).strip():
                short[pt_pt] = str(row[4]).strip()
    phrases = {}
    for row in book["Frases"].iter_rows(min_row=2, values_only=True):
        old, new = (row[1] or "").strip(), (row[2] or "").strip()
        if old and new:
            phrases[old] = new
    return Glossary(terms, short), phrases
