from __future__ import annotations

import argparse
import json
import struct
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from fm06patch.fmm_schema import FMM2_DEFAULT, describe_schema  # noqa: E402
from live_player_memory import (  # noqa: E402
    find_process_id,
    kernel32,
    make_snapshot,
    open_process,
    read_memory,
    scan_value,
)


PLAYER_UID = 3100367
OUTPUT = ROOT / "workspace" / "live_memory" / "fmm_manual_batch"


STEPS = [
    ("player", "01_height_169", "Height 168 -> 169"),
    ("player", "02_weight_62", "Weight 61 -> 62"),
    ("player", "03_home_rep_8197", "Home Rep. 8198 -> 8197"),
    ("player", "04_current_rep_7997", "Current Rep. 7998 -> 7997"),
    ("player", "05_world_rep_5861", "World Rep. 5862 -> 5861"),
    ("player", "06_morale_19", "Morale 20 -> 19"),
    ("player", "07_fitness_3999", "Fitness 4000 -> 3999"),
    ("player", "08_jadedness_1", "Jadedness 0 -> 1"),
    ("player", "09_match_exercise_7079", "Match Exercise 7080 -> 7079"),
    ("player", "10_adaptability_13", "Adaptability 12 -> 13"),
    ("player", "11_crossing_16", "Crossing 17 -> 16"),
    ("player", "12_dribbling_19", "Dribbling 20 -> 19"),
    ("player", "13_penalty_15", "Penalty 16 -> 15"),
    ("player", "14_creativity_17", "Creativity 18 -> 17"),
    ("player", "15_aggression_5", "Aggression 4 -> 5"),
    ("player", "16_acceleration_18", "Acceleration 19 -> 18"),
    ("player", "17_attacker_19", "Attacker 20 -> 19"),
    ("player", "18_att_mid_16", "Att. Mid. 17 -> 16"),
    ("player", "19_ppm_remove_0", "Desativar Runs With Ball Down Left (índice 0)"),
    ("player", "20_ppm_add_1", "Ativar Runs With Ball Down Right (índice 1)"),
    ("player", "21_ppm_add_31", "Ativar Arrives Late In Opponents Area (índice 31)"),
    ("player", "22_ppm_remove_47", "Desativar Likes To Switch Ball To Other Flank (índice 47)"),
    ("contract", "23_wages_plus_1", "Empréstimo Sevilla: Wages 650000 -> 650001"),
    ("contract", "24_started_plus_1_day", "Empréstimo Sevilla: Started 01/06/2005 -> 02/06/2005"),
    ("contract", "25_expires_plus_1_day", "Empréstimo Sevilla: Expires 30/06/2006 -> 01/07/2006"),
    ("contract", "26_squad_number_8", "Empréstimo Sevilla: Squad Number 7 -> 8"),
    ("contract", "27_release_minus_1", "Contrato Barcelona: Minimum Release 180000000 -> 179999999"),
    ("club", "28_sevilla_reputation_minus_1", "Sevilla Reputation: anote o valor e reduza exatamente 1"),
    ("nation", "29_argentina_reputation_minus_1", "Argentina Reputation: anote o valor e reduza exatamente 1"),
]


def pool_spec(schema: dict, scope: str):
    if scope == "contract":
        return [
            (schema["roots"]["Contract"][0], None, 256),
            (schema["roots"]["Contract"][1], None, 192),
        ]
    name = "Club" if scope == "club" else "Nation"
    roots = schema["roots"][name][:5]
    signature = b"".join(struct.pack("<I", value) for value in roots)
    return [(roots[0], signature, 1024)]


def discover_pool(handle, schema: dict, scope: str) -> list[dict]:
    records = []
    for root, signature, size in pool_spec(schema, scope):
        for address in scan_value(handle, struct.pack("<I", root)):
            if signature is not None:
                candidate = read_memory(handle, address, len(signature))
                if candidate != signature:
                    continue
            records.append({"address": address, "root": root, "size": size})
    records.sort(key=lambda item: item["address"])
    return records


def capture_pool(handle, scope: str, label: str, records: list[dict]) -> None:
    captured = []
    for record in records:
        data = read_memory(handle, record["address"], record["size"])
        if data is None:
            continue
        captured.append(
            {
                "address": record["address"],
                "root": record["root"],
                "size": len(data),
                "data_hex": data.hex(),
            }
        )
    destination = OUTPUT / scope
    destination.mkdir(parents=True, exist_ok=True)
    payload = {
        "scope": scope,
        "label": label,
        "captured_at": datetime.now().astimezone().isoformat(),
        "records": captured,
    }
    (destination / f"{label}.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Captura {scope}/{label}: {len(captured)} registros")


def capture_player(label: str) -> None:
    make_snapshot(PLAYER_UID, f"fmm_batch_{label}", 4096)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fmm", type=Path, default=FMM2_DEFAULT)
    parser.add_argument(
        "--from-step",
        type=int,
        default=1,
        help="Retoma a partir do número indicado, ainda capturando baseline do escopo.",
    )
    args = parser.parse_args()

    schema = describe_schema(args.fmm)
    pid = find_process_id("fm.exe")
    handle = open_process(pid)
    pools: dict[str, list[dict]] = {}
    initialized: set[str] = set()

    print("=" * 78)
    print("RODADA CONTROLADA FMM2 — JAVIER SAVIOLA UID 3100367")
    print("Uma alteração por passo. Não avance a partida. Pressione Enter só depois de aplicar.")
    print("Se o valor exibido divergir do roteiro, NÃO altere; escreva o valor nas notas.")
    print("=" * 78)

    try:
        for number, (scope, label, instruction) in enumerate(STEPS, start=1):
            if number < args.from_step:
                continue
            if scope not in initialized:
                if scope == "player":
                    capture_player(f"{scope}_baseline")
                else:
                    print(f"Descobrindo pool {scope}...")
                    pools[scope] = discover_pool(handle, schema, scope)
                    capture_pool(handle, scope, f"{scope}_baseline", pools[scope])
                initialized.add(scope)

            input(f"\n[{number:02d}/29] No FMM2: {instruction}\nENTER para capturar...")
            if scope == "player":
                capture_player(label)
            else:
                capture_pool(handle, scope, label, pools[scope])

        input(
            "\nRestaure TODOS os valores originais em ordem inversa. "
            "Quando terminar, pressione ENTER para as capturas finais..."
        )
        capture_player("restored_final")
        for scope in ("contract", "club", "nation"):
            if scope not in pools:
                pools[scope] = discover_pool(handle, schema, scope)
            capture_pool(handle, scope, "restored_final", pools[scope])
    finally:
        kernel32.CloseHandle(handle)

    print("\nRodada concluída. Dados em:")
    print(OUTPUT)


if __name__ == "__main__":
    main()
