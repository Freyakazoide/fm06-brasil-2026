"""Regens de verdade: joias da base de 2026 que o jogo cria na chegada dos juniores.

Comando FUTURE_REGEN do .edt (leitor 0x00AAD070): primeiro nome, nome comum, sobrenome,
nascimento, nação e clube favorito. O regen fica guardado na nação; se ela ou os três
nomes faltarem, a linha não faz nada. Conferido no fm.exe 6.0.2:

- nascimento: dia, mês e ano separados por "/", "-" ou "." (0x00C587D0); ano com dois
  dígitos vira 20xx abaixo de 40 e 19xx acima. Vai no ano do motor (real − 20): quem
  nasceu em 2010 entra como 1990 e tem 16 anos em 2026 na tela;
- nação e clube: o texto é comparado com o UID do objeto ([+0x14]) e com os nomes (o da
  nação no idioma do jogo). Vai o UID quando é conhecido: o do clube pela identidade
  (UID do jogo) e o da nação pela tabela abaixo; fora dela, o nome da planilha.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

SHIFT = 20

# código da nação no people_db -> UID público: cada registro de nação do server_db fecha com
# (código, UID) (Brasil 189/1651 em 0x5F46E4). Só os de sequência conferida: CONMEBOL
# 1649-1658 e Europa (código − 626, Inglaterra a Espanha; FMM: França 769, Espanha 796).
NATION_UIDS = {
    "Argentina": 1649, "Bolívia": 1650, "Brasil": 1651, "Chile": 1652, "Colômbia": 1653,
    "Equador": 1654, "Paraguai": 1655, "Peru": 1656, "Uruguai": 1657, "Venezuela": 1658,
    "Inglaterra": 765, "França": 769, "Itália": 776, "Holanda": 784, "Portugal": 788,
    "Espanha": 796,
}


@dataclass
class Prospect:
    clube: str
    primeiro_nome: str
    sobrenome: str
    nome_comum: str
    nascimento: str            # AAAA-MM-DD (data real)
    nacionalidade: str = "Brasil"

    @property
    def display_name(self) -> str:
        return self.nome_comum or f"{self.primeiro_nome} {self.sobrenome}".strip()


def engine_date(date: str, shift: int = SHIFT) -> str | None:
    """'2010-03-15' -> '15/03/1990' (formato do FUTURE_REGEN, ano do motor)."""
    try:
        real = dt.date.fromisoformat(str(date)[:10])
    except ValueError:
        return None
    day = 28 if (real.month, real.day) == (2, 29) else real.day
    return f"{day:02d}/{real.month:02d}/{real.year - shift}"


def _text(value: str) -> str:
    return '"' + str(value or "").replace('"', "").strip() + '"'


def edt_text(prospects: list[Prospect], club_uid: dict[str, int], shift: int = SHIFT) -> tuple[str, list[str]]:
    """(texto do .edt, avisos). Clube pelo nome de 2026 (identidade_fm06)."""
    lines = ["# FM06 Brasil 2026: joias da base (FUTURE_REGEN), data/modelos/regens_futuros_2026.xlsx"]
    warnings = []
    for p in prospects:
        date = engine_date(p.nascimento, shift)
        club = club_uid.get(p.clube)
        if not (p.primeiro_nome or p.sobrenome or p.nome_comum):
            continue
        if date is None:
            warnings.append(f"{p.display_name}: nascimento '{p.nascimento}' fora do formato AAAA-MM-DD")
            continue
        if club is None:
            warnings.append(f"{p.display_name}: clube '{p.clube}' não está na identidade_fm06.csv")
            continue
        year = int(date[-4:])
        if 2004 - year > 25:
            warnings.append(f"{p.display_name}: nascido em {year + shift}, velho demais para regen")
            continue
        nation = NATION_UIDS.get(p.nacionalidade, p.nacionalidade)
        lines.append("\t".join(['"FUTURE_REGEN"', _text(p.primeiro_nome), _text(p.nome_comum), _text(p.sobrenome),
                                _text(date), _text(nation), _text(club)]))
    return "\r\n".join(lines) + "\r\n", warnings


def load_sheet(path) -> list[Prospect]:
    """Aba Regens: clube, primeiro_nome, sobrenome, nome_comum, nascimento, nacionalidade."""
    import openpyxl

    rows = openpyxl.load_workbook(path, read_only=True)["Regens"].iter_rows(values_only=True)
    header = [str(h or "") for h in next(rows)]
    out = []
    for values in rows:
        row = {k: ("" if v is None else str(v).strip()) for k, v in zip(header, values)}
        if row.get("clube") and (row.get("primeiro_nome") or row.get("sobrenome") or row.get("nome_comum")):
            out.append(Prospect(row["clube"], row.get("primeiro_nome", ""), row.get("sobrenome", ""),
                                row.get("nome_comum", ""), row.get("nascimento", "")[:10],
                                row.get("nacionalidade") or "Brasil"))
    return out
