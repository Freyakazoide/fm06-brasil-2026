"""Saldo e público dos clubes no server_db.dat (FM06 6.0.2, banco versão 0x127).

Registro do clube, como o leitor do CLUB (vtable 0x010EFFCC, método 10, 0x00A31C70)
o lê, a partir do byte de tipo (00) antes da nação:

    u8 tipo, u32 nação, u8, texto apelido, u8, texto apelido 2, u8, u8,
    u16 ano de fundação, u32, u8,
    u32 público médio, u32 mínimo, u32 máximo          -> CLUB+0xF0, +0xF4, +0xF8
    u8, u8, u32, u8, u32, u8,
    u8 n + n × u32, u8 m + m × u32,
    u8 tipo de finanças (0 básico, 1 completo), u32 saldo (CLUB_FINANCE+4), ...

Texto: u32 tamanho, UTF-16 e 00 00 (sem o 00 00 quando vazio). O dinheiro do jogo
é em libras; o real vale 5,08 libras no banco (registro "Brazilian Real", "R$").

Os clubes brasileiros têm finanças do tipo básico, e o BOOST_TEAM do .lnc só grava
o caixa no completo (0x00AAD270): por isso o saldo vai direto no banco. O leitor
corrige o público na carga (médio >= 250, mínimo >= 150, máximo >= 5000).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

BRL_PER_GBP = 5.08


@dataclass
class ClubFinance:
    attendance_at: int     # u32 médio, mínimo, máximo
    attendance: tuple[int, int, int]
    finance_type: int
    balance_at: int        # i32 saldo em libras
    balance: int


def _skip_text(data: bytes, at: int) -> int:
    size = struct.unpack_from("<I", data, at)[0]
    if size > 200:
        raise ValueError(f"texto inválido em {at:#x}")
    return at + 4 + 2 * size + (2 if size else 0)


def read(data: bytes, start: int) -> ClubFinance:
    """start: posição do byte de tipo (00) antes da nação do registro do clube."""
    at = start + 1 + 4 + 1
    at = _skip_text(data, at) + 1
    at = _skip_text(data, at) + 2 + 2 + 4 + 1
    attendance_at = at
    attendance = struct.unpack_from("<III", data, at)
    at += 12 + 2 + 4 + 1 + 4 + 1
    for _ in range(2):
        at += 1 + 4 * data[at]
    finance_type = data[at]
    if finance_type not in (0, 1):
        raise ValueError(f"tipo de finanças {finance_type} em {at:#x}")
    return ClubFinance(attendance_at, attendance, finance_type, at + 1, struct.unpack_from("<i", data, at + 1)[0])


def record_start(data: bytes, repo_uid: int, nation: int = 0xBD) -> int:
    """Posição do byte de tipo do registro do clube que server_teams.club_names(repo_uid) lê."""
    needle = struct.pack("<I", repo_uid) + b"\x00" + struct.pack("<I", nation)
    at = data.find(needle, 0, 0x400000)
    if at < 0:
        raise ValueError(f"clube {repo_uid} não achado")
    return at + 4


def apply(data: bytes, changes: dict[int, tuple[int | None, int | None]], into: bytes | None = None) -> bytes:
    """changes: repo_uid -> (saldo em R$, público médio) (None = não muda). Lê as posições em
    `data` (banco original) e grava em `into` (o banco já alterado, do mesmo tamanho)."""
    out = bytearray(data if into is None else into)
    for repo_uid, (balance_brl, average) in changes.items():
        info = read(data, record_start(data, repo_uid))
        if balance_brl is not None:
            struct.pack_into("<i", out, info.balance_at, round(balance_brl / BRL_PER_GBP))
        if average:
            low = max(150, round(average * 0.5))
            high = max(5000, round(average * 2), info.attendance[2])
            struct.pack_into("<III", out, info.attendance_at, max(250, average), low, high)
    return bytes(out)
