"""Confere as planilhas que você preenche antes de rodar o aplicar_tudo.py.

    python scripts\\validar_entregas.py

Para cada planilha de data/modelos (e as listas de data/brasil/comissao), mostra o que o
script do mod não vai conseguir usar: jogador que não está na jogadores_2026.xlsx (nome e
clube têm de ser iguais), clube que não é de 2026, data fora do formato AAAA-MM-DD, nota
fora de 1-20, jogada preferida que o jogo não conhece, nação sem código. Não muda nada.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import comissao, historico_jogadores, people_contracts  # noqa: E402
from fm06patch.live_player import FMM_DIR  # noqa: E402

MODELS = ROOT / "data" / "modelos"
PLAYERS = ROOT / "data" / "brasil" / "jogadores" / "jogadores_2026.xlsx"
IDENTITIES = ROOT / "data" / "brasil" / "clubes" / "identidade_fm06.csv"
SHOW = 12                                   # problemas mostrados por planilha


def rows(path: Path, sheet: str) -> list[dict]:
    values = openpyxl.load_workbook(path, read_only=True)[sheet].iter_rows(values_only=True)
    header = [str(h or "").strip() for h in next(values)]
    return [dict(zip(header, r)) for r in values if any(v not in (None, "") for v in r)]


def text(value) -> str:
    return "" if value is None else str(value).strip()


def is_date(value, empty_ok: bool = True) -> bool:
    if isinstance(value, (dt.date, dt.datetime)):
        return True
    if not text(value):
        return empty_ok
    try:
        dt.date.fromisoformat(text(value)[:10])
        return True
    except ValueError:
        return False


def grade(value, low: int = 1, high: int = 20) -> bool:
    return not text(value) or (text(value).isdigit() and low <= int(text(value)) <= high)


class Report:
    def __init__(self) -> None:
        self.problems: dict[str, list[str]] = defaultdict(list)
        self.checked: list[str] = []

    def file(self, name: str) -> None:
        self.checked.append(name)

    def add(self, name: str, line: int, message: str) -> None:
        self.problems[name].append(f"linha {line}: {message}")

    def show(self) -> int:
        total = 0
        for name in self.checked:
            found = self.problems.get(name, [])
            total += len(found)
            print(f"\n{'[OK]   ' if not found else '[CONFIRA]'} {name}" + (f": {len(found)} problema(s)" if found else ""))
            for line in found[:SHOW]:
                print("    ", line)
            if len(found) > SHOW:
                print(f"     ... e mais {len(found) - SHOW}")
        return total


def main() -> None:
    report = Report()
    players = rows(PLAYERS, "Jogadores")
    by_club = {(text(r["clube"]), text(r["nome_comum"]) or f"{text(r['primeiro_nome'])} {text(r['sobrenome'])}".strip())
               for r in players}
    born = {(text(r["clube"]), text(r["nome_comum"])): text(r["nascimento"])[:10] for r in players}
    names = {key[1].casefold() for key in by_club}
    clubs = {r["clube_2026"] for r in csv.DictReader(IDENTITIES.open(encoding="utf-8-sig"))}

    def player(name: str, line: int, club, nome, nascimento=None) -> None:
        key = (text(club), text(nome))
        if key[0] not in clubs:
            report.add(name, line, f"clube '{key[0]}' não é um clube de 2026 (identidade_fm06.csv)")
        elif key not in by_club:
            report.add(name, line, f"'{key[1]}' não está no {key[0]} na jogadores_2026.xlsx (nome igual ao de lá)")
        elif nascimento and born.get(key) and text(nascimento)[:10] != born[key]:
            report.add(name, line, f"'{key[1]}': nascimento {text(nascimento)[:10]}, na jogadores_2026 {born[key]}")

    path = MODELS / "jogadores_perfil.xlsx"
    if path.exists():
        name = path.name
        report.file(name)
        moves = {m["move_name"].casefold() for m in
                 json.loads((FMM_DIR / "preferred_moves_layout.json").read_text(encoding="utf-8"))["moves"]}
        columns = ("adaptabilidade", "ambicao", "lealdade", "pressao", "profissionalismo", "desportivismo",
                   "temperamento", "controversia", "consistencia", "jogos_importantes", "propensao_lesao",
                   "versatilidade", "jogo_sujo")
        for line, row in enumerate(rows(path, "Perfil"), start=2):
            player(name, line, row.get("clube"), row.get("nome_comum"))
            bad = [c for c in columns if not grade(row.get(c))]
            if bad:
                report.add(name, line, "fora de 1-20: " + ", ".join(bad))
            unknown = [m.strip() for m in text(row.get("jogadas_preferidas")).split(";")
                       if m.strip() and m.strip().casefold() not in moves]
            if unknown:
                report.add(name, line, "jogada preferida que o jogo não conhece (use o nome_ingles da aba Jogadas): "
                           + "; ".join(unknown))

    path = MODELS / "historico_carreira.xlsx"
    if path.exists():
        name = path.name
        report.file(name)
        for line, row in enumerate(rows(path, "Historico"), start=2):
            player(name, line, row.get("clube_2026"), row.get("nome_comum"), row.get("nascimento"))
            try:
                historico_jogadores.period(text(row.get("temporada")))
            except ValueError as error:
                report.add(name, line, str(error))
            for column in ("jogos", "gols"):
                if text(row.get(column)) and not text(row.get(column)).isdigit():
                    report.add(name, line, f"{column} '{text(row.get(column))}' não é número inteiro")
            if text(row.get("emprestimo")).lower() not in ("", "sim", "não", "nao", "s", "n"):
                report.add(name, line, "emprestimo tem de ser sim ou não")

    path = MODELS / "regens_futuros_2026.xlsx"
    if path.exists():
        name = path.name
        report.file(name)
        for line, row in enumerate(rows(path, "Regens"), start=2):
            if text(row.get("clube")) not in clubs:
                report.add(name, line, f"clube '{text(row.get('clube'))}' não é um clube de 2026")
            if not is_date(row.get("nascimento"), empty_ok=False):
                report.add(name, line, "nascimento obrigatório, AAAA-MM-DD")
            shown = text(row.get("nome_comum")) or f"{text(row.get('primeiro_nome'))} {text(row.get('sobrenome'))}".strip()
            if shown.casefold() in names:
                report.add(name, line, f"'{shown}' já está na jogadores_2026.xlsx (ficaria duplicado)")
            if text(row.get("nacionalidade")) and people_contracts.NATION_CODES.get(text(row["nacionalidade"])) is None:
                report.add(name, line, f"nação '{text(row['nacionalidade'])}' sem código no jogo")

    path = MODELS / "arbitros_2026.xlsx"
    if path.exists():
        name = path.name
        report.file(name)
        for line, row in enumerate(rows(path, "Arbitros"), start=2):
            if not text(row.get("nome")):
                report.add(name, line, "sem nome")
            if not text(row.get("nivel")) or not grade(row.get("nivel")):
                report.add(name, line, "nivel obrigatório, 1-20")
            if not grade(row.get("rigor")):
                report.add(name, line, "rigor fora de 1-20")

    path = MODELS / "clubes_estrutura_2026.xlsx"
    if path.exists():
        name = path.name + " (Rivais)"
        report.file(name)
        for line, row in enumerate(rows(path, "Rivais"), start=2):
            for column in ("clube", "rival"):
                if text(row.get(column)) not in clubs:
                    report.add(name, line, f"{column} '{text(row.get(column))}' não é clube de 2026 "
                               "(fora de 2026 vale o nome curto do FM06, se o registro não virou outro clube)")
            if text(row.get("intensidade")) not in ("1", "2", "3"):
                report.add(name, line, "intensidade tem de ser 1, 2 ou 3")
        name = path.name + " (Estrutura)"
        report.file(name)
        for line, row in enumerate(rows(path, "Estrutura"), start=2):
            if text(row.get("clube")) not in clubs:
                report.add(name, line, f"clube '{text(row.get('clube'))}' não é clube de 2026")
            bad = [c for c in ("ct", "base_instalacoes", "base_recrutamento") if not grade(row.get(c))]
            if bad:
                report.add(name, line, "fora de 1-20: " + ", ".join(bad))

    def number(value) -> bool:
        return not text(value) or text(value).replace(".", "", 1).replace(",", "", 1).isdigit()

    path = MODELS / "patrocinadores_2026.xlsx"
    if path.exists():
        name = path.name
        report.file(name)
        for line, row in enumerate(rows(path, "Patrocinios"), start=2):
            if text(row.get("clube")) not in clubs:
                report.add(name, line, f"clube '{text(row.get('clube'))}' não é clube de 2026")
            if not text(row.get("empresa")):
                report.add(name, line, "sem empresa")
            if not number(row.get("valor_anual_brl")):
                report.add(name, line, "valor_anual_brl tem de ser número (sem R$)")
            if not (is_date(row.get("inicio")) and is_date(row.get("fim"))):
                report.add(name, line, "inicio/fim fora do formato AAAA-MM-DD")

    path = MODELS / "premiacao_2026.xlsx"
    if path.exists():
        for sheet, column in (("Premiacao", "valor"), ("Cotas_TV", "valor_anual")):
            name = f"{path.name} ({sheet})"
            report.file(name)
            for line, row in enumerate(rows(path, sheet), start=2):
                if not text(row.get(column)) or not number(row.get(column)):
                    report.add(name, line, f"{column} obrigatório, número (sem R$ ou US$)")
                if text(row.get("moeda")).upper() not in ("BRL", "USD"):
                    report.add(name, line, "moeda tem de ser BRL ou USD")
                if sheet == "Cotas_TV" and text(row.get("clube")) not in clubs:
                    report.add(name, line, f"clube '{text(row.get('clube'))}' não é clube de 2026")

    path = MODELS / "premios_historico.xlsx"
    if path.exists():
        name = path.name
        report.file(name)
        for line, row in enumerate(rows(path, "Premios"), start=2):
            if not text(row.get("ano")).isdigit() or not 2006 <= int(text(row.get("ano"))) <= 2025:
                report.add(name, line, "ano de 2006 a 2025")
            if not text(row.get("premio")) or not text(row.get("vencedor")):
                report.add(name, line, "premio e vencedor obrigatórios")

    path = MODELS / "lesoes_suspensoes_2026.xlsx"
    if path.exists():
        for sheet, dates in (("Lesoes", ("desde", "volta_prevista")), ("Suspensoes", ())):
            name = f"{path.name} ({sheet})"
            report.file(name)
            for line, row in enumerate(rows(path, sheet), start=2):
                player(name, line, row.get("clube"), row.get("nome_comum"))
                for column in dates:
                    if not is_date(row.get(column)):
                        report.add(name, line, f"{column} fora do formato AAAA-MM-DD")

    path = MODELS / "nomes_regens.xlsx"
    if path.exists():
        name = path.name
        report.file(name)
        for line, row in enumerate(rows(path, "Nomes"), start=2):
            if people_contracts.NATION_CODES.get(text(row.get("nacao"))) is None:
                report.add(name, line, f"nação '{text(row.get('nacao'))}' sem código no jogo")
            if text(row.get("peso")) and not text(row.get("peso")).replace(".", "", 1).isdigit():
                report.add(name, line, "peso tem de ser número")

    path = ROOT / "data" / "brasil" / "comissao" / "selecoes_2026.csv"
    if path.exists():
        name = path.name
        report.file(name)
        for line, row in enumerate(csv.DictReader(path.open(encoding="utf-8-sig")), start=2):
            if not text(row.get("nome")):
                continue
            if comissao.nation_code(row["nacao"]) is None:
                report.add(name, line, f"nacao '{row['nacao']}' sem código (use BRA, ARG, URU...)")
            if text(row.get("nacionalidade")) and comissao.nation_code(row["nacionalidade"]) is None:
                report.add(name, line, f"nacionalidade '{row['nacionalidade']}' sem código")
            if not is_date(row.get("nascimento")):
                report.add(name, line, "nascimento fora do formato AAAA-MM-DD")
            if not text(row.get("fonte")):
                report.add(name, line, "sem fonte")

    path = ROOT / "data" / "brasil" / "comissao" / "comissao_2026.csv"
    if path.exists():
        name = path.name
        report.file(name)
        for line, row in enumerate(csv.DictReader(path.open(encoding="utf-8-sig")), start=2):
            if row["clube"] not in clubs:
                report.add(name, line, f"clube '{row['clube']}' não é clube de 2026")
            if row["cargo"] not in comissao.JOB_OF:
                report.add(name, line, f"cargo '{row['cargo']}' (use: {', '.join(comissao.JOB_OF)})")
            if not is_date(row.get("nascimento")):
                report.add(name, line, "nascimento fora do formato AAAA-MM-DD")

    total = report.show()
    print(f"\n{total} problema(s) no total." if total else "\nTudo certo: as planilhas podem ir para o aplicar_tudo.py.")


if __name__ == "__main__":
    main()
