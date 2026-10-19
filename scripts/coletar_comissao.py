"""Técnicos e comissões técnicas de 2026 dos clubes das Séries A, B, C e D.

    python scripts/coletar_comissao.py [--sofascore workspace/sofascore] [--wiki workspace/wiki]

- Técnico: o atual do Sofascore (/team/{id} e /manager/{id}: nome, nacionalidade e
  nascimento). Sem técnico no Sofascore (clubes da Série D já eliminados), o da tabela
  de comissão da Wikipédia.
- Comissão: a tabela "Current staff" / "Technical staff" / "Management team" do
  artigo do clube na Wikipédia em inglês (o artigo vem das páginas das Séries de
  2026). As tabelas nem sempre estão em dia; a coluna "atualizado" traz a data que
  a página informa.

Grava data/brasil/comissao/comissao_2026.csv. Depois: scripts/aplicar_comissao.py.
Precisa do times.json do coletar_sofascore.py.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from coletar_historico import Wiki  # noqa: E402
from coletar_sofascore import Sofascore  # noqa: E402
from fm06patch import wikitables  # noqa: E402
from fm06patch.estaduais_clubes import _words, normalize  # noqa: E402

OUT = ROOT / "data" / "brasil" / "comissao" / "comissao_2026.csv"
FIELDS = ["serie", "clube", "uf", "cargo", "funcao", "nome", "nacionalidade", "nascimento", "fonte", "atualizado"]
SECTION = re.compile(r"(?i)staff|technical|coaching|personnel|management team|comiss")
ROLES = [   # ordem importa: "Health and performance manager" é médico, não técnico
    ("medico", re.compile(r"(?i)doctor|physician|medic|physio|massag|masseur|nutrition|physiolog|psycholog|health")),
    ("olheiro", re.compile(r"(?i)scout")),
    ("analista", re.compile(r"(?i)analys|performance coordinator")),
    ("preparador", re.compile(r"(?i)goalkeep|fitness|physical|conditioning|strength|preparador")),
    ("auxiliar", re.compile(r"(?i)assistant|auxiliar")),
    ("tecnico", re.compile(r"(?i)^\s*(head coach|manager|coach|treinador|técnico)\s*$")),
]
CLUB_LINK = re.compile(r"(?i)\b(clube|club|futebol|esporte|sport|associa|sociedade|atl[eé]tico|fc|ec|sc|cr|cf|se|fr|"
                       r"aa|ad|grêmio|gremio|ac|recreativ|desportiv|bragantino)\b")
NOT_CLUB = re.compile(r"(?i)campeonato|copa|federa|est[aá]dio|arena|stadium|\d{4}")
# nome formal do Sofascore -> nome conhecido
KNOWN_AS = {"Renato Portaluppi": "Renato Gaúcho"}


SKIP_ROLE = re.compile(r"(?i)general assistant|kit|equipment|supervisor|roupeiro|director|president|executive")


def role_of(text: str) -> str | None:
    if SKIP_ROLE.search(text):
        return None
    for cargo, pattern in ROLES:
        if pattern.search(text):
            return cargo
    return None


def cell_names(cell: str) -> list[str]:
    """Nomes de uma célula ("Múcio Vaz, Paulo Regueira & Jorge Silva" são três)."""
    text = wikitables.strip_refs(cell)
    text = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\{\{[^{}]*\}\}|<[^>]+>", "", text).replace("'''", "").replace("''", "")
    names = re.split(r"\s*(?:,|&|/|\band\b|\be\b)\s*", text)
    return [n.strip(" .") for n in names if len(n.strip(" .")) > 1]


def staff_rows(text: str) -> tuple[list[tuple[str, str, str, str]], str]:
    """[(cargo, função, nome, nação)] das tabelas de comissão e a data de atualização."""
    found, updated = [], ""
    heads = [(m.start(), m.group()) for m in re.finditer(r"\n=+[^=\n]+=+", text)] + [(len(text), "")]
    for (start, head), (end, _) in zip(heads, heads[1:]):
        if not SECTION.search(head) or re.search(r"(?i)former|history|records", head):
            continue
        body = text[start:end]
        stamp = re.search(r"\{\{updated\|([^|}]+)", body) or re.search(r"(?i)last updated:?\s*([^<\n]+)", body)
        for table in wikitables.tables(body):
            for cells in wikitables.rows(table)[1:]:
                if len(cells) < 2:
                    continue
                plain = [wikitables._plain(wikitables.link_text(c)[0] if "[[" in c else c) for c in cells]
                for i, j in ((0, 1), (1, 0)):
                    cargo = role_of(plain[i])
                    if cargo and plain[j] and not role_of(plain[j]) and not SKIP_ROLE.search(plain[j]):
                        for name in cell_names(cells[j]):
                            found.append((cargo, plain[i], name, wikitables.flag_of(cells[j]) or ""))
                        break
        if found and stamp:
            updated = stamp.group(1).strip().rstrip(".")
    return found, updated


def club_articles(wiki: Wiki, teams: list[dict]) -> dict[str, str]:
    """Clube de 2026 -> artigo, pelos links das páginas de cada Série de 2026."""
    articles = {}
    for serie in "ABCD":
        text = wiki.raw(f"2026 Campeonato Brasileiro Série {serie}")
        strong, weak = {}, {}
        for target, label in re.findall(r"\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]", text):
            target, label = target.strip(), (label or target).strip()
            if NOT_CLUB.search(target):
                continue
            links = strong if CLUB_LINK.search(target) else weak
            for key in (normalize(label), normalize(target)):
                links.setdefault(key, target)
        for team in (t for t in teams if t["serie"] == serie):
            keys = [normalize(team["clube"]), normalize(team["sofascore_nome"]),
                    normalize(re.sub(r"-[A-Z]{2}$", "", team["clube"])), normalize(team["sofascore_nome"].split("/")[0])]
            article = next((links[k] for links in (strong, weak) for k in keys if k in links), None)
            if not article:
                words = _words(team["sofascore_nome"], team["estado"])
                hits = {v for k, v in strong.items() if words and words <= set(k.split())}
                article = hits.pop() if len(hits) == 1 else None
            if article:
                articles[team["clube"]] = article
    return articles


def pt_coach(wiki: Wiki, article: str) -> str:
    """Técnico do parâmetro "treinador" do artigo na Wikipédia em português."""
    text = wiki.raw(article, "pt")
    match = re.search(r"\|\s*treinador(?:_nome)?\s*=\s*([^\n|]*(?:\[\[[^\]]*\]\][^\n|]*)?)", text)
    if not match:
        return ""
    name = re.sub(r"<!--.*?(-->|$)|<ref.*", "", match.group(1))
    name = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]", r"\1", name)
    name = re.sub(r"\{\{[^{}]*\}\}|<[^>]+>|'''?", "", name).strip(" ,.")
    words = [w if w.lower() in ("de", "da", "do", "dos", "das") else w[:1].upper() + w[1:] for w in name.split()]
    return " ".join(words)


def manager(api: Sofascore, team_id: int) -> dict | None:
    team = (api.get(f"/team/{team_id}") or {}).get("team", {})
    boss = team.get("manager")
    if not boss:
        return None
    detail = (api.get(f"/manager/{boss['id']}") or {}).get("manager", {})
    born = detail.get("dateOfBirthTimestamp")
    return {
        "nome": KNOWN_AS.get(boss["name"], boss["name"]),
        "nacionalidade": detail.get("nationality") or (boss.get("country") or {}).get("alpha3", ""),
        "nascimento": (dt.date(1970, 1, 1) + dt.timedelta(seconds=born)).isoformat() if born is not None else "",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sofascore", type=Path, default=ROOT / "workspace" / "sofascore")
    parser.add_argument("--wiki", type=Path, default=ROOT / "workspace" / "wiki")
    args = parser.parse_args()
    teams = json.loads((args.sofascore / "times.json").read_text(encoding="utf-8"))
    api, wiki = Sofascore(args.sofascore), Wiki(args.wiki)
    articles = club_articles(wiki, teams)
    rows, no_staff = [], []
    for team in teams:
        base = {"serie": team["serie"], "clube": team["clube"], "uf": team["estado"]}
        boss = manager(api, team["sofascore_id"])
        staff, updated = staff_rows(wiki.raw(articles[team["clube"]])) if team["clube"] in articles else ([], "")
        if boss:
            rows.append({**base, "cargo": "tecnico", "funcao": "Head coach", **boss, "fonte": "Sofascore", "atualizado": ""})
        for cargo, funcao, nome, nation in staff:
            if cargo == "tecnico" and (boss or any(r["clube"] == team["clube"] and r["cargo"] == "tecnico" for r in rows)):
                continue
            rows.append({**base, "cargo": cargo, "funcao": funcao, "nome": nome, "nacionalidade": nation,
                         "nascimento": "", "fonte": f"Wikipédia: {articles[team['clube']]}", "atualizado": updated})
        has_boss = any(r["clube"] == team["clube"] and r["cargo"] == "tecnico" for r in rows)
        if not has_boss and team["clube"] in articles:
            name = pt_coach(wiki, articles[team["clube"]])
            if name:
                rows.append({**base, "cargo": "tecnico", "funcao": "Treinador", "nome": name, "nacionalidade": "",
                             "nascimento": "", "fonte": f"Wikipédia (pt): {articles[team['clube']]}", "atualizado": ""})
        if not staff:
            no_staff.append(team["clube"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    bosses = sum(1 for r in rows if r["cargo"] == "tecnico")
    print(f"[OK] {bosses} técnicos e {len(rows) - bosses} membros de comissão de {len(teams)} clubes em {OUT}")
    print(f"[INFO] {len(no_staff)} clubes sem tabela de comissão na Wikipédia (fica a do FM06)")


if __name__ == "__main__":
    main()
