"""CT e base dos clubes (aba Estrutura da clubes_estrutura_2026.xlsx) no server_db.dat.

No registro do clube (financas.py), o leitor do CLUB (0x00A31C70) lê:

    ... texto apelido 2, u8 -> CLUB+0xE0, u8 -> CLUB+0xE1, u16 ano de fundação, u32, u8,
    u32 público médio, mínimo, máximo, u8 -> CLUB+0xEB, u8 (bits), ...

As três são notas de 1 a 20; fora disso o leitor põe uma pelo público médio (Manchester
United 20/20/20, Chesterfield 7/8/5 no banco da SI):

- CLUB+0xEB, o CT ("Facilities" no FMM): 0x00A29940 tira dele a frase da tela de
  instalações (acima de 15 "Top facilities plus youth academy", acima de 12 "Good",
  acima de 9 "Average"...); a diretoria que aceita melhorar as instalações sobe ele
  primeiro (0x00A80D40, 0x00A289A0) e o que passa de 20 vai para os outros dois;
- CLUB+0xE1, a base: entra na qualidade dos juniores que sobem (0x0076EEA5: metade da
  nota + 10 como faixa do sorteio);
- CLUB+0xE0, a captação: soma com a reputação e o nível da divisão na conta que decide
  se o clube recebe juniores (0x0076D9DF: até 10, nenhum).

Numa rotina do começo do jogo (0x009F75F0) as duas da base ficam limitadas a reputação do
time / 250 (reputação 4.000: no máximo 16). Por isso o script avisa quando a nota da
planilha passa disso.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from . import financas


@dataclass(frozen=True)
class Facilities:
    training_at: int        # CLUB+0xEB
    youth_at: int           # CLUB+0xE1
    recruitment_at: int     # CLUB+0xE0
    training: int
    youth: int
    recruitment: int


def read(data: bytes, start: int) -> Facilities:
    """start: o byte de tipo do registro do clube (financas.record_start)."""
    attendance_at = financas.read(data, start).attendance_at
    recruitment_at, youth_at, training_at = attendance_at - 9, attendance_at - 8, attendance_at + 12
    return Facilities(training_at, youth_at, recruitment_at, data[training_at], data[youth_at], data[recruitment_at])


def rating(value) -> int | None:
    """Nota 1-20 da planilha (branco: não muda)."""
    text = str(value if value is not None else "").strip()
    if not text:
        return None
    number = round(float(text.replace(",", ".")))
    if not 1 <= number <= 20:
        raise ValueError(f"nota {value} fora de 1-20")
    return number


def load_sheet(path) -> dict[str, tuple[int | None, int | None, int | None]]:
    """Aba Estrutura -> clube de 2026: (CT, base, captação)."""
    import openpyxl

    rows = openpyxl.load_workbook(path, read_only=True)["Estrutura"].iter_rows(values_only=True)
    header = [str(h or "").strip() for h in next(rows)]
    out = {}
    for values in rows:
        row = dict(zip(header, values))
        club = str(row.get("clube") or "").strip()
        if club:
            out[club] = (rating(row.get("ct")), rating(row.get("base_instalacoes")),
                         rating(row.get("base_recrutamento")))
    return out


def apply(data: bytes, changes: dict[int, tuple[int | None, int | None, int | None]],
          into: bytes | None = None) -> bytes:
    """changes: repo_uid -> (CT, base, captação) (None = não muda). Lê as posições em
    ``data`` (banco original) e grava em ``into`` (o banco já alterado, do mesmo tamanho)."""
    out = bytearray(data if into is None else into)
    for repo_uid, values in changes.items():
        info = read(data, financas.record_start(data, repo_uid))
        for at, value in zip((info.training_at, info.youth_at, info.recruitment_at), values):
            if value is not None:
                struct.pack_into("<B", out, at, value)
    return bytes(out)
