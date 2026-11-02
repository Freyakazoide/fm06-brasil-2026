"""Central de Desenvolvimento externa: leitura do jogo aberto (só leitura).

    python tools\\central\\leitor.py                (jovens do clube do humano, até 19 anos)
    python tools\\central\\leitor.py --idade 99 --json saida.json

Abre o fm_brasil.exe só para leitura (PROCESS_VM_READ) e monta, a partir das tabelas do banco na
memória, os jogadores do clube do humano: nome, idade, time, posições, CA/PA, atributos e as
estrelas da comissão calculadas como no patch centro_colunas (ficha T1).

Mapa usado (conferido nas fichas C14 e T1):
- tabelas: pessoas [0x14EAA54], PLAYING_DATA [0x14EAA6C]; T = [[tabela]+4], itens [T+4], qtd [T+8];
- pessoa R: assinatura (vtable em R), UID em R+0x14, nomes em R+44/48/52 (PERSON_NAME, texto UTF-16
  em [[nome+0x24]+8]), nascimento em UID+52 (dia, ano do motor), time em R+0x74, clube em
  time+0x38; CA/PA em UID-204/-202; PLAYING_DATA em [R-32] (conferido em 300 jogadores);
- time: UID em +0x14, tipo em +0x3C (0 principal, 3 B, 18 Sub-20); clube: times em [+0x68], qtd +0x6C;
- PLAYING_DATA: UID no bloco+0x14, atributos relativos ao UID (reverse/fmm/playing_attributes_layout);
- humano: vtable 0x10F6F8C; jogador: 0x10F1034;
- data do jogo: dia (base 0) em 0x14EAB38, ano do motor em 0x14EAB3A;
- cache da comissão (patch centro_colunas): .fm26+0xD5F0 (+4 melhor Npja, +8 melhor Npjp).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import struct
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
from live_player_memory import find_process_id, open_process, read_memory  # noqa: E402
from fm06patch import live_player as lp  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjunto  # noqa: E402
import analitica  # noqa: E402

PEOPLE, PLAYING = 0x014EAA54, 0x014EAA6C
HUMAN_VT, PLAYER_VT = 0x010F6F8C, 0x010F1034
TODAY_DAY, TODAY_YEAR = 0x014EAB38, 0x014EAB3A
JUDGES = 0x015C15F0                       # .fm26+0xD5F0
TEAM_KIND = {0: "Principal", 3: "B", 18: "Sub-20"}   # byte em time+0x3C
# Contrato (conferido em 02/11 no save do Figueirense): [R+0x98] é um bloco de 8 bytes com o
# ponteiro do contrato C. C+0x08 clube; C+0x10 salário bruto (semanal); C+0x18/0x1A início (dia,
# ano do motor); C+0x20/0x22 fim (ano 1900 = sem data); byte C+0x31 número da camisa (igual ao Psnu
# do jogo em 14 de 14 jogadores; 255 = sem número).
CONTRACT_PTR = 0x98
WAGE_TO_MONTH_BRL = 750 / 38              # calibrado: Otacílio, bruto 38 = "R$750 por mês" na ficha
YEAR_SHIFT = 20                           # ano do motor + 20 = ano mostrado (ano_exibido)
POSITIONS = {                             # posição exibida -> atributo DIRECT (1..20)
    "GR": "Goalkeeper", "DD": "Right Def.", "DC": "Center Def.", "DE": "Left Def.",
    "AD": "Wing B.R.", "AE": "Wing B.L.", "MD": "Def. C.M.", "M D": "Mid. Right",
    "M C": "Mid. Center", "M E": "Mid. Left", "MA D": "Att. M.R.", "MA C": "Att. M.C.",
    "MA E": "Att. M.L.", "PL": "Att. Center",
}
PREFERRED_MOVES = json.loads(
    (ROOT / "reverse" / "fmm" / "preferred_moves_layout.json").read_text(encoding="utf-8")
)["moves"]


@dataclass
class Jovem:
    uid: int
    nome: str
    apelido: str
    idade: int
    nascimento: str
    time: str
    ca: int
    pa: int
    hab: int                               # estrelas da comissão, 0..10
    pot: int
    altura: int = 0
    peso: int = 0
    moral: int = 0
    condicao_raw: int = 0
    ritmo_raw: int = 0
    cansaco_raw: int = 0
    valor_pedido_raw: int = 0
    numero: int | None = None                                 # número da camisa no time
    salario_raw: int = 0
    salario_mes: int = 0                                      # ≈ R$ por mês (calibrado)
    contrato_inicio: str | None = None
    contrato_fim: str | None = None                           # None: sem data de fim
    reputacao: dict[str, int] = field(default_factory=dict)
    internacional: dict[str, int] = field(default_factory=dict)
    pe_preferido: str = ""
    posicoes: list[str] = field(default_factory=list)
    familiaridades: dict[str, int] = field(default_factory=dict)
    movimentos: list[str] = field(default_factory=list)
    atributos: dict[str, int] = field(default_factory=dict)
    futuro: dict[str, int] = field(default_factory=dict)      # projeção do olheiro no auge
    nivel: str = ""                                           # onde pode chegar
    adjunto: dict = field(default_factory=dict)               # melhor posição e foco de treino
    analise: dict = field(default_factory=dict)                # indicadores explicáveis da Central


# Futuro potencial (opinião do olheiro): o PA que ele enxerga é o das estrelas (pot × 20, com o erro
# do avaliador). Os atributos RELATIVE são guardados em relação ao CA (live_player.relative_base):
# com o CA no PA visto, o próprio jogo daria esses valores. Os ABSOLUTE não acompanham o CA: ganho
# estimado de treino, proporcional ao que falta (PA visto − CA), maior nos físicos.
GROWTH = {"Acceleration": .35, "Pace": .35, "Agility": .4, "Balance": .4, "Jumping": .45, "Strength": .55,
          "Stamina": .55, "Natural fit.": .3, "Penalty": .7, "Corner": .7, "Set Pieces": .7, "Throwing": .7}
LEVELS = ((170, "nível de seleção e de clube grande da Europa"), (150, "titular de time grande da Série A"),
          (130, "jogador de Série A"), (110, "titular de Série B"), (90, "jogador de Série C e D"),
          (0, "jogador de estaduais"))


def future(raw: bytes, attributes, ca: int, seen_pa: int) -> dict[str, int]:
    out = {}
    for a in attributes:
        now = lp.decode_attribute(a, raw[0x14 + a.rel], ca)
        if a.kind == "RELATIVE":
            out[a.name] = max(now, lp.decode_attribute(a, raw[0x14 + a.rel], seen_pa))
        elif a.kind == "ABSOLUTE":
            out[a.name] = min(20, now + round((seen_pa - ca) / 10 * GROWTH.get(a.name, .3)))
        else:
            out[a.name] = now
    return out


class Jogo:
    def __init__(self) -> None:
        self.handle = open_process(find_process_id("fm_brasil.exe"))

    def raw(self, at: int, size: int) -> bytes:
        data = read_memory(self.handle, at, size)
        if data is None or len(data) < size:
            raise OSError(f"leitura falhou em 0x{at:08X}")
        return data

    def u32(self, at: int) -> int:
        return struct.unpack("<I", self.raw(at, 4))[0]

    def u16(self, at: int) -> int:
        return struct.unpack("<H", self.raw(at, 2))[0]

    def table(self, root: int) -> list[int]:
        t = self.u32(self.u32(root) + 4)
        items, count = self.u32(t + 4), self.u32(t + 8)
        return list(struct.unpack(f"<{count}I", self.raw(items, 4 * count)))

    def text(self, person_name: int) -> str:
        if not person_name:
            return ""
        raw = read_memory(self.handle, self.u32(self.u32(person_name + 0x24) + 8), 80) or b""
        return raw.decode("utf-16-le", "replace").split("\x00")[0]

    def today(self) -> dt.date:
        return dt.date(self.u16(TODAY_YEAR), 1, 1) + dt.timedelta(days=self.u16(TODAY_DAY))


def stars(uid: int, value: int, judge: int, salt: int) -> int:
    """Mesma conta do desvio do executável (centro.hook_code)."""
    spread = (21 - max(1, judge)) * 3 // 2
    h = (((uid ^ salt) * 0x9E3779B1) & 0xFFFFFFFF) >> 8
    tenths = min(100, max(0, value // 2 + h % (2 * spread + 1) - spread))
    return (tenths + 5) // 10


def contract(jogo: Jogo, r: int) -> dict:
    """Número, salário e datas do contrato do jogador (vazio se não houver)."""
    try:
        c = jogo.u32(jogo.u32(r + CONTRACT_PTR))
        if not c:
            return {}
        def date(at: int) -> str | None:
            day, year = jogo.u16(c + at), jogo.u16(c + at + 2)
            if year < 1950:
                return None
            return (dt.date(year + YEAR_SHIFT, 1, 1) + dt.timedelta(days=day)).isoformat()
        number, wage = jogo.raw(c + 0x31, 1)[0], jogo.u32(c + 0x10)
        return {"numero": None if number == 255 else number, "salario_raw": wage,
                "salario_mes": int(round(wage * WAGE_TO_MONTH_BRL, -1)),
                "contrato_inicio": date(0x18), "contrato_fim": date(0x20)}
    except OSError:
        return {}


def preferred_moves(jogo: Jogo, uid_at: int) -> list[str]:
    """Movimentos preferidos do bitset já mapeado em reverse/fmm."""
    raw = jogo.raw(uid_at - 48, 6)
    return [move.get("visible_portuguese") or move["move_name"] for move in PREFERRED_MOVES
            if raw[move["fmm_index"] // 8] & (1 << (move["fmm_index"] % 8))]


def jovens(max_age: int = 19) -> tuple[list[Jovem], dict]:
    jogo = Jogo()
    people = jogo.table(PEOPLE)
    human = next(p for p in people if p and jogo.u32(p) == HUMAN_VT)
    my_team = jogo.u32(human + 0x74)
    my_club = jogo.u32(my_team + 0x38)
    today = jogo.today()
    ability_judge, potential_judge = jogo.u32(JUDGES + 4), jogo.u32(JUDGES + 8)
    attributes = {a.fmm_index: a for a in lp.load_attributes().values()}
    teams: dict[int, str] = {}
    out = []
    for r in people:
        if not r or jogo.u32(r) != PLAYER_VT:
            continue
        team = jogo.u32(r + 0x74)
        if not team or jogo.u32(team + 0x38) != my_club:
            continue
        uid_at = r + 0x14
        uid = jogo.u32(uid_at)
        day, year = struct.unpack("<HH", jogo.raw(r + 0x14 + lp.BORN_REL, 4))
        born = dt.date(year, 1, 1) + dt.timedelta(days=day)
        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        if age > max_age:
            continue
        ca, pa = jogo.u16(uid_at - 204), jogo.u16(uid_at - 202)
        values: dict[str, int] = {}
        projected: dict[str, int] = {}
        pot = stars(uid, pa, potential_judge, 0x9E3779B9)
        seen_pa = max(ca, min(200, pot * 20))
        block = jogo.u32(r - 32)                                    # PLAYING_DATA do jogador
        if block:
            raw = jogo.raw(block, 0x70)
            for a in attributes.values():
                values[a.name] = lp.decode_attribute(a, raw[0x14 + a.rel], ca)
            projected = future(raw, attributes.values(), ca, seen_pa)
        familiarities = {short: values.get(name, 0) for short, name in POSITIONS.items()}
        positions = [short for short, value in familiarities.items() if value >= 15]
        left, right = values.get("Left foot", 0), values.get("Right foot", 0)
        foot = "ambos" if min(left, right) >= 15 else "esquerdo" if left > right else "direito"
        moral = jogo.raw(uid_at - 184, 1)[0]
        assistant = adjunto.analyse(values, projected) if values else {}
        kind = jogo.raw(team + 0x3C, 1)[0]
        team_name = teams.setdefault(team, TEAM_KIND.get(kind, f"time tipo {kind}"))
        analysis = analitica.analyse_player(
            age=age, team=team_name,
            hab=stars(uid, ca, ability_judge, 0x2545F491), pot=pot, moral=moral,
            adjunto=assistant, ability_judge=ability_judge, potential_judge=potential_judge)
        out.append(Jovem(
            uid=uid, nome=f"{jogo.text(jogo.u32(r + 44))} {jogo.text(jogo.u32(r + 48))}".strip(),
            apelido=jogo.text(jogo.u32(r + 52)), idade=age,
            nascimento=born.replace(year=born.year + YEAR_SHIFT).isoformat(), time=team_name,
            ca=ca, pa=pa, hab=stars(uid, ca, ability_judge, 0x2545F491), pot=pot,
            altura=jogo.u16(uid_at - 76), peso=jogo.u16(uid_at - 78), moral=moral,
            condicao_raw=jogo.u16(uid_at - 216), ritmo_raw=jogo.u16(uid_at - 214),
            cansaco_raw=jogo.u16(uid_at - 212), valor_pedido_raw=jogo.u32(uid_at - 192), **contract(jogo, r),
            reputacao={"local": jogo.u16(uid_at - 210), "atual": jogo.u16(uid_at - 208),
                       "mundial": jogo.u16(uid_at - 206)},
            internacional={"jogos": jogo.raw(uid_at + 72, 1)[0], "gols": jogo.raw(uid_at + 74, 1)[0],
                           "sub21_jogos": jogo.raw(uid_at + 73, 1)[0], "sub21_gols": jogo.raw(uid_at + 75, 1)[0]},
            pe_preferido=foot, posicoes=positions, familiaridades=familiarities,
            movimentos=preferred_moves(jogo, uid_at), atributos=values, futuro=projected,
            nivel=next(text for floor, text in LEVELS if seen_pa >= floor),
            adjunto=assistant, analise=analysis))
    info = {"data": today.replace(year=today.year + YEAR_SHIFT).isoformat(), "time_uid": jogo.u32(my_team + 0x14),
            "time_humano": f"0x{my_team:08X}",
            "clube": f"0x{my_club:08X}", "avaliador_hab": ability_judge, "avaliador_pot": potential_judge}
    return sorted(out, key=lambda j: (-j.pot, -j.hab, j.nome)), info


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--idade", type=int, default=19)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    lista, info = jovens(args.idade)
    print(info)
    for j in lista:
        print(f"{j.apelido or j.nome:24} {j.idade:2} {j.time:16} CA {j.ca:3} PA {j.pa:3} "
              f"Hab {j.hab:2} Pot {j.pot:2} {'/'.join(j.posicoes)}")
    if args.json:
        args.json.write_text(json.dumps({"info": info, "jovens": [asdict(j) for j in lista]},
                                        ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[OK] {len(lista)} jovens em {args.json}")


if __name__ == "__main__":
    main()
