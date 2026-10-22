"""Histórico de carreira dos jogadores (aba Histórico): data/db/pl_hist_*.dat.

    pl_hist_index.dat  02 01 "tad." 27 01 00, u32 n, n x (u32 UID da pessoa, u32 bloco),
                       em ordem de UID; o mesmo jogador pode ter vários blocos
    pl_hist_id.dat     02 01 "tad." 01 00 00; por bloco: u32 primeiro, u32 último registro
                       (posições no pl_hist_dt sem o cabeçalho); os blocos vêm em sequência
    pl_hist_dt.dat     02 01 "tad." 01 00 00; registros de 17 bytes:
                       u16 ano do motor, u8 empréstimo, u8 jogos, u8 gols (255 = sem dado),
                       u32 valor da transferência (FFFFFFFF = sem), u32 UID do clube no jogo,
                       u32 posição do próximo (FFFFFFFF = último do bloco)

Conferido na 6.0.2 (181.294 blocos, 747.088 registros): os anos de um bloco crescem e o
jogo junta os blocos do jogador. Vários jogadores têm uma linha de 2005 (a temporada em
que o jogo começa). No ano de um empréstimo só aparece o clube do empréstimo (Saviola,
2004: só o Monaco). O jogo lê os três arquivos no New Game.
"""

from __future__ import annotations

import bisect
import re
import struct
import unicodedata
from collections import Counter
from dataclasses import dataclass

NONE = 0xFFFFFFFF
UNKNOWN = 255
RECORD = 17
_BODY = struct.Struct("<HBBBII")            # o registro sem o "próximo"
LAST_YEAR = 2025                            # última temporada antes da de 2026 (a do jogo)
SOURCE_YEAR = 2026                          # a planilha vai até 20/10/2026: "2019–" chega a 2026
LANG_CLUBS = 0x20                           # seção do lang_db com a tabela de clubes

# nome na planilha -> UID do clube no jogo; None: o clube não existe no banco de 2005
ALIASES = {
    "Porto": 1478, "Porto B": 7000091, "Boavista": 1471,          # os de Portugal, não os do Brasil
    "Racing": 93, "Racing Club": 93,                               # o da Argentina
    "Sporting CP B": 1489, "Sparta Prague": 476, "West Ham United": 735, "Tottenham Hotspur": 728,
    "Zenit Saint Petersburg": 1301108, "Dynamo Moscow": 1520, "Inter Milan": 1135, "Hellas Verona": 2201,
    "PSV Eindhoven": 1028, "Jong Ajax": 856118, "River Plate Montevideo": 1925, "River Plate-PY": 5280414,
    "Liverpool Montevideo": 1920, "Deportes Antofagasta": 130790, "Universidad de San Martín": 8832487,
    "Tiradentes-CE": 310645,
    "Charlotte FC": None, "FC Cincinnati": None, "Krasnodar": None, "Sochi": None, "Neom": None,
    "Orlando City": None, "Orlando City B": None, "New York City FC": None, "Atlanta United": None,
    "Independiente del Valle": None, "Independiente Juniors": None, "Deportivo Sarmiento": None,
    "Red Bull Brasil": None, "Desportivo Brasil": None, "Boa Esporte": None, "Crato": None,
}
# nome na planilha (Wikipédia) -> clube de 2026 (data/brasil/clubes/identidade_fm06.csv)
BRAZIL = {
    "Athletico Paranaense": "Athletico-PR", "Athlético Paranaense": "Athletico-PR",
    "Atlético Paranaense": "Athletico-PR", "Atlético Mineiro": "Atlético-MG", "América Mineiro": "América-MG",
    "Atlético Goianiense": "Atlético-GO", "Sport Recife": "Sport", "Cajazeiras": "Atlético de Cajazeiras",
}
_STOP = {"fc", "cf", "ac", "as", "sc", "cd", "ca", "c", "club", "de", "del", "la", "le", "futbol", "football",
         "calcio", "afc", "sv", "fk", "cfc", "the", "sad", "s", "a", "d"}
_RESERVE = {"b", "ii", "2", "u19", "u21", "u23", "d", "reserves"}


@dataclass(frozen=True)
class Season:
    year: int                   # do motor (ano exibido - 20)
    club: int                   # UID do clube no jogo
    apps: int = UNKNOWN
    goals: int = UNKNOWN
    loan: bool = False
    fee: int = NONE


class History:
    """Os três arquivos; files() grava de novo (sem mudança, byte a byte igual)."""

    def __init__(self, index: bytes, ids: bytes, dt: bytes):
        self.headers = (index[:9], ids[:9], dt[:9])
        count = struct.unpack_from("<I", index, 9)[0]
        if len(index) != 13 + 8 * count or len(ids) != 9 + 8 * count or (len(dt) - 9) % RECORD:
            raise ValueError("pl_hist: tamanhos não batem com a quantidade de blocos")
        self.entries = list(struct.iter_unpack("<II", index[13:]))
        self.blocks = [[dt[9 + at:9 + at + RECORD - 4] for at in range(first, last + RECORD, RECORD)]
                       for first, last in struct.iter_unpack("<II", ids[9:])]
        self._uids = [uid for uid, _ in self.entries]

    def career(self, uid: int) -> list[Season]:
        at, end = bisect.bisect_left(self._uids, uid), bisect.bisect_right(self._uids, uid)
        out = []
        for _, slot in self.entries[at:end]:
            for body in self.blocks[slot]:
                year, loan, apps, goals, fee, club = _BODY.unpack(body)
                out.append(Season(year, club, apps, goals, bool(loan), fee))
        return sorted(out, key=lambda s: s.year)

    def club_refs(self) -> Counter:
        """UID do clube -> quantos registros o citam (o mais citado é o clube grande)."""
        return Counter(_BODY.unpack(body)[5] for block in self.blocks for body in block)

    def replace(self, careers: dict[int, list[Season]]) -> None:
        """Troca a carreira inteira destes jogadores; lista vazia tira o histórico."""
        drop = {slot for uid, slot in self.entries if uid in careers}
        renumber, blocks = {}, []
        for slot, block in enumerate(self.blocks):
            if slot not in drop:
                renumber[slot] = len(blocks)
                blocks.append(block)
        entries = [(uid, renumber[slot]) for uid, slot in self.entries if uid not in careers]
        for uid in sorted(careers):
            seasons = sorted(careers[uid], key=lambda s: s.year)
            if seasons:
                entries.append((uid, len(blocks)))
                blocks.append([_BODY.pack(s.year, int(s.loan), s.apps, s.goals, s.fee, s.club) for s in seasons])
        entries.sort(key=lambda e: e[0])            # estável: os blocos de um UID ficam na ordem
        self.entries, self.blocks = entries, blocks
        self._uids = [uid for uid, _ in entries]

    def files(self) -> tuple[bytes, bytes, bytes]:
        index = bytearray(self.headers[0]) + struct.pack("<I", len(self.entries))
        for entry in self.entries:
            index += struct.pack("<II", *entry)
        ids, dt, at = bytearray(self.headers[1]), bytearray(self.headers[2]), 0
        for block in self.blocks:
            ids += struct.pack("<II", at, at + RECORD * (len(block) - 1))
            for i, body in enumerate(block):
                at += RECORD
                dt += body + struct.pack("<I", at if i < len(block) - 1 else NONE)
        return bytes(index), bytes(ids), bytes(dt)


# ---------------------------------------------------------------- clubes

def _string(data: bytes, at: int) -> tuple[str, int] | None:
    size = struct.unpack_from("<I", data, at)[0]
    end = at + 4 + 2 * size
    if not 1 <= size <= 100 or data[end:end + 2] != b"\0\0":
        return None
    try:
        text = data[at + 4:end].decode("utf-16-le")
    except UnicodeDecodeError:
        return None
    return (text, end + 2) if text.isprintable() else None


def lang_clubs(lang: bytes, start: int, end: int, wanted: set[int]) -> dict[int, tuple[str, str]]:
    """UID -> (nome longo, curto) da tabela de clubes do lang_db: u32 UID, nome longo,
    u8, nome curto (strings u32 n + UTF-16LE + 00 00). Só os UIDs de ``wanted``."""
    found: dict[int, tuple[str, str]] = {}
    for match in re.finditer(rb"(?=[\x01-\x64]\x00\x00\x00)", lang[start:end]):
        at = start + match.start()
        uid = struct.unpack_from("<I", lang, at - 4)[0]
        if uid not in wanted or uid in found:
            continue
        long_name = _string(lang, at)
        if not long_name or lang[long_name[1]] > 3:
            continue
        short_name = _string(lang, long_name[1] + 1)
        if short_name:
            found[uid] = (long_name[0], short_name[0])
    return found


def clean(name: str) -> str:
    """'→ Cruzeiro (loan)' -> 'Cruzeiro'; tira as notas '[es]' da Wikipédia."""
    name = re.sub(r"\[.*?\]", "", name).replace("→", "")
    return re.sub(r"\((loan|empréstimo)\)", "", name, flags=re.I).strip()


def _tokens(name: str) -> list[str]:
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9 ]", " ", plain).split()


def _key(name: str) -> frozenset[str]:
    tokens = _tokens(name)
    return frozenset(t for t in tokens if t not in _STOP) or frozenset(tokens)


class Clubs:
    """Nome de clube da planilha -> UID do clube no jogo."""

    def __init__(self, names: dict[int, tuple[str, str]], refs: Counter, brazil: dict[str, int]):
        self.names, self.refs, self.brazil = names, refs, brazil
        self._by_key: dict[frozenset[str], set[int]] = {}
        for uid, pair in names.items():
            for name in pair:
                self._by_key.setdefault(_key(name), set()).add(uid)

    def find(self, name: str) -> tuple[int | None, str]:
        """(UID ou None, como casou: apelido, brasil, nome, aproximado, sem clube)."""
        name = clean(name)
        if name in ALIASES:
            return ALIASES[name], "apelido"
        if BRAZIL.get(name, name) in self.brazil:
            return self.brazil[BRAZIL.get(name, name)], "brasil"
        uid, how = self._match(name)
        if uid is None:                             # time B, sub-23: o clube principal
            base = re.sub(r"^Jong\s+|\s+(B|II|2|U\d\d)$", "", name)
            if base != name:
                uid, how = self._match(base)
        return uid, how

    def _match(self, name: str) -> tuple[int | None, str]:
        key = _key(name)
        exact = self._by_key.get(key, set())
        if exact:
            return max(exact, key=lambda u: (self.refs[u], -u)), "nome"
        near = {u for other, uids in self._by_key.items() if key < other and not (other - key) & _RESERVE
                for u in uids}
        if near:
            return max(near, key=lambda u: (self.refs[u], -u)), "aproximado"
        return None, "sem clube"


# ---------------------------------------------------------------- carreira

@dataclass(frozen=True)
class Passage:
    start: int
    end: int | None             # None: em aberto ("2019–")
    club: str
    apps: int | None
    goals: int | None
    loan: bool

    @property
    def label(self) -> str:
        return str(self.start) if self.end == self.start else f"{self.start}–{self.end or ''}"


def period(text: str) -> tuple[int, int | None]:
    """'2016–2019' -> (2016, 2019); '2025–' -> (2025, None); '2022' e '2019/20' -> (2022, 2022)."""
    text = str(text).strip()
    match = re.fullmatch(r"(\d{4})\s*[–-]\s*(\d{4})?", text)
    if match:
        return int(match.group(1)), int(match.group(2)) if match.group(2) else None
    match = re.fullmatch(r"(\d{4})(/\d{2})?", text)
    if not match:
        raise ValueError(f"temporada '{text}' fora dos formatos AAAA, AAAA/AA, AAAA–AAAA e AAAA–")
    return int(match.group(1)), int(match.group(1))


def years(passages: list[Passage]) -> list[list[int]]:
    """Anos (do mundo real) de cada passagem; "2019–" vai até SOURCE_YEAR.

    Empréstimo "2020–2021" é uma temporada (2020). No clube dono, o último ano fica para
    a passagem seguinte quando ela começa dentro deste período, e saem os anos dos
    empréstimos que vêm logo abaixo dele."""
    def loan_years(p: Passage) -> range:
        end = p.end or SOURCE_YEAR
        return range(p.start, (end - 1 if end > p.start else p.start) + 1)

    out: list[list[int]] = []
    for i, p in enumerate(passages):
        loans: set[int] = set()
        if p.loan:
            span = list(loan_years(p))
        else:
            last = p.end or SOURCE_YEAR
            following = next((q.start for q in passages[i + 1:] if not q.loan), None)
            if following and p.start < following <= last:
                last -= 1
            span = list(range(p.start, max(p.start, last) + 1))
            for q in passages[i + 1:]:
                if not q.loan:
                    break
                loans.update(loan_years(q))
        if set(span) - loans:
            span = [y for y in span if y not in loans]
        out.append(span)
    return out


def _split(total: int, parts: int) -> list[int]:
    return [total // parts + (1 if i >= parts - total % parts else 0) for i in range(parts)]


def _share(total: int, weights: list[int]) -> list[int]:
    """total repartido como os pesos (maiores restos), ou por igual se os pesos são zero."""
    if not sum(weights):
        return _split(total, len(weights))
    exact = [total * w / sum(weights) for w in weights]
    out = [int(x) for x in exact]
    for i in sorted(range(len(weights)), key=lambda i: out[i] - exact[i])[:total - sum(out)]:
        out[i] += 1
    return out


def seasons(passages: list[Passage], clubs: Clubs, current_club: int, shift: int = -20
            ) -> list[tuple[Passage, int | None, str, list[Season]]]:
    """(passagem, UID do clube, como casou, temporadas do pl_hist) de cada passagem.

    Jogos e gols da passagem repartidos por igual entre os anos dela. Fica de fora a
    temporada de 2025 no clube de 2026 (o jogo começa nela) e o que é depois."""
    out = []
    for passage, span in zip(passages, years(passages)):
        uid, how = clubs.find(passage.club)
        apps = [UNKNOWN] * len(span) if passage.apps is None else [min(254, a) for a in _split(passage.apps, len(span))]
        goals = [UNKNOWN] * len(span) if passage.goals is None else \
            [min(254, g) for g in _share(passage.goals, [0 if a == UNKNOWN else a for a in apps])]
        kept = [Season(y + shift, uid, a, g, passage.loan) for y, a, g in zip(span, apps, goals)
                if y < LAST_YEAR or (y == LAST_YEAR and uid != current_club)]
        out.append((passage, uid, how, kept if uid is not None else []))
    return out


def merge(seasons: list[Season]) -> list[Season]:
    """Junta as linhas do mesmo ano, clube e empréstimo (time B e principal no mesmo clube)."""
    def add(a: int, b: int) -> int:
        return b if a == UNKNOWN else a if b == UNKNOWN else min(254, a + b)

    out: dict[tuple[int, int, bool], Season] = {}
    for s in seasons:
        key = (s.year, s.club, s.loan)
        if key in out:
            old = out[key]
            s = Season(s.year, s.club, add(old.apps, s.apps), add(old.goals, s.goals), s.loan, old.fee)
        out[key] = s
    return sorted(out.values(), key=lambda s: s.year)
