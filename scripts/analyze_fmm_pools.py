from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_fmm_live import analyze  # noqa: E402
from fm06patch.fmm_schema import FMM2_DEFAULT  # noqa: E402


DEFAULT_POOL_ROOT = ROOT / "workspace" / "live_memory" / "fmm_manual_batch"
DEFAULT_PLAYER_SNAPSHOTS = [
    ROOT / "workspace" / "live_memory" / "3100367" / "manual_changes_observed_20261012.json",
    ROOT / "workspace" / "live_memory" / "8076" / "baseline_20261012.json",
    ROOT / "workspace" / "live_memory" / "3300977" / "baseline_20261012.json",
    ROOT / "workspace" / "live_memory" / "321081" / "baseline_20261012.json",
]


def load_snapshot(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def record_bytes(record: dict) -> bytes:
    return bytes.fromhex(record["data_hex"])


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def decode_date(data: bytes, offset: int) -> dict:
    day_of_year_0, year = struct.unpack_from("<HH", data, offset)
    return {"day_of_year_0": day_of_year_0, "year": year}


def player_roots(paths: list[Path]) -> dict[int, dict]:
    roots = {}
    for path in paths:
        if not path.exists():
            continue
        result = analyze(path, FMM2_DEFAULT)
        for address_text in result["objects"]["Player"]:
            uid_address = int(address_text, 16)
            roots[uid_address - 20] = {
                "player_uid": result["player_uid"],
                "player_root_address": uid_address - 20,
                "snapshot": str(path.relative_to(ROOT)),
            }
    return roots


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Liga snapshots de pools Contract/Club/Nation aos objetos Player."
    )
    parser.add_argument("label", help="Rótulo usado por capture_fmm_pools.py.")
    parser.add_argument(
        "--pool-root", type=Path, default=DEFAULT_POOL_ROOT
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "reverse" / "fmm" / "pool_link_analysis.json",
    )
    parser.add_argument(
        "--player-snapshot",
        action="append",
        type=Path,
        dest="player_snapshots",
    )
    args = parser.parse_args()

    snapshots = args.player_snapshots or DEFAULT_PLAYER_SNAPSHOTS
    players = player_roots(snapshots)

    contract_path = args.pool_root / "contract" / f"{args.label}.json"
    club_path = args.pool_root / "club" / f"{args.label}.json"
    nation_path = args.pool_root / "nation" / f"{args.label}.json"
    contracts = load_snapshot(contract_path)["records"]
    clubs = load_snapshot(club_path)["records"]
    nations = load_snapshot(nation_path)["records"]

    club_by_address = {int(row["address"]): row for row in clubs}
    linked_contracts = []
    for row in contracts:
        data = record_bytes(row)
        if len(data) < 36 or u32(data, 0) != int(row["root"]):
            continue
        player_pointer = u32(data, 4)
        if player_pointer not in players:
            continue
        club_pointer = u32(data, 8)
        club = club_by_address.get(club_pointer)
        club_uid = None
        club_ordinal = None
        if club is not None:
            club_data = record_bytes(club)
            club_uid = u32(club_data, 20)
            club_ordinal = u32(club_data, 24)
        wage_raw = u32(data, 16)
        linked_contracts.append(
            {
                **players[player_pointer],
                "contract_address": int(row["address"]),
                "contract_root": f"0x{int(row['root']):08X}",
                "player_pointer_offset": 4,
                "club_pointer_offset": 8,
                "club_pointer": club_pointer,
                "club_public_uid": club_uid,
                "club_internal_ordinal": club_ordinal,
                "wages_raw_offset_16": wage_raw,
                "wages_if_tagged_x10_plus_2": (
                    (wage_raw - 2) // 10 if wage_raw % 10 == 2 else None
                ),
                "started_offset_24": decode_date(data, 24),
                "expires_offset_32": decode_date(data, 32),
            }
        )

    known_nations = []
    wanted_ordinals = {143: "France", 170: "Spain", 187: "Argentina", 189: "Brazil"}
    for row in nations:
        data = record_bytes(row)
        if len(data) < 28 or u32(data, 0) != int(row["root"]):
            continue
        ordinal = u32(data, 24)
        if ordinal in wanted_ordinals:
            known_nations.append(
                {
                    "name": wanted_ordinals[ordinal],
                    "address": int(row["address"]),
                    "public_uid_offset_20": u32(data, 20),
                    "internal_ordinal_offset_24": ordinal,
                }
            )

    payload = {
        "label": args.label,
        "contract_snapshot": str(contract_path.relative_to(ROOT)),
        "club_snapshot": str(club_path.relative_to(ROOT)),
        "nation_snapshot": str(nation_path.relative_to(ROOT)),
        "linked_contracts": linked_contracts,
        "known_nations": known_nations,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Análise salva em {args.output}")
    print(f"Contratos ligados: {len(linked_contracts)}")


if __name__ == "__main__":
    main()
