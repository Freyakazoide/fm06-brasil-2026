"""Captura a memória do jogo em volta de uma pessoa ou de um clube, para eu interpretar.

    python scripts\\capturar.py "Pedro" lesionado               (nome de 2026 ou UID; rótulo)
    python scripts\\capturar.py 322 flamengo_info               (UID de clube ou pessoa)
    python scripts\\capturar.py "Raphael Claus" arbitro --raio 16384

Com o jogo aberto (fm_brasil.exe ou fm.exe), acha todas as cópias do UID na memória e
grava uma janela em volta de cada uma em workspace\\capturas\\<rótulo>\\<UID>.json, com a
frase que você escrever sobre o que a tela mostra ("lesão no joelho, volta em 15/03",
"Instalações de treino: Excelentes"). O nome é procurado nas listas do mod
(workspace\\mods: jogadores, comissão e árbitros de 2026; identidade_fm06 para clubes).
Depois zipe a pasta workspace\\capturas e mande. Não muda nada no jogo.
"""

from __future__ import annotations

import argparse
import csv
import json
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

OUT = ROOT / "workspace" / "capturas"
MODS = ROOT / "workspace" / "mods"
LISTS = (   # (arquivo, coluna do nome, coluna do UID)
    (MODS / "brasil_2026_jogadores_hospedeiros.csv", "jogador_2026", "uid_hospedeiro"),
    (MODS / "comissao_2026_hospedeiros.csv", "nome_2026", "uid"),
    (MODS / "arbitros_2026_hospedeiros.csv", "arbitro_2026", "uid"),
    (ROOT / "data" / "brasil" / "clubes" / "identidade_fm06.csv", "clube_2026", "uid_jogo"),
)


def find_uid(key: str) -> int:
    if key.isdigit():
        return int(key)
    found = []
    for path, name, uid in LISTS:
        if path.exists():
            for row in csv.DictReader(path.open(encoding="utf-8-sig")):
                if row.get(name, "").strip().casefold() == key.strip().casefold():
                    found.append((int(row[uid]), path.name, {k: v for k, v in row.items() if k != uid}))
    if len({uid for uid, _, _ in found}) == 1:
        return found[0][0]
    if not found:
        sys.exit(f"[ERRO] '{key}' não está nas listas do mod; use o UID.")
    print(f"'{key}' tem mais de um UID; rode de novo com o número:")
    for uid, source, row in found:
        print(f"   {uid}  ({source}: {row})")
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("quem", help="UID ou nome de 2026 (jogador, técnico, árbitro ou clube)")
    parser.add_argument("rotulo", help="nome da captura (ex.: lesionado, flamengo_info)")
    parser.add_argument("--raio", type=int, default=8192, help="bytes antes e depois de cada cópia do UID")
    parser.add_argument("--nota", help="o que a tela mostra (senão o script pergunta)")
    args = parser.parse_args()

    from live_player_memory import find_process_id, open_process, read_memory, scan_value

    uid = find_uid(args.quem)
    for exe in ("fm_brasil.exe", "fm.exe"):
        try:
            pid = find_process_id(exe)
            break
        except RuntimeError:
            continue
    else:
        sys.exit("[ERRO] abra o fm_brasil.exe antes (com o jogo carregado).")
    note = args.nota if args.nota is not None else input("O que a tela mostra (uma linha): ")
    handle = open_process(pid)
    print(f"Procurando o UID {uid} na memória...", flush=True)
    hits = scan_value(handle, struct.pack("<I", uid))
    windows = []
    for address in hits:
        start = max(0, address - args.raio)
        data = read_memory(handle, start, 2 * args.raio + 4)
        if data:
            windows.append({"uid_address": address, "window_address": start, "data_hex": data.hex()})
    folder = OUT / args.rotulo
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{uid}.json"
    path.write_text(json.dumps({"uid": uid, "quem": args.quem, "rotulo": args.rotulo, "nota": note, "exe": exe,
                                "quando": time.strftime("%Y-%m-%d %H:%M:%S"), "raio": args.raio,
                                "janelas": windows}, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] {len(windows)} cópias do UID {uid} gravadas em {path}")


if __name__ == "__main__":
    main()
