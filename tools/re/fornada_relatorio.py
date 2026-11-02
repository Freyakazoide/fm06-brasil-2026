"""Relatório da fornada no jogo aberto: os garotos de 16 anos criados no dia, por clube, com a
base e a captação do clube (ficha C14).

    python tools\\re\\fornada_relatorio.py

Lê a tabela de pessoas ([0x014EAA54]): jogador (ACTUAL_PLAYER, assinatura 0x010F1034) com UID
de tempo de jogo (≥ 102.000.000) e nascido no ano do motor − 16. O clube vem do UID em
jogador − 48 e a base/captação de CLUB+0xE1/+0xE0 na tabela de clubes ([0x014EAA30]).
"""

from __future__ import annotations

import statistics
import struct
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "re"))
sys.path.insert(0, str(ROOT / "scripts"))

import chamada_remota as cr  # noqa: E402
from live_player_memory import read_memory  # noqa: E402

PLAYER_VTABLE = 0x010F1034
RUNTIME_UID = 102_000_000


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--uid-min", type=int, default=RUNTIME_UID,
                        help="só garotos com UID acima deste (peneira: o maior UID da fornada de janeiro)")
    parser.add_argument("--pa-min", type=int, default=0, help="só garotos com PA a partir deste")
    args = parser.parse_args()
    _, h = cr.game()
    u = lambda at: struct.unpack("<I", read_memory(h, at, 4))[0]

    def table(root: int) -> list[int]:
        inner = u(u(root) + 4)
        count, items = u(inner + 8), u(inner + 4)
        return list(struct.unpack(f"<{count}I", read_memory(h, items, 4 * count)))

    year = struct.unpack("<H", read_memory(h, 0x014EAB3A, 2))[0]
    clubs = {}
    for club in table(0x014EAA30):
        if club:
            raw = read_memory(h, club, 0xF0)
            if raw:
                clubs[struct.unpack_from("<I", raw, 0x14)[0]] = (raw[0xE1], raw[0xE0], club)
    by_club = defaultdict(list)
    top_uid = 0
    for person in table(0x014EAA54):
        raw = read_memory(h, person - 0xD0, 0x1C8) if person else None
        if not raw or struct.unpack_from("<I", raw, 0xD0)[0] != PLAYER_VTABLE:
            continue
        uid = struct.unpack_from("<I", raw, 0xD0 + 0x14)[0]
        born = struct.unpack_from("<H", raw, 0xD0 + 0x14 + 52 + 2)[0]
        if uid < args.uid_min or born != year - 16:
            continue
        ca, pa = struct.unpack_from("<HH", raw, 0xD0 + 0x14 - 204)
        if pa < args.pa_min:
            continue
        top_uid = max(top_uid, uid)
        club = struct.unpack_from("<I", raw, 0xD0 - 48)[0]
        by_club[club].append((ca, pa))
    rows = []
    for club, players in by_club.items():
        youth, recruitment, _ = clubs.get(club, (0, 0, 0))
        pas = [pa for _, pa in players]
        rows.append((youth + recruitment, club, youth, recruitment, len(players), statistics.mean(pas),
                     sum(pa >= 150 for pa in pas), max(pas)))
    rows.sort(reverse=True)
    total = sum(r[4] for r in rows)
    print(f"{total} garotos de 16 anos criados em tempo de jogo, em {len(rows)} clubes (ano do motor {year}); "
          f"maior UID {top_uid}")
    if not rows:
        return
    print(f"{'clube':>9} {'base':>4} {'capt':>4} {'qtd':>3} {'PA médio':>8} {'PA≥150':>6} {'maior':>5}")
    for row in rows[:15] + [None] + rows[-10:]:
        if row is None:
            print("      ...")
            continue
        q, club, youth, recruitment, n, mean, stars, best = row
        print(f"{club:>9} {youth:>4} {recruitment:>4} {n:>3} {mean:>8.1f} {stars:>6} {best:>5}")
    for low, high in ((0, 12), (13, 20), (21, 28), (29, 40)):
        group = [r for r in rows if low <= r[0] <= high]
        if group:
            n = sum(r[4] for r in group)
            print(f"base+captação {low:2}–{high:2}: {len(group):3} clubes, PA médio "
                  f"{sum(r[5] * r[4] for r in group) / n:5.1f}, PA≥150 por clube {sum(r[6] for r in group) / len(group):.2f}")


if __name__ == "__main__":
    main()
