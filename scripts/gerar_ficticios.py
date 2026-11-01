"""Jogadores fictícios para completar os elencos de 2026 (pelo menos 24 por clube).

    python scripts\\gerar_ficticios.py            (simulação: mostra quantos por clube)
    python scripts\\gerar_ficticios.py --apply    (grava a planilha)

Para cada clube de 2026 da identidade_fm06.csv (séries e estaduais) com menos de ELENCO
jogadores na jogadores_2026.xlsx, gera o que falta no mesmo formato da planilha, em
data/brasil/jogadores/ficticios_2026.xlsx (aba Jogadores) e uma cópia em .csv. O instalador lê
essa planilha junto com a jogadores_2026.xlsx (reforço, montar_elencos, comissão): o fictício
ocupa um jogador de 2005 como qualquer outro, com nome, posição, idade e CA/PA gravados.

- Posições: completa um elenco de 24 (3 GK, 4 CB, 2 RB, 2 LB, 2 DM, 4 CM, 2 AM, 1 RW, 1 LW,
  3 ST) descontando quem a planilha já tem.
- Nível: CA pela reputação do clube no server_db do jogo (a da instalação), calibrado pelos
  jogadores reais da planilha (mediana 76 nos clubes pequenos): ~68 até 3.500 de reputação,
  ~96 em 7.000, com variação; PA maior nos jovens.
- Nomes: os brasileiros de hoje da nomes_regens.xlsx, no máximo 2 palavras (prenome e
  sobrenome de uma palavra), sem repetir no clube. Uns 28% ganham nome de jogo pelas chances da
  aba Regras_apelido: o sobrenome, um apelido da lista (o peso é a raridade), diminutivo,
  origem (Baiano, Gaúcho...), porte físico e "-gol" para atacante.

O sorteio é fixo por clube (a mesma planilha a cada rodada). Para pôr um jogador de verdade no
lugar de um fictício: apague a linha daqui e ponha o jogador na jogadores_2026.xlsx; na próxima
rodada o gerador só completa o que faltar.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import nomes_regens, server_teams  # noqa: E402
from fm06patch.people_contracts import NATION_CODES  # noqa: E402

PLAYERS = ROOT / "data" / "brasil" / "jogadores" / "jogadores_2026.xlsx"
OUT = ROOT / "data" / "brasil" / "jogadores" / "ficticios_2026.xlsx"
IDENTITY = ROOT / "data" / "brasil" / "clubes" / "identidade_fm06.csv"
REGEN_NAMES = ROOT / "data" / "modelos" / "nomes_regens.xlsx"
ELENCO = 24
SHAPE = {"GK": 3, "CB": 4, "RB": 2, "LB": 2, "DM": 2, "CM": 4, "AM": 2, "RW": 1, "LW": 1, "ST": 3}
HEIGHT = {"GK": (184, 196), "CB": (180, 193), "ST": (174, 190)}


def game_dir() -> Path:
    return Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"])


def target_ca(reputation: int) -> int:
    """Os reais da planilha: mediana 76 nos clubes de até ~4.000 de reputação, ~100 nos de
    6.000-7.000. O fictício completa o elenco: um pouco abaixo."""
    return max(60, min(110, round(68 + max(0, reputation - 3500) * 28 / 3500)))


def names_of_brazil() -> tuple[list[str], list[int], list[str], list[int], list[str], list[int]]:
    """Prenomes, sobrenomes e apelidos brasileiros (com o peso = raridade) da nomes_regens.xlsx;
    o load_sheet já tira prenome e sobrenome de mais de uma palavra."""
    table = nomes_regens.load_sheet(REGEN_NAMES)
    brazil = NATION_CODES["Brasil"]
    first, second, nick = (table.get((kind, brazil), {}) for kind in ("first", "second", "common"))
    return list(first), list(first.values()), list(second), list(second.values()), list(nick), list(nick.values())


# nome de jogo (apelido), com as chances da aba Regras_apelido da nomes_regens.xlsx; o resto
# joga com prenome e sobrenome
GENTILIC = {"AC": "Acreano", "AL": "Alagoano", "AM": "Amazonense", "AP": "Amapá", "BA": "Baiano", "CE": "Cearense",
            "DF": "Brasília", "ES": "Capixaba", "GO": "Goiano", "MA": "Maranhão", "MG": "Mineiro", "MS": "Pantanal",
            "MT": "Cuiabano", "PA": "Paraense", "PB": "Paraíba", "PE": "Pernambuco", "PI": "Piauí", "PR": "Paranaense",
            "RJ": "Carioca", "RN": "Potiguar", "RO": "Rondônia", "RR": "Roraima", "RS": "Gaúcho", "SC": "Catarina",
            "SE": "Sergipe", "SP": "Paulista", "TO": "Tocantins"}
SIZE = ["Magrão", "Baixinho", "Pezão", "Galego", "Careca", "Cabeção"]


def diminutive(name: str) -> str:
    if name[-1] in "oa":
        return name[:-1] + ("inho" if name[-1] == "o" else "inha" if not name.endswith("ia") else "inho")
    return name + "zinho"


def nickname(rng: random.Random, first: str, second: str, role: str, uf: str, nicks, nick_w) -> str:
    roll = rng.random() * 100
    if roll < 12:
        return second                                   # sobrenome como nome de jogo (Ribeiro)
    if roll < 20 and nicks:
        return rng.choices(nicks, nick_w)[0]            # apelido da lista, pela raridade
    if roll < 25:
        return diminutive(first)                        # Gabriel -> Gabrielzinho
    if roll < 27 and uf in GENTILIC:
        return f"{first} {GENTILIC[uf]}" if rng.random() < 0.5 else GENTILIC[uf]
    if roll < 28:
        return rng.choice(SIZE)
    if roll < 28.5 and role == "ST":
        return first[:4].rstrip("aeiou") + "gol"
    return ""


def player(rng: random.Random, club: str, uf: str, role: str, ca: int, reputation: int, names, taken: set[str],
           numbers: set[int]) -> dict:
    first_names, first_w, surnames, surname_w, nicks, nick_w = names
    while True:
        first = rng.choices(first_names, first_w)[0]
        second = rng.choices(surnames, surname_w)[0]
        common = nickname(rng, first, second, role, uf, nicks, nick_w)
        if f"{first} {second}" not in taken and common not in taken and first != second:
            break
    taken.add(f"{first} {second}")
    if common:
        taken.add(common)
    age = rng.choices(range(17, 35), [3, 5, 6, 7, 8, 8, 8, 8, 7, 7, 6, 6, 5, 4, 3, 3, 2, 2])[0]
    level = max(40, min(150, round(rng.gauss(ca, 7) - (8 if age <= 19 else 0))))
    growth = rng.randint(12, 45) if age <= 21 else rng.randint(4, 15) if age <= 24 else rng.randint(0, 5)
    low, high = HEIGHT.get(role, (168, 186))
    height = rng.randint(low, high)
    number = next(n for n in range(1, 99) if n not in numbers and (n > 23 or rng.random() < 0.5))
    numbers.add(number)
    month, day = rng.randint(1, 12), rng.randint(1, 28)
    return {"clube": club, "numero": number, "nome_comum": common, "primeiro_nome": first, "sobrenome": second,
            "nascimento": f"{2026 - age - 1}-{month:02d}-{day:02d}", "nacionalidade": "Brasil",
            "segunda_nacionalidade": None, "posicoes": role,
            "pe": rng.choices(["D", "E", "A"], [74, 22, 4])[0], "altura": height,
            "peso": round((height - 100) * rng.uniform(0.82, 0.95)), "valor_mercado_eur": None,
            "ca": level, "pa": min(170, level + growth), "contrato_inicio": "2025-01-01",
            "contrato_fim": rng.choice(["2026-12-31", "2027-12-31"]),
            "salario_mensal_brl": max(1518, round(reputation * 2 * rng.uniform(0.6, 1.3) / 100) * 100),
            "situacao_elenco": "Elenco", "emprestado_de": None, "emprestimo_fim": None, "jogos_selecao": 0,
            "gols_selecao": 0, "destaques": None, "fonte_url": None, "obs": "fictício (gerar_ficticios.py)"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    rows = openpyxl.load_workbook(PLAYERS, read_only=True)["Jogadores"].iter_rows(values_only=True)
    header = list(next(rows))
    sheet = [dict(zip(header, values)) for values in rows]
    count = Counter(r["clube"] for r in sheet if r.get("clube"))
    roles = {}
    for r in sheet:
        if r.get("clube"):
            roles.setdefault(r["clube"], Counter())[str(r.get("posicoes") or "CM").split()[0]] += 1
    server = (game_dir() / "data" / "db" / "server_db.dat").read_bytes()
    true = server_teams.true_uids(server)
    reputation = {true.get(t.club_uid, t.club_uid): t.reputation for t in server_teams.find_brazil_teams(server)}
    names = names_of_brazil()
    out, report = [], []
    for ident in csv.DictReader(IDENTITY.open(encoding="utf-8-sig")):
        club = ident["clube_2026"]
        missing = ELENCO - count[club]
        if not club or missing <= 0:
            continue
        rep = reputation.get(int(ident["uid_jogo"]), 1500)
        rng = random.Random(f"ficticios-2026-{club}")
        have = roles.get(club, Counter())
        need = [role for role, n in SHAPE.items() for _ in range(max(0, n - have[role]))]
        rng.shuffle(need)
        need = (need + ["CM", "ST", "CB", "CM", "AM"] * 5)[:missing]
        taken = {f"{r.get('primeiro_nome')} {r.get('sobrenome')}" for r in sheet if r.get("clube") == club}
        numbers = {int(r["numero"]) for r in sheet if r.get("clube") == club and str(r.get("numero") or "").isdigit()}
        for role in sorted(need, key=list(SHAPE).index):
            out.append(player(rng, club, ident["uf"], role, target_ca(rep), rep, names, taken, numbers))
        report.append((club, ident["uf"], count[club], missing, rep, target_ca(rep)))
    for club, uf, have, missing, rep, ca in report:
        print(f"{uf}  {club:28} {have:2} na planilha + {missing:2} fictícios (reputação {rep}, CA ~{ca})")
    print(f"{len(out)} fictícios para {len(report)} clubes")
    if not args.apply:
        print("(simulação: rode com --apply para gravar)")
        return
    book = openpyxl.Workbook()
    ws = book.active
    ws.title = "Jogadores"
    ws.append(header)
    for row in out:
        ws.append([row.get(h) for h in header])
    book.save(OUT)
    with OUT.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(out)
    print(f"[OK] gravado {OUT} e {OUT.with_suffix('.csv')}")


if __name__ == "__main__":
    main()
