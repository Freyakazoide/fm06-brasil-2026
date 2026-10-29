"""Contrato de patrocínio de 2026 no registro do clube (server_db.dat), ficha C1b.

O leitor do CLUB (0x00A31C70), logo depois das finanças básicas (financas.py: tipo, saldo,
u8, u32, DATE), lê um u32 para CLUB+0x11C. Se não for 0, lê o contrato (0x00AAED20):

    u32 0, u32 valor por temporada (£), DATE fim (u16 dia do ano a partir de 0, u16 ano), u8 anos

No banco original o u32 é 0 em todos os clubes e o New Game gera o contrato (0x00A29130,
só quando CLUB+0x11C está vazio). Na renovação o jogo gera outro pela reputação do clube
(0x00A7E410). O jogo mostra o ano + 20 (year_shift −20 do mod): fim em 2028 vai como 2008.

Gravar o contrato troca o u32 por 1 e insere 13 bytes: o arquivo cresce. Por isso as
posições são lidas no banco já alterado e a inserção vai do fim para o começo.

O jogo só paga o patrocínio no fechamento do ano (método 0xF0 das finanças, 0x008AA580,
chamado por 0x006D0870 no evento 9 do calendário da nação), já para a temporada seguinte:
a 1ª temporada do save ficava sem. O patch `patrocinio_inicio` (exe_swaps) paga uma vez no
init das finanças do New Game (0x00A87170): o jne + call do gerador (0x00A872E9) vira uma
chamada a um desvio que faz o mesmo teste, cria o contrato se faltar e paga o valor pelo
método 0xA0 (0x00A7C8D0, o mesmo do fechamento: saldo e linha "Patrocínio"). O init roda
duas vezes no mesmo clube no New Game (vigia_orcamento, 27/10); o desvio só paga com
FINANCE+0x7C ainda 0 (zerado no construtor e somado pelo próprio 0xA0).
"""

from __future__ import annotations

import datetime as dt
import struct
from dataclasses import dataclass

from . import financas
from .exe_cave import SECTION_VA, Asm, off, sec_off, section_swaps

YEAR_SHIFT = -20
_CONTRACT = struct.Struct("<IIHHB")


@dataclass(frozen=True)
class Contract:
    value_brl: float
    end: dt.date
    years: int

    def pack(self) -> bytes:
        end = _shift(self.end)
        return _CONTRACT.pack(0, round(self.value_brl / financas.BRL_PER_GBP),
                              end.timetuple().tm_yday - 1, end.year, self.years)


def _shift(date: dt.date) -> dt.date:
    try:
        return date.replace(year=date.year + YEAR_SHIFT)
    except ValueError:                    # 29/2
        return date.replace(year=date.year + YEAR_SHIFT, day=28)


def flag_at(data: bytes, repo_uid: int) -> int:
    """Posição do u32 que diz se o clube traz contrato (logo depois das finanças)."""
    info = financas.read(data, financas.record_start(data, repo_uid))
    if info.finance_type != 0:
        raise ValueError(f"clube {repo_uid}: finanças completas, formato não conferido")
    return info.balance_at + 4 + 1 + 4 + 4


def apply(data: bytes, contracts: dict[int, Contract]) -> tuple[bytes, list[int]]:
    """contracts: repo_uid -> contrato. Devolve o banco novo e os clubes que já tinham contrato
    (ficam como estão)."""
    places, kept = [], []
    for repo_uid, contract in contracts.items():
        at = flag_at(data, repo_uid)
        if struct.unpack_from("<I", data, at)[0]:
            kept.append(repo_uid)
        else:
            places.append((at, contract))
    out = bytearray(data)
    for at, contract in sorted(places, key=lambda p: p[0], reverse=True):
        out[at:at + 4] = struct.pack("<I", 1) + contract.pack()
    return bytes(out), kept


def _date(value) -> dt.date | None:
    if value in (None, ""):
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    text = str(value).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"data inválida: {value}")


def load_sheet(path) -> dict[str, Contract]:
    """Aba Contrato_jogo -> clube de 2026: contrato (só as linhas com valor e fim)."""
    import openpyxl

    rows = openpyxl.load_workbook(path, read_only=True, data_only=True)["Contrato_jogo"].iter_rows(values_only=True)
    header = [str(h or "").strip() for h in next(rows)]
    out = {}
    for values in rows:
        row = dict(zip(header, values))
        club = str(row.get("clube") or "").strip()
        value, end = row.get("valor_anual_brl"), _date(row.get("fim"))
        if not club or value in (None, "") or end is None:
            continue
        start = _date(row.get("inicio")) or dt.date(2026, 1, 1)
        if end <= start:
            raise ValueError(f"{club}: fim {end} antes do início {start}")
        out[club] = Contract(float(value), end, max(1, round((end - start).days / 365.25)))
    return out


INIT_SPONSOR_CHECK = 0x00A872E9       # jne +5 ; call 0x00A29130 (gera o contrato se faltar)
GENERATE = 0x00A29130
PAY = 0x00A7C8D0                      # FINANCE método 0xA0 (thiscall, valor)
PAY_STUB = SECTION_VA + 0x6000


def _pay_stub() -> bytes:
    a = Asm(PAY_STUB)                                # ecx = clube, esi = finanças
    a.raw(bytes.fromhex("83B91C01000000"))           # cmp dword [ecx+0x11C], 0
    a.raw(bytes.fromhex("7505"))                     # jne tem
    a.call(GENERATE)
    a.raw(bytes.fromhex("8B4608"))                   # tem: mov eax, [esi+8]
    a.raw(bytes.fromhex("8B801C010000"))             # mov eax, [eax+0x11C]
    a.raw(bytes.fromhex("85C07410"))                 # test eax, eax ; je fim
    a.raw(bytes.fromhex("837E7C00"))                 # cmp dword [esi+0x7C], 0
    a.raw(bytes.fromhex("750A"))                     # jne fim (já pago)
    a.raw(bytes.fromhex("FF7004"))                   # push dword [eax+4] (valor)
    a.raw(bytes.fromhex("8BCE"))                     # mov ecx, esi
    a.call(PAY)
    a.raw(bytes.fromhex("C3"))                       # fim: ret
    return bytes(a.code)


def exe_swaps(data: bytes):
    from .exe_patches import Swap

    code = _pay_stub()
    call = bytes.fromhex("E8") + struct.pack("<i", PAY_STUB - (INIT_SPONSOR_CHECK + 5)) + bytes.fromhex("9090")
    return (*section_swaps(data),
            Swap(sec_off(PAY_STUB), bytes(len(code)), code),
            Swap(off(INIT_SPONSOR_CHECK), bytes.fromhex("7505e8401efaff"), call))
