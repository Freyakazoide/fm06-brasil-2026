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
import dataclasses
import datetime as dt
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
EUR_PER_GBP = 1.17                          # o dinheiro do banco é em libras (financas.BRL_PER_GBP)

# nome na planilha -> UID do clube no jogo; None: o clube não existe no banco de 2005
ALIASES = {
    "Porto": 1478, "Porto B": 7000091, "Boavista": 1471,          # os de Portugal, não os do Brasil
    "Racing": 93, "Racing Club": 93,                               # o da Argentina
    "Sporting CP B": 1489, "Sparta Prague": 476, "West Ham United": 735, "Tottenham Hotspur": 728,
    "Zenit Saint Petersburg": 1301108, "Dynamo Moscow": 1520, "Inter Milan": 1135, "Hellas Verona": 2201,
    "PSV Eindhoven": 1028, "Jong Ajax": 856118, "River Plate Montevideo": 1925, "River Plate-PY": 5280414,
    "Liverpool Montevideo": 1920, "Deportes Antofagasta": 130790, "Universidad de San Martín": 8832487,
    "Tiradentes-CE": 310645,
    # nomes do Sofascore (carreiras_2026.csv) que o nome do banco não acha
    "Vitória SC": 1494, "Vitória de Setúbal": 1495, "CS Marítimo": 1476, "UD Oliveirense": 2416,
    "SC Covilhã": 2395, "Louletano DC": 2446, "Académico Viseu FC": 2388, "UD Vilafranquense": 2480,
    "UD Santarém": 2471, "AD Sanjoanense": 2428, "CF Estrela Amadora": 1473, "CF Estrela Sad": 1473,
    "LA Galaxy": 1907, "Whitecaps FC": 4400014, "Kyoto Sanga FC": 1192, "Nagoya Grampus": 1191,
    "JEF United Chiba": 1187, "Wolverhampton": 740, "Levante UD": 1717, "UD Las Palmas": 1772,
    "Rayo Vallecano": 1729, "Stade de Reims": 2047, "Independiente Rivadavia": 3101453, "LDU": 5270338,
    "LDU Quito": 5270338, "Neftçi PFK": 167, "Lommel SK": 269, "Botev Vratsa": 138442, "SSC Napoli": 1150,
    "Makedonija Gjorce Petrov": 116192, "River Plate UY": 1925, "Flamengo de Arcoverde": 309771,
    "SER Santo Ângelo": 301282, "Artsul-RJ": 2100850, "Mineiros-GO": 2111642, "Aparecida-GO": 301149,
    "Patrocinense-MG": 310901, "ASSU-RN": 309633, "Tupan-MA": 313785, "Ipanema-AL": 314684,
    "EC União Suzano": 2114007, "Porto Alegre-RS": 314778,
    "Olympique Lyonnais": 865, "Olympique de Marseille": 866, "Club Atlético Peñarol": 1922,
    "Barcelona SC Guayaquil": 109180, "Red Bull Salzburg": 158, "Dynamo Kyiv": 1885, "Olympiacos FC": 981,
    "Junior Barranquilla": 419, "Club Atletico Colón": 102462, "Independiente Medellín": 425,
    "Atlético Madrileño": 1666, "Barcelona Atlètic": 1668, "SL Benfica": 1487, "SL Benfica B": 7000095,
    "Leicester City": 673, "Birmingham City": 609, "Zenit St. Petersburg": 1301108, "Club Atlético Belgrano": 81,
    "Royal Antwerp FC": 262, "HNK Hajduk Split": 433, "FK Crvena zvezda": 1955,
    "Club Atlético Unión de Santa Fe": 102467, "Pumas UNAM": 1260, "Tigres UANL": 104360,
    "Club Atlético Platense": 92, "Quilmes Atlético Club": 102487, "Club Atlético Chacarita Juniors": 102493,
    "Aris Thessaloniki": 969, "US Salernitana 1919": 1166, "Al-Qadsiah": 1104149, "Al-Ettifaq": 135427,
    "Akhmat Grozny": 477632, "Zoria Luhansk": 1902, "Suwon Samsung Bluewings": 106813,
    "Jeonbuk Hyundai Motors": 130776, "Ulsan HD": 106808, "Hokkaido Consadole Sapporo": 107285,
    "Shandong Taishan": 116403, "Jeju SK": 106817, "Jeonnam Dragons": 106812, "Daejeon Hana Citizen": 130774,
    "Liverpool UY": 1920, "Nacional": 1921, "Nacional Reserve": 1921, "Kasımpaşa": 130360,
    "Hapoel Be'er Sheva": 1085, "Koninklijke Lierse Sportkring": 268, "K. Beerschot V.A.": 176,
    "AOK Kerkyra": 676510, "ETO FC Győr": 1054, "JFK Ventspils": 483868, "KF Bylis": 1300042,
    "MKS Odra Wodzisław Śląski": 1300877, "Al-Gharafa": 1026831, "Al-Jazira": 135450,
    "Montevideo Wanderers": 1926, "Club Atlético Lanús": 90, "Godoy Cruz": 102491,
    "FC Setúbal": None, "Capital FC": None, "Majd FC": None, "Tocantins": None, "Bandeirante FC": None,
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
    "Atlético-PR": "Athletico-PR", "Bragantino": "Red Bull Bragantino",
}
_STOP = {"fc", "cf", "ac", "as", "sc", "cd", "ca", "c", "club", "de", "del", "la", "le", "futbol", "football",
         "calcio", "afc", "sv", "fk", "cfc", "the", "sad", "s", "a", "d"}
_RESERVE = {"b", "ii", "2", "u19", "u21", "u23", "d", "reserves"}
_UF = {"AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR",
       "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"}
# o que o nome do banco pode ter a mais numa aproximação: forma jurídica, artigo, número
_GENERIC = _STOP | {"futebol", "clube", "sport", "balompie", "sa", "kp", "rks", "csd", "adc", "fk", "ofk", "ks", "sk",
                    "k", "aa", "ec", "ge", "se", "ad", "da", "do", "dos", "das", "e", "and", "associacao", "real",
                    "desportivo", "desportiva", "deportivo", "al", "1"}


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


def lang_clubs(lang: bytes, start: int, end: int, wanted: set[int] | None = None) -> dict[int, tuple[str, str]]:
    """UID -> (nome longo, curto) da tabela de clubes do lang_db: u32 UID, nome longo,
    u8, nome curto (strings u32 n + UTF-16LE + 00 00). Só os UIDs de ``wanted`` (todos se None)."""
    found: dict[int, tuple[str, str]] = {}
    for match in re.finditer(rb"(?=[\x01-\x64]\x00\x00\x00)", lang[start:end]):
        at = start + match.start()
        uid = struct.unpack_from("<I", lang, at - 4)[0]
        if (wanted is not None and uid not in wanted) or uid in found:
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


def _generic(extra: frozenset[str]) -> bool:
    """Tokens que o nome do banco tem a mais e não mudam o clube ("SAD", "Futebol Clube",
    "04"); time B nunca."""
    return not extra & _RESERVE and all(t in _GENERIC or len(t) == 1 or any(c.isdigit() for c in t) for t in extra)


class Clubs:
    """Nome de clube da planilha -> UID do clube no jogo.

    Os clubes de 2026 (``brazil``) só casam pelo nome de 2026 (ou por BRAZIL): por
    aproximação, "Paulista" acharia o "SC Corinthians Paulista". Com ``strict`` (nomes do
    Sofascore, em que o clube de 2026 já vem com o nome de 2026) também não pelo nome do
    banco: "Vitória SC" é o de Guimarães, não o Vitória. Pelo nome exato, qualquer clube
    de ``names``; por aproximação (o nome do banco com "SAD", "Futebol Clube", número ou
    país a mais: "Real Betis Balompié S.A.D.", "Al Hilal (KSA)"), só os que já aparecem no
    histórico de 2005 (``refs``): entre os 21 mil do banco, um nome curto acharia um
    homônimo de outro país."""

    def __init__(self, names: dict[int, tuple[str, str]], refs: Counter, brazil: dict[str, int],
                 strict: bool = False):
        self.names, self.refs, self.brazil = names, refs, brazil
        own = set(brazil.values())
        self._by_key: dict[frozenset[str], set[int]] = {}
        self._near: dict[frozenset[str], set[int]] = {}
        self._found: dict[str, tuple[int | None, str]] = {}
        for uid, pair in names.items():
            for name in pair:
                if not (strict and uid in own):
                    self._by_key.setdefault(_key(name), set()).add(uid)
                if refs[uid] and uid not in own:      # sem o país entre parênteses: "Al Hilal (KSA)"
                    self._near.setdefault(_key(re.sub(r"\(.*?\)", "", name)), set()).add(uid)

    def find(self, name: str) -> tuple[int | None, str]:
        """(UID ou None, como casou: apelido, brasil, nome, aproximado, sem clube)."""
        if name not in self._found:
            self._found[name] = self._find(name)
        return self._found[name]

    def _find(self, name: str) -> tuple[int | None, str]:
        name = clean(name)
        if name in ALIASES:
            return ALIASES[name], "apelido"
        if BRAZIL.get(name, name) in self.brazil:
            return self.brazil[BRAZIL.get(name, name)], "brasil"
        key = _key(name)
        exact = self._by_key.get(key, set())
        if exact:
            return self._best(exact), "nome"
        state = re.fullmatch(r"(.+?)\s*[-(]\s*([A-Z]{2})\)?", name)
        if state and state.group(2) in _UF:         # "Flamengo-PI": o "Flamengo (PI)" do banco
            exact = self._by_key.get(_key(f"{state.group(1)} ({state.group(2)})"), set())
            return (self._best(exact), "nome") if exact else (None, "sem clube")
        base = re.sub(r"^Jong\s+|\s+(B|II|2|U\d\d|Sub-?\d\d|Reserves?)$", "", name)
        if base != name:                            # time B, sub-20: o clube principal
            return self.find(base)
        near = {u for other, uids in self._near.items() if key <= other and _generic(other - key) for u in uids} \
            if any(len(t) >= 3 for t in key) else set()       # "FC A&N" não aproxima
        if near:
            return self._best(near), "aproximado"
        return None, "sem clube"

    def _best(self, uids: set[int]) -> int:
        return max(uids, key=lambda u: (self.refs[u], -u))     # o mais citado no histórico de 2005


# ---------------------------------------------------------------- carreira

@dataclass(frozen=True)
class Passage:
    start: int
    end: int | None             # None: em aberto ("2019–")
    club: str
    apps: int | None
    goals: int | None
    loan: bool
    fee: int | None = None      # euros pagos para chegar (vai no último ano do clube anterior)

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
    previous = None                                 # valor da venda no último ano do clube que vendeu
    for passage, _, _, kept in out:
        if passage.loan:
            continue
        if passage.fee and previous and previous[-1].year <= passage.start + shift:
            previous[-1] = dataclasses.replace(previous[-1], fee=min(NONE - 1, round(passage.fee / EUR_PER_GBP)))
        if kept:
            previous = kept
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
            s = Season(s.year, s.club, add(old.apps, s.apps), add(old.goals, s.goals), s.loan,
                       old.fee if old.fee != NONE else s.fee)
        out[key] = s
    return sorted(out.values(), key=lambda s: s.year)


# ---------------------------------------------------------------- transferências (Sofascore)

NO_CLUB = {"No team", "Retired", "Without club", "Unknown"}
_YOUTH = re.compile(r"\s(U\d\d|Sub-?\d\d|B|II|Youth|Juniors?)$", re.I)


@dataclass(frozen=True)
class Transfer:
    date: dt.date
    origin: str | None          # clube de onde saiu
    to: str | None              # clube para onde foi
    kind: int                   # Sofascore: 3 transferência, 1 empréstimo, 2 volta do empréstimo,
                                # 7 chegou sem clube, 6 saiu para "sem clube", 4 aposentou
    fee: int | None = None      # euros


def passages_from_transfers(transfers: list[Transfer]) -> list[Passage]:
    """Passagens (como as da historico_carreira.xlsx) a partir das transferências.

    Cada transferência abre uma passagem no clube de destino no ano dela; a seguinte a
    fecha. Empréstimo fica logo abaixo do clube dono (years() tira os anos dele do dono);
    a volta do empréstimo só fecha o empréstimo, e uma nova transferência para o mesmo
    clube continua a passagem. O clube de origem da primeira entra com um ano (o anterior,
    se a saída foi no 1º semestre), menos quando é a base (sub-20)."""
    transfers = sorted(transfers, key=lambda t: t.date)
    out: list[dict] = []
    parent = loan = None

    def close(item, year):
        if item is not None and item["end"] is None:
            item["end"] = year

    if transfers and transfers[0].origin and transfers[0].origin not in NO_CLUB \
            and not _YOUTH.search(transfers[0].origin):
        first = transfers[0].date
        parent = {"club": transfers[0].origin, "start": first.year - (first.month <= 6), "end": None,
                  "loan": False, "fee": None}
        out.append(parent)
    for t in transfers:
        year = t.date.year
        if not t.to or t.to in NO_CLUB:
            close(loan, year)
            close(parent, year)
            parent = loan = None
            continue
        if t.kind == 1:                              # empréstimo
            close(loan, year)
            loan = {"club": t.to, "start": year, "end": None, "loan": True, "fee": None}
            out.append(loan)
            continue
        if t.kind == 2 and parent is not None and t.to == parent["club"]:
            close(loan, year)                        # voltou para o clube dono
            loan = None
            continue
        close(loan, year)
        close(parent, year)
        loan = None
        fee = t.fee if t.kind == 3 else None
        if parent is not None and parent["club"] == t.to and parent["end"] == year:
            parent["end"], parent["fee"] = None, parent["fee"] or fee   # renovou ou comprou: a mesma passagem
            continue
        parent = {"club": t.to, "start": year, "end": None, "loan": False, "fee": fee}
        out.append(parent)
    return [Passage(p["start"], p["end"], p["club"], None, None, p["loan"], p["fee"] or None) for p in out]
