"""Transforma uma planilha de elenco em arquivos para o jogo.

Entrada:
    - planilha do elenco desejado (ex.: data/brasil/flamengo_2026.csv)
    - elenco hospedeiro gerado por ``live_player_editor.py --squad``

Saída:
    - .lnc com CHANGE_PLAYER_NAME (aplicado pelo jogo no New Game)
    - .json para ``live_player_editor.py`` (dados do jogador)
    - CSV com quem virou quem

Os atributos são estimativas: um perfil por função, escalado pelo CA, mais
os "destaques" da planilha, que têm prioridade.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path


# Jogadores de 2005 usados para copiar a nacionalidade (nationality_like).
NATIONALITY_DONORS = {
    "Brasil": 3300977,     # Rogério Ceni
    "Argentina": 3100367,  # Javier Saviola
    "Uruguai": 5512281,    # Diego Lugano
    "Chile": 2001859,      # Marcelo Salas
    "Espanha": 6700151,    # Iker Casillas
    "França": 8076,        # Zinedine Zidane
    # Achados no people_db (nome completo, ano, código da nação; UID no fim do registro):
    "Colômbia": 309478, "Paraguai": 120938, "Portugal": 735216, "Equador": 856896,
    "Venezuela": 121009, "Peru": 8826193, "Bolívia": 5240074, "Nigéria": 919581,
    "Camarões": 105788, "Gana": 876900, "Angola": 913822, "Marrocos": 916312,
    "Panamá": 5260831, "Croácia": 652368, "Holanda": 1590, "Inglaterra": 2003443,
    "Dinamarca": 928418, "Suécia": 15951, "Bulgária": 5313413, "Estados Unidos": 976234,
    "México": 120929, "Senegal": 403128, "Guiné": 8168095, "RD Congo": 144178,
    "Costa do Marfim": 533344, "Moçambique": 4100618,
}

# Perfis para um jogador de CA 160, na escala exibida (1..20).
_TECH = ("Cabeceamento", "Cantos", "Cruzamentos", "Desarme", "Finalização", "Finta",
         "Lançam. Longos", "Livres", "Marcação", "Marcação Penalties", "Passe",
         "Primeiro Toque", "Remates Longe", "Técnica")
_MENT = ("Agressividade", "Antecipação", "Bravura", "Compostura", "Concentração",
         "Criatividade", "Decisões", "Determinação", "Influência", "Instinto",
         "Posicionamento", "Sem Bola", "Trabalho Equipa", "Índice Trabalho")
_PHYS = ("Aceleração", "Agilidade", "Balance", "Cond. Fís. Natural", "Força",
         "Impulsão", "Resistência", "Velocidade")
_GK = ("Handling", "Aer ability", "Cmd of area", "Communiction", "Kicking",
       "Long throws", "One on one", "Reflexes", "Rushing out", "Punch", "Eccentricity")


def _profile(tech, ment, phys, gk=(1,) * 11) -> dict[str, int]:
    return dict(zip(_TECH + _MENT + _PHYS + _GK, tech + ment + phys + gk))


PROFILES = {
    "GK": _profile((3, 3, 3, 4, 3, 4, 10, 4, 4, 5, 9, 8, 4, 7),
                   (8, 15, 15, 15, 16, 6, 15, 15, 12, 6, 16, 4, 12, 10),
                   (11, 15, 12, 14, 13, 15, 10, 10),
                   (16, 15, 15, 15, 14, 13, 16, 17, 13, 12, 8)),
    "CB": _profile((16, 4, 6, 16, 5, 7, 6, 5, 16, 7, 12, 11, 6, 10),
                   (13, 15, 15, 14, 15, 8, 14, 15, 12, 6, 16, 6, 13, 12),
                   (12, 11, 13, 14, 16, 16, 13, 12)),
    "FB": _profile((10, 8, 15, 14, 7, 13, 10, 7, 13, 7, 13, 13, 8, 13),
                   (11, 13, 12, 12, 13, 11, 12, 14, 9, 11, 13, 12, 14, 16),
                   (16, 14, 13, 15, 11, 11, 16, 16)),
    "DM": _profile((12, 8, 9, 16, 8, 10, 6, 10, 15, 10, 15, 14, 12, 13),
                   (14, 15, 14, 15, 15, 12, 15, 16, 14, 8, 16, 9, 16, 16),
                   (11, 11, 14, 15, 15, 13, 16, 11)),
    "AM": _profile((8, 15, 14, 7, 14, 16, 5, 16, 6, 14, 18, 17, 15, 18),
                   (8, 15, 9, 16, 13, 18, 16, 14, 13, 17, 9, 15, 14, 13),
                   (14, 15, 14, 13, 9, 8, 14, 13)),
    "W": _profile((7, 12, 15, 6, 14, 17, 5, 11, 5, 12, 13, 15, 14, 16),
                  (9, 14, 10, 13, 11, 14, 13, 14, 9, 17, 7, 16, 12, 13),
                  (17, 16, 14, 13, 9, 8, 14, 17)),
    "ST": _profile((16, 5, 8, 5, 18, 13, 5, 8, 4, 15, 12, 16, 14, 15),
                   (11, 17, 13, 17, 13, 12, 14, 15, 11, 13, 7, 17, 11, 10),
                   (14, 13, 15, 14, 15, 15, 13, 14)),
}

ROLE_PROFILE = {"GK": "GK", "CB": "CB", "RB": "FB", "LB": "FB", "DM": "DM",
                "CM": "AM", "AM": "AM", "RW": "W", "LW": "W", "ST": "ST"}

POSITION_FIELDS = (
    "Goalkeeper", "Sweeper", "Defender", "Def. Mid.", "Midfielder", "Att. Mid.",
    "Attacker", "Wing back", "Free role", "Right side", "Left side", "Center side",
    "Left Def.", "Center Def.", "Right Def.", "Def. C.M.", "Mid. Left", "Mid. Center",
    "Mid. Right", "Att. M.L.", "Att. M.C.", "Att. M.R.", "Att. Center",
    "Wing B.L.", "Wing B.R.",
)

# Nota 15+ aparece na posição do jogador; as vizinhas ficam abaixo disso (o meia central com
# "meia ofensivo" 16 aparecia como "MD, MA C" no lugar de volante/meia).
ROLE_POSITIONS = {
    "GK": {"Goalkeeper": 20},
    "CB": {"Defender": 20, "Center side": 20, "Center Def.": 20},
    "RB": {"Defender": 20, "Wing back": 15, "Right side": 20, "Right Def.": 20, "Wing B.R.": 15},
    "LB": {"Defender": 20, "Wing back": 15, "Left side": 20, "Left Def.": 20, "Wing B.L.": 15},
    "DM": {"Def. Mid.": 20, "Midfielder": 13, "Center side": 20, "Def. C.M.": 20, "Mid. Center": 13},
    "CM": {"Midfielder": 20, "Def. Mid.": 12, "Att. Mid.": 12, "Center side": 20, "Mid. Center": 20},
    "AM": {"Att. Mid.": 20, "Midfielder": 13, "Center side": 20, "Att. M.C.": 20, "Mid. Center": 13},
    "RW": {"Att. Mid.": 20, "Midfielder": 12, "Right side": 20, "Att. M.R.": 20, "Mid. Right": 13},
    "LW": {"Att. Mid.": 20, "Midfielder": 12, "Left side": 20, "Att. M.L.": 20, "Mid. Left": 13},
    "ST": {"Attacker": 20, "Center side": 20, "Att. Center": 20},
}


@dataclass
class Target:
    number: str
    common: str
    first: str
    second: str
    born: str
    nationality: str
    roles: list[str]
    foot: str
    height: int
    weight: int
    ca: int
    pa: int
    highlights: dict[str, int] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        return self.common or f"{self.first} {self.second}".strip()

    @property
    def is_goalkeeper(self) -> bool:
        return self.roles[0] == "GK"


def read_targets(path: Path) -> list[Target]:
    targets = []
    with path.open(encoding="utf-8") as source:
        for row in csv.DictReader(source):
            highlights = {}
            for item in filter(None, (row.get("destaques") or "").split(";")):
                name, value = item.split("=")
                highlights[name.strip()] = int(value)
            roles = row["posicoes"].split()
            unknown = [r for r in roles if r not in ROLE_POSITIONS]
            if unknown:
                raise ValueError(f"{row['primeiro_nome']}: posição desconhecida {unknown}")
            targets.append(Target(
                number=row["numero"], common=row["nome_comum"], first=row["primeiro_nome"],
                second=row["sobrenome"], born=row["nascimento"], nationality=row["nacionalidade"],
                roles=roles, foot=row["pe"], height=int(row["altura"]), weight=int(row["peso"]),
                ca=int(row["ca"]), pa=int(row["pa"]), highlights=highlights,
            ))
    return targets


def read_hosts(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as source:
        return [
            {**row, "uid": int(row["uid"]), "ca": int(row["ca"]), "peso": int(row["peso"])}
            for row in csv.DictReader(source)
        ]


def assign_hosts(targets: list[Target], hosts: list[dict]) -> list[tuple[Target, dict]]:
    """Goleiros viram goleiros; o resto, por CA decrescente. Prefere
    jogadores com contrato próprio e peso cadastrado (elenco principal)."""
    def rank(host: dict) -> tuple:
        return (host["vinculo"] != "contrato", host["peso"] == 0, -host["ca"])

    pools = {
        True: sorted((h for h in hosts if "Goalkeeper" in h["posicoes"]), key=rank),
        False: sorted((h for h in hosts if "Goalkeeper" not in h["posicoes"]), key=rank),
    }
    pairs = []
    for target in sorted(targets, key=lambda t: -t.ca):
        pool = pools[target.is_goalkeeper] or pools[not target.is_goalkeeper]
        if not pool:
            raise ValueError(f"Faltam hospedeiros: {len(targets)} jogadores, {len(hosts)} hospedeiros")
        pairs.append((target, pool.pop(0)))
    return pairs


def estimate_attributes(target: Target) -> dict[str, int]:
    profile = PROFILES[ROLE_PROFILE[target.roles[0]]]
    scale = (target.ca + 60) / 220  # 1.0 com CA 160
    values = {name: max(1, min(20, round(base * scale))) for name, base in profile.items()}
    if target.foot == "E":
        values.update({"Left foot": 20, "Right foot": 8})
    elif target.foot == "A":
        values.update({"Left foot": 18, "Right foot": 18})
    else:
        values.update({"Left foot": 8, "Right foot": 20})
    values.update(target.highlights)
    return values


def positions(target: Target) -> dict[str, int]:
    result = {name: 1 for name in POSITION_FIELDS}
    for rank, role in enumerate(target.roles):
        for name, value in ROLE_POSITIONS[role].items():
            value = value if rank == 0 else min(value, 16)
            result[name] = max(result[name], value)
    return result


def build(targets: list[Target], hosts: list[dict], year_shift: int = -20):
    pairs = assign_hosts(targets, hosts)
    lnc_lines = ['# Gerado por scripts/build_squad.py: nomes do elenco']
    players, mapping, warnings = [], [], []
    for target, host in pairs:
        first, common, second = (n.replace('"', "") for n in (target.first, target.common, target.second))
        lnc_lines.append(f'"CHANGE_PLAYER_NAME"\t{host["uid"]}\t"{first}"\t"{common}"\t"{second}"')
        entry = {
            "uid": host["uid"],
            "name": target.display_name,
            "ca": target.ca,
            "pa": target.pa,
            "height": target.height,
            "weight": target.weight,
            "birth_date": target.born,
            "current_reputation": min(10000, target.ca * 50),
            "home_reputation": min(10000, target.ca * 50),
            "world_reputation": min(10000, target.ca * 35),
            "attributes": estimate_attributes(target),
            "positions": positions(target),
        }
        donor = NATIONALITY_DONORS.get(target.nationality)
        if donor:
            entry["nationality_like"] = donor
        else:
            warnings.append(f"{target.display_name}: sem doador para {target.nationality}; nacionalidade não alterada")
        players.append(entry)
        mapping.append({"numero": target.number, "jogador_2026": target.display_name,
                        "uid_hospedeiro": host["uid"], "ca_hospedeiro": host["ca"],
                        "nascido_hospedeiro": host["nascido"]})
    spec = {"year_shift": year_shift, "players": players}
    return "\r\n".join(lnc_lines) + "\r\n", spec, mapping, warnings


def write_outputs(out_dir: Path, name: str, lnc: str, spec: dict, mapping: list[dict]) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "lnc": out_dir / f"{name}.lnc",
        "json": out_dir / f"{name}.json",
        "map": out_dir / f"{name}_hospedeiros.csv",
    }
    paths["lnc"].write_text(lnc, encoding="utf-16")
    paths["json"].write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    with paths["map"].open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=list(mapping[0]))
        writer.writeheader()
        writer.writerows(mapping)
    return paths
