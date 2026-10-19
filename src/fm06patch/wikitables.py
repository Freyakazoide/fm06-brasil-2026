"""Tabelas de campeões no wikitexto da Wikipédia (action=raw).

champions(texto) lê as tabelas cujo cabeçalho tem uma coluna de campeão
("Champions", "Winner", "Campeão") e devolve, por ano, o campeão e o vice com o
artigo de cada um e o estado ou país da bandeira ao lado ({{flagicon|Paraná}},
{{BRA}}). Linhas com células mescladas (rowspan) caem no modo por posição: o
primeiro time depois do ano é o campeão, o segundo o vice.
"""

from __future__ import annotations

import re

SCORE = re.compile(r"^\s*\(?\d+\s*[–\-]\s*\d+")
COUNTRY_TPL = re.compile(r"^\{\{[A-Z]{3}\}\}$")
CHAMP_KEYS = ("champion", "winner", "campeão", "campeao", "campeões")
RUNNER_KEYS = ("runner", "vice", "finalist")
YEAR_KEYS = ("season", "year", "ano", "edição", "temporada")


def strip_refs(text: str) -> str:
    text = re.sub(r"<ref[^>]*/>", "", text)
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    text = re.sub(r"<ref[^>]*>.*", "", text, flags=re.S)
    return re.sub(r"\{\{(?:efn|refn|sfn|note|ref label)[^{}]*\}\}", "", text)


def tables(text: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"\{\|(.*?)\n\|\}", text, re.S)]


def rows(table: str) -> list[list[str]]:
    result = []
    for chunk in re.split(r"\n\|-[^\n]*", "\n" + table):
        cells: list[str] = []
        for line in chunk.split("\n"):
            line = line.rstrip()
            if not line or line[0] not in "|!" or line.startswith("|+") or line.startswith("{|"):
                if cells and line and line[0] not in "|!{":
                    cells[-1] += " " + line
                continue
            for part in re.split(r"\|\||!!", line[1:]):
                head = part.split("|")[0]
                if "|" in part and "[[" not in head and "{{" not in head and "=" in head:
                    part = part.split("|", 1)[1]            # atributos da célula (align=center|...)
                cells.append(part.strip())
        if cells:
            result.append(cells)
    return result


def _plain(cell: str) -> str:
    text = re.sub(r"\{\{[^{}]*\}\}", "", cell)
    text = re.sub(r"<[^>]+>", "", text)
    return text.replace("'''", "").replace("''", "").strip(" *†‡")


def link_text(cell: str) -> tuple[str, str | None]:
    """(nome, artigo) do primeiro link de time da célula (sem cidade entre parênteses)."""
    cell = strip_refs(cell)
    cell = re.sub(r"\{\{small\|.*?\}\}", "", cell)
    cell = re.sub(r"<br\s*/?>.*", "", cell)
    cell = re.sub(r"\(\s*\[\[[^\]]*\]\][^)]*\)", "", cell)
    cell = re.sub(r"\{\{flag[a-z]*\|[^{}]*\}\}", "", cell)
    links = [l for l in re.findall(r"\[\[([^\]]+)\]\]", cell)
             if not re.search(r"(?i)^(file|image|ficheiro|arquivo):", l)]
    for link in links:
        target, _, label = link.partition("|")
        label = (label or target).strip()
        if not re.match(r"^\d{4}", label) and not SCORE.match(label):
            return label, target.strip()
    return _plain(cell), None


def flag_of(cell: str | None) -> str | None:
    match = re.search(r"\{\{flag[a-z]*\|([^{}|]+)", cell or "")
    if match:
        return match.group(1).strip()
    match = re.search(r"\{\{([A-Z]{3})\}\}", cell or "")
    return match.group(1) if match else None


def is_team(cell: str) -> bool:
    cell = strip_refs(cell)
    if COUNTRY_TPL.match(cell.strip()):
        return False
    links = [l.split("|")[-1].strip() for l in re.findall(r"\[\[([^\]]+)\]\]", cell)]
    links = [l for l in links if l and not re.match(r"^\d{4}", l) and not SCORE.match(l)
             and not re.search(r"(?i)^(file|image):", l)]
    if links:
        return True
    if re.search(r"\{\{flag", cell):
        text = _plain(cell)
        return bool(text) and not SCORE.match(text)
    return False


def year_of(cell: str) -> int | None:
    match = re.search(r"\b(19[0-9]{2}|20[0-2][0-9])\b", cell)
    return int(match.group(1)) if match else None


def champions(text: str) -> dict[int, tuple[tuple, tuple]]:
    """{ano: ((campeão, artigo, local), (vice, artigo, local))}."""
    out: dict[int, tuple[tuple, tuple]] = {}
    none = (None, None, None)
    for table in tables(text):
        table_rows = rows(table)
        if not table_rows:
            continue
        header = [_plain(link_text(h)[0] if "[[" in h else h).lower() for h in table_rows[0]]
        ci = next((i for i, h in enumerate(header) if any(k in h for k in CHAMP_KEYS)), None)
        ri = next((i for i, h in enumerate(header) if any(k in h for k in RUNNER_KEYS)), None)
        yi0 = next((i for i, h in enumerate(header) if any(k in h for k in YEAR_KEYS)), None)
        if ci is None:
            continue
        for cells in table_rows[1:]:
            if len(cells) == len(header):
                year_cell = cells[yi0] if yi0 is not None else next(
                    (c for c in cells[:3] if year_of(strip_refs(c))), None)
                year = year_of(strip_refs(year_cell)) if year_cell else None
                if not year or not is_team(cells[ci]):
                    continue
                champ = link_text(cells[ci]) + (flag_of(cells[ci]) or flag_of(cells[ci - 1]),)
                runner = none
                if ri is not None and is_team(cells[ri]):
                    after = cells[ri + 1] if ri + 1 < len(cells) else None
                    runner = link_text(cells[ri]) + (flag_of(cells[ri]) or flag_of(after),)
            else:
                yi = next((i for i, c in enumerate(cells[:3]) if year_of(strip_refs(c)) and not is_team(c)), None)
                if yi is None:
                    continue
                teams = [c for c in cells[yi + 1:] if is_team(c) and link_text(c)[0]
                         and not re.fullmatch(r"\{\{flag[a-z]*\|[^{}]*\}\}", strip_refs(c).strip())]
                if not teams:
                    continue
                year = year_of(strip_refs(cells[yi]))
                champ = link_text(teams[0]) + (flag_of(teams[0]),)
                runner = link_text(teams[1]) + (flag_of(teams[1]),) if len(teams) > 1 and ri is not None else none
            if champ[0]:
                out.setdefault(year, (champ, runner))
    return out


def section(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    end = text.find("\n==", start + len(heading) + 2)
    while end >= 0 and text[end:end + 4] == "\n===":
        end = text.find("\n==", end + 4)
    return text[start:end if end > 0 else None]
