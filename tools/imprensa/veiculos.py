"""Veículos e jornalistas fictícios usados pela Sala de Imprensa."""

from __future__ import annotations

import csv
import hashlib
import re
from html import escape
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SHEET = ROOT / "data" / "brasil" / "midia_2026.csv"


def slugify(value: str) -> str:
    swaps = str.maketrans("áàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇ", "aaaaeeiooouucAAAAEEIOOOUUC")
    return re.sub(r"[^a-z0-9]+", "-", value.translate(swaps).lower()).strip("-")


BRANDS: dict[str, tuple[str, str, str]] = {
    "ge": ("ge", "#ff6b00", "#fff4e8"),
    "lance": ("L!", "#e5282d", "#ffffff"),
    "uol-esporte": ("UOL", "#7024c4", "#ffffff"),
    "placar": ("PLACAR", "#dc1f2d", "#ffffff"),
    "sportv": ("sportv", "#ef3e42", "#ffffff"),
    "espn-brasil": ("ESPN", "#e31b23", "#ffffff"),
    "cazetv": ("CAZÉTV", "#7c39d8", "#dfff31"),
    "folha-de-s-paulo": ("Folha", "#1e6eb5", "#ffffff"),
    "o-estado-de-s-paulo": ("ESTADÃO", "#193a62", "#ffffff"),
    "o-globo": ("O GLOBO", "#1671b9", "#ffffff"),
    "extra": ("EXTRA", "#e51f2b", "#ffffff"),
    "estado-de-minas": ("EM", "#135c92", "#ffffff"),
    "o-tempo": ("O TEMPO", "#1171b8", "#ffffff"),
    "radio-itatiaia": ("ITATIAIA", "#1663a8", "#ffdd32"),
    "zero-hora": ("ZH", "#1d73b7", "#ffffff"),
    "radio-gaucha": ("GAÚCHA", "#d9282f", "#ffffff"),
    "correio-do-povo": ("CP", "#203f77", "#ffffff"),
    "a-tarde": ("A TARDE", "#e86f21", "#ffffff"),
    "jornal-do-commercio": ("JC", "#1d5d98", "#ffffff"),
    "diario-de-pernambuco": ("DIARIO", "#174e7f", "#ffffff"),
    "o-povo": ("O POVO", "#ee7b22", "#ffffff"),
    "diario-do-nordeste": ("DN", "#1f64a8", "#ffffff"),
    "gazeta-do-povo": ("GAZETA", "#194f75", "#ffffff"),
}

FIRST_NAMES = [
    "Ana", "Beatriz", "Bruno", "Caio", "Camila", "Carolina", "Daniel", "Diego", "Eduarda", "Felipe",
    "Fernanda", "Gabriel", "Helena", "Igor", "Isabela", "João", "Júlia", "Leonardo", "Lívia", "Marcelo",
    "Marina", "Mateus", "Natália", "Paulo", "Rafael", "Renata", "Rodrigo", "Sabrina", "Thiago", "Vitória",
]
LAST_NAMES = [
    "Albuquerque", "Amaral", "Barbosa", "Bastos", "Campos", "Cardoso", "Carvalho", "Castro", "Correia",
    "Costa", "Duarte", "Farias", "Ferraz", "Freitas", "Lacerda", "Leal", "Lima", "Macedo", "Menezes",
    "Moraes", "Nogueira", "Paiva", "Pires", "Ramos", "Rezende", "Rocha", "Salles", "Tavares", "Viana",
]

MEDIUM_STYLE = {
    "site": ("repórter", "ritmo rápido", ["desempenho", "mercado", "bastidores"]),
    "tv": ("comentarista", "análise ao vivo", ["tática", "protagonistas", "pressão"]),
    "radio": ("repórter de campo", "pergunta direta", ["ambiente", "torcida", "notícia imediata"]),
    "jornal": ("setorista", "contexto local", ["política do clube", "vestiário", "planejamento"]),
    "revista": ("jornalista especial", "entrevista longa", ["carreira", "história", "identidade"]),
}


def _seed(value: str) -> int:
    return int.from_bytes(hashlib.blake2s(value.encode("utf-8"), digest_size=4).digest(), "little")


def load_outlets() -> list[dict]:
    with SHEET.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    outlets: list[dict] = []
    for row in rows:
        slug = slugify(row["nome"])
        mark, primary, foreground = BRANDS.get(slug, (row["nome"][:8].upper(), "#28618d", "#ffffff"))
        role, cadence, focus = MEDIUM_STYLE.get(row["meio"], ("jornalista", "equilibrado", ["futebol"]))
        journalists = []
        for index in range(2):
            seed = _seed(f"{row['nome']}:{index}")
            first = FIRST_NAMES[seed % len(FIRST_NAMES)]
            last = LAST_NAMES[(seed >> 7) % len(LAST_NAMES)]
            journalists.append({
                "id": f"{slug}-{index + 1}",
                "name": f"{first} {last}",
                "role": role if index == 0 else ("apresentador" if row["meio"] in {"tv", "radio"} else "colunista"),
                "seed": seed,
                "approach": cadence if index == 0 else "pergunta de acompanhamento",
            })
        outlets.append({
            "id": slug,
            "name": row["nome"],
            "medium": row["meio"],
            "frequency": row["periodicidade"],
            "scope": row["alcance"],
            "city": row["cidade"] or "Brasil",
            "clubs": [club for club in row["clubes"].split(";") if club],
            "url": row["endereco"],
            "mark": mark,
            "colors": {"primary": primary, "foreground": foreground},
            "voice": cadence,
            "focus": focus,
            "journalists": journalists,
            "logo": f"/logos/{slug}.svg",
        })
    return outlets


def logo_svg(slug: str) -> bytes | None:
    outlet = next((item for item in load_outlets() if item["id"] == slug), None)
    if not outlet:
        return None
    primary = outlet["colors"]["primary"]
    foreground = outlet["colors"]["foreground"]
    mark = escape(outlet["mark"])
    name = escape(outlet["name"])
    size = 34 if len(mark) <= 3 else 24 if len(mark) <= 7 else 19
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="240" height="84" viewBox="0 0 240 84">
<rect width="240" height="84" rx="8" fill="#031426"/>
<rect x="3" y="3" width="234" height="78" rx="6" fill="{primary}" stroke="#71b4e2" stroke-opacity=".45"/>
<path d="M8 66H232" stroke="#020a13" stroke-opacity=".35"/>
<text x="120" y="52" text-anchor="middle" fill="{foreground}" font-family="Arial Black,Arial,sans-serif" font-size="{size}" font-weight="900" letter-spacing=".4">{mark}</text>
<title>{name}</title>
</svg>"""
    return svg.encode("utf-8")

