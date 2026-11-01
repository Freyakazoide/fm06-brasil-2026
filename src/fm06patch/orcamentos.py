"""Orçamento de transferências dos clubes no New Game (tabela do FINANCE_MANAGER no server_db.dat).

As finanças dos clubes no banco são do tipo básico e não guardam orçamento: no New Game o
jogo troca pelas completas e calcula o orçamento (ficha C5b). Logo depois,
FINANCE_MANAGER::setup() (0x006D4400) percorre uma tabela do banco e, para cada registro,
chama a troca das finanças do clube, cria o empréstimo (0x006CF960) e grava o orçamento de
transferências fixo por cima do calculado (0x006D45A1, CLUB_FINANCE+0x1C). Conferido com
depurador no New Game de 27/10: o init deu £5.590.221 ao Flamengo e o setup gravou £50.000,
o valor do registro do Flamengo.

A tabela (0x13D8555 no banco original): u32 quantidade (3.536) e registros de 24 bytes

    u8, u32 time, u32 empréstimo (£), u16 meses, u32 orçamento de transferências (£),
    u8 tipo do empréstimo, u32 índice do registro, u32 FFFFFFFF

O "time" é o índice do registro do time do clube (o u32 antes do UID do clube e do 0A 00 do
registro do time, mais 1): Corinthians 287, Flamengo 290, Chelsea 544 (£100 mi).
O setup só considera registros com time e com empréstimo ou orçamento; um clube pode ter
dois (orçamento num, empréstimo noutro, como o Flamengo) e o setup trata os dois campos no
mesmo registro. Por isso um clube sem registro ganha o registro que sobra quando os dois de
outro clube da planilha viram um só; o arquivo não muda de tamanho e nenhum clube fora da
planilha muda.

Empréstimos de 2005 (ficha C5b, 31/10): o setup só cria o empréstimo se o valor do registro
não for 0 (0x006D4569, `test ebx, ebx ; je`). clear_loans zera valor e prazo nos registros
dos clubes brasileiros; o orçamento do mesmo registro continua valendo.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, replace

from . import server_teams
from .exe_cave import SECTION_VA, Asm, off, sec_off, section_swaps
from .financas import BRL_PER_GBP

RECORD = 24
_DATA = struct.Struct("<BIIHIB")      # 16 bytes antes do índice


@dataclass(frozen=True)
class Entry:
    at: int          # início do registro (o u8)
    flag: int
    team: int
    loan: int        # £
    months: int
    budget: int      # £
    kind: int

    def pack(self) -> bytes:
        return _DATA.pack(self.flag, self.team, self.loan, self.months, self.budget, self.kind)


def _valid(data: bytes, count_at: int) -> bool:
    count = struct.unpack_from("<I", data, count_at)[0]
    if not 100 <= count <= 100_000 or count_at + 4 + RECORD * count > len(data):
        return False
    return all(struct.unpack_from("<Ii", data, count_at + 4 + RECORD * i + 16) == (i, -1)
               for i in (0, 1, count // 2, count - 1))


def locate(data: bytes) -> int:
    """Posição do u32 quantidade da tabela."""
    needle = struct.pack("<Ii", 0, -1)
    at = data.find(needle)
    while at >= 0:
        if at >= 20 and _valid(data, at - 20):
            return at - 20
        at = data.find(needle, at + 1)
    raise ValueError("tabela de orçamentos do FINANCE_MANAGER não achada")


def entries(data: bytes) -> list[Entry]:
    count_at = locate(data)
    count = struct.unpack_from("<I", data, count_at)[0]
    return [Entry(at, *_DATA.unpack_from(data, at))
            for at in (count_at + 4 + RECORD * i for i in range(count))]


def team_index(data: bytes, repo_uid: int) -> int | None:
    """Índice do registro do time do clube (o número que a tabela usa)."""
    rec = server_teams._team_record(data, repo_uid)
    return None if rec is None else struct.unpack_from("<I", data, rec - 8)[0] + 1


@dataclass
class Plan:
    changes: list[Entry]
    lines: list[str]
    missing: list[int]      # repo_uid sem time no banco ou sem registro livre


def plan(data: bytes, budgets: dict[int, float]) -> Plan:
    """budgets: repo_uid -> orçamento de transferências em R$."""
    table = entries(data)
    by_team: dict[int, list[Entry]] = {}
    for entry in table:
        by_team.setdefault(entry.team, []).append(entry)
    changed: dict[int, Entry] = {}
    free: list[Entry] = []
    waiting: list[tuple[int, int, int]] = []
    lines, missing = [], []
    for repo_uid, brl in budgets.items():
        team = team_index(data, repo_uid)
        if team is None:
            missing.append(repo_uid)
            continue
        value = round(brl / BRL_PER_GBP)
        mine = by_team.get(team, [])
        if not mine:
            waiting.append((repo_uid, team, value))
            continue
        keep = next((e for e in mine if e.loan), mine[0])
        changed[keep.at] = replace(keep, budget=value)
        old = max(e.budget for e in mine)
        for entry in mine:
            if entry is not keep:
                changed[entry.at] = replace(entry, budget=0)
                if not entry.loan:                  # sobra zerado: o setup pula
                    free.append(entry)
        lines.append(f"{repo_uid}: time {team}, £{old:,} -> £{value:,}")
    for repo_uid, team, value in waiting:
        if not free:
            missing.append(repo_uid)
            continue
        entry = free.pop(0)
        changed[entry.at] = Entry(entry.at, 0, team, 0, 0, value, 0)
        lines.append(f"{repo_uid}: time {team}, sem registro -> £{value:,} (registro {entry.at:#x})")
    return Plan(sorted(changed.values(), key=lambda e: e.at), lines, missing)


def apply(data: bytes, changes: list[Entry], into: bytes | None = None) -> bytes:
    """Grava os registros (posições lidas em ``data``) em ``into`` (mesmo tamanho)."""
    out = bytearray(data if into is None else into)
    for entry in changes:
        out[entry.at:entry.at + _DATA.size] = entry.pack()
    return bytes(out)


def clear_loans(db: bytes, teams: set[int]) -> tuple[bytes, list[Entry]]:
    """Zera empréstimo e prazo dos registros desses times (lidos em ``db``, já com o orçamento).
    Devolve o banco e os registros como ficaram."""
    cleared = [replace(e, loan=0, months=0) for e in entries(db) if e.team in teams and e.loan]
    return apply(db, cleared), cleared


def load_sheet(path) -> dict[str, float]:
    """Aba Estrutura -> clube de 2026: orçamento de contratações em R$ (só os preenchidos)."""
    import openpyxl

    rows = openpyxl.load_workbook(path, read_only=True, data_only=True)["Estrutura"].iter_rows(values_only=True)
    header = [str(h or "").strip() for h in next(rows)]
    out = {}
    for values in rows:
        row = dict(zip(header, values))
        club = str(row.get("clube") or "").strip()
        value = row.get("orcamento_contratacoes_brl")
        if club and value not in (None, ""):
            out[club] = float(value)
    return out


# Orçamento salarial (ficha C5b). O init das finanças completas (0x00A87170) e a posse do
# técnico (0x006F4F4C) gravam em +0x88 o que o método 0xC8 devolve (0x008AB710, fórmula com a
# reputação do clube e da nação); ninguém chama a fórmula direto, só pelas vtables (finanças
# completas 0x010EFE14: ponteiro em 0x010EFEDC). No New Game de 27/10 o Flamengo ficou com
# £413.803/sem de orçamento para £520.578/sem de folha (+0x90). O patch troca esse ponteiro
# por um desvio que chama a fórmula e devolve o maior entre ela e a folha + 10%.
WAGE_FORMULA = 0x008AB710
WAGE_SLOT_AT = 0x010EFEDC           # vtable das finanças completas + 0xC8
WAGE_STUB = SECTION_VA + 0x6300
PAYROLL = 0x90                      # folha semanal (£), conferida com a tela
WAGE_MARGIN = 11                    # folha × 11 / 10


def _wage_stub() -> bytes:
    a = Asm(WAGE_STUB)
    a.raw(bytes.fromhex("56" "8BF1" "FF742408"))            # push esi ; mov esi, ecx ; push [esp+8]
    a.call(WAGE_FORMULA)                                    # eax = fórmula
    a.raw(bytes.fromhex("50" "8B86") + struct.pack("<I", PAYROLL)   # push eax ; mov eax, [esi+0x90]
          + bytes.fromhex("6BC0") + bytes([WAGE_MARGIN])            # imul eax, eax, 11
          + bytes.fromhex("33D2" "B90A000000" "F7F1" "8BC8" "58")   # eax / 10 -> ecx ; pop eax
          + bytes.fromhex("3BC1" "7D02" "8BC1" "5E" "C20400"))      # eax = max(eax, ecx) ; ret 4
    return bytes(a.code)


def wage_swaps(data: bytes):
    from .exe_patches import Swap

    code = _wage_stub()
    return (*section_swaps(data),
            Swap(off(WAGE_SLOT_AT), struct.pack("<I", WAGE_FORMULA), struct.pack("<I", WAGE_STUB)),
            Swap(sec_off(WAGE_STUB), bytes(len(code)), code))
