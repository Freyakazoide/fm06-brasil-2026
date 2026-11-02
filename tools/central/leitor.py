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

PEOPLE, PLAYING = 0x014EAA54, 0x014EAA6C
HUMAN_VT, PLAYER_VT = 0x010F6F8C, 0x010F1034
TODAY_DAY, TODAY_YEAR = 0x014EAB38, 0x014EAB3A
JUDGES = 0x015C15F0                       # .fm26+0xD5F0
TEAM_KIND = {0: "Principal", 3: "B", 18: "Sub-20"}   # byte em time+0x3C
YEAR_SHIFT = 20                           # ano do motor + 20 = ano mostrado (ano_exibido)
POSITIONS = {                             # posição exibida -> atributo DIRECT (1..20)
    "GR": "Goalkeeper", "DD": "Right Def.", "DC": "Center Def.", "DE": "Left Def.",
    "AD": "Wing B.R.", "AE": "Wing B.L.", "MD": "Def. C.M.", "M D": "Mid. Right",
    "M C": "Mid. Center", "M E": "Mid. Left", "MA D": "Att. M.R.", "MA C": "Att. M.C.",
    "MA E": "Att. M.L.", "PL": "Att. Center",
}


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
    posicoes: list[str] = field(default_factory=list)
    atributos: dict[str, int] = field(default_factory=dict)


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
        uid = jogo.u32(r + 0x14)
        day, year = struct.unpack("<HH", jogo.raw(r + 0x14 + lp.BORN_REL, 4))
        born = dt.date(year, 1, 1) + dt.timedelta(days=day)
        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        if age > max_age:
            continue
        ca, pa = jogo.u16(r + 0x14 - 204), jogo.u16(r + 0x14 - 202)
        values: dict[str, int] = {}
        block = jogo.u32(r - 32)                                    # PLAYING_DATA do jogador
        if block:
            raw = jogo.raw(block, 0x70)
            for a in attributes.values():
                values[a.name] = lp.decode_attribute(a, raw[0x14 + a.rel], ca)
        positions = [short for short, name in POSITIONS.items() if values.get(name, 0) >= 15]
        kind = jogo.raw(team + 0x3C, 1)[0]
        teams.setdefault(team, TEAM_KIND.get(kind, f"time tipo {kind}"))
        out.append(Jovem(
            uid=uid, nome=f"{jogo.text(jogo.u32(r + 44))} {jogo.text(jogo.u32(r + 48))}".strip(),
            apelido=jogo.text(jogo.u32(r + 52)), idade=age,
            nascimento=born.replace(year=born.year + YEAR_SHIFT).isoformat(), time=teams[team],
            ca=ca, pa=pa, hab=stars(uid, ca, ability_judge, 0x2545F491),
            pot=stars(uid, pa, potential_judge, 0x9E3779B9), posicoes=positions, atributos=values))
    info = {"data": today.replace(year=today.year + YEAR_SHIFT).isoformat(), "time_humano": f"0x{my_team:08X}",
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
