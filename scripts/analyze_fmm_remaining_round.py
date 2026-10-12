from __future__ import annotations

import argparse
import csv
import json
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_fmm_live import analyze  # noqa: E402
from fm06patch.fmm_schema import FMM2_DEFAULT, describe_schema, object_hits  # noqa: E402


ROUND = "remaining_round_20261012"
MEMORY = ROOT / "workspace" / "live_memory"
BATCH = MEMORY / "fmm_manual_batch"
MANIFEST = BATCH / f"{ROUND}_manifest.json"
PLAYER_DIR = MEMORY / "3100367"
REPORT_JSON = ROOT / "reverse" / "fmm" / "remaining_round_analysis.json"
REPORT_CSV = ROOT / "reverse" / "fmm" / "remaining_round_analysis.csv"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def player_path(label: str) -> Path:
    return PLAYER_DIR / f"fmm_batch_{ROUND}_{label}.json"


def pool_path(scope: str, label: str) -> Path:
    return BATCH / scope / f"{ROUND}_{label}.json"


def hit_byte_map(snapshot: dict) -> dict[int, int]:
    result: dict[int, int] = {}
    for hit in snapshot["hits"]:
        start = int(hit["window_address"])
        data = bytes.fromhex(hit["data_hex"])
        for index, value in enumerate(data):
            result[start + index] = value
    return result


def pool_byte_map(snapshot: dict) -> dict[int, int]:
    result: dict[int, int] = {}
    for record in snapshot["records"]:
        start = int(record["address"])
        data = bytes.fromhex(record["data_hex"])
        for index, value in enumerate(data):
            result[start + index] = value
    return result


def byte_changes(before: dict[int, int], after: dict[int, int]) -> list[tuple[int, int, int]]:
    return [
        (address, before[address], after[address])
        for address in sorted(before.keys() & after.keys())
        if before[address] != after[address]
    ]


def change_runs(changes: list[tuple[int, int, int]]) -> list[dict]:
    runs: list[list[tuple[int, int, int]]] = []
    for change in changes:
        if not runs or change[0] != runs[-1][-1][0] + 1:
            runs.append([change])
        else:
            runs[-1].append(change)
    result = []
    for run in runs:
        old = bytes(row[1] for row in run)
        new = bytes(row[2] for row in run)
        item = {
            "address": run[0][0],
            "size": len(run),
            "before_hex": old.hex(),
            "after_hex": new.hex(),
        }
        # A run records only changed bytes. Decode integers only when the whole
        # candidate scalar changed contiguously; single-byte fields are exact.
        if len(run) in (1, 2, 4):
            item["before_unsigned_le"] = int.from_bytes(old, "little")
            item["after_unsigned_le"] = int.from_bytes(new, "little")
        result.append(item)
    return result


def exact_records(snapshot: dict, root: int) -> list[dict]:
    rows = []
    for row in snapshot["records"]:
        data = bytes.fromhex(row["data_hex"])
        if len(data) >= 4 and u32(data, 0) == root:
            rows.append({**row, "data": data})
    return rows


def find_public_uid(snapshot: dict, root: int, uid: int) -> dict:
    matches = [row for row in exact_records(snapshot, root) if u32(row["data"], 20) == uid]
    if len(matches) != 1:
        raise ValueError(f"UID {uid}: esperava 1 objeto, encontrei {len(matches)}")
    return matches[0]


def annotate_ranges(runs: list[dict], ranges: list[dict]) -> list[dict]:
    result = []
    for run in runs:
        item = dict(run)
        address = int(run["address"])
        matches = [row for row in ranges if row["start"] <= address < row["end"]]
        if matches:
            target = min(matches, key=lambda row: row["end"] - row["start"])
            item["object"] = target["name"]
            item["relative_offset"] = address - target["base"]
            item["inside_expected_target"] = bool(target.get("expected", False))
        result.append(item)
    return result


def player_objects(path: Path, schema: dict) -> tuple[dict, list[dict]]:
    snapshot = load(path)
    objects = {}
    ranges = []
    bounds = {"Player": (-256, 456), "PData": (-20, 36), "Playing": (-20, 112)}
    for name in ("Player", "PData", "Playing"):
        hits = object_hits(snapshot, schema["roots"][name][:5])
        if len(hits) != 1:
            continue
        uid_address = int(hits[0]["uid_address"])
        objects[name] = uid_address
        low, high = bounds[name]
        ranges.append(
            {
                "name": name,
                "base": uid_address,
                "start": uid_address + low,
                "end": uid_address + high,
                "expected": True,
            }
        )
    return objects, ranges


def main() -> None:
    parser = argparse.ArgumentParser(description="Analisa a rodada manual restante do FMM2.")
    parser.add_argument("--fmm", type=Path, default=FMM2_DEFAULT)
    parser.add_argument("--output", type=Path, default=REPORT_JSON)
    parser.add_argument("--csv", type=Path, default=REPORT_CSV)
    args = parser.parse_args()

    schema = describe_schema(args.fmm)
    manifest = load(MANIFEST)
    captured = [row for row in manifest["results"] if row["status"] == "captured"]

    player_baseline_path = player_path("player_baseline")
    player_baseline = load(player_baseline_path)
    player_objects_found, player_ranges = player_objects(player_baseline_path, schema)
    player_root_address = player_objects_found["Player"] - 20

    club_baseline = load(pool_path("club", "club_baseline"))
    nation_baseline = load(pool_path("nation", "nation_baseline"))
    contract_baseline = load(pool_path("contract", "contract_baseline"))
    sevilla = find_public_uid(club_baseline, schema["roots"]["Club"][0], 1759)
    argentina = find_public_uid(nation_baseline, schema["roots"]["Nation"][0], 1649)
    spain = find_public_uid(nation_baseline, schema["roots"]["Nation"][0], 796)

    club_records = exact_records(club_baseline, schema["roots"]["Club"][0])
    club_ranges = []
    for row in club_records:
        data = row["data"]
        club_ranges.append(
            {
                "name": f"Club UID {u32(data, 20)} ordinal {u32(data, 24)}",
                "base": int(row["address"]),
                "start": int(row["address"]),
                "end": int(row["address"]) + 440,
                "expected": int(row["address"]) == int(sevilla["address"]),
            }
        )

    nation_records = exact_records(nation_baseline, schema["roots"]["Nation"][0])
    nation_ranges = []
    for row in nation_records:
        data = row["data"]
        nation_ranges.append(
            {
                "name": f"Nation UID {u32(data, 20)} ordinal {u32(data, 24)}",
                "base": int(row["address"]),
                "start": int(row["address"]),
                "end": int(row["address"]) + 700,
                "expected": int(row["address"]) == int(argentina["address"]),
            }
        )

    club_by_address = {int(row["address"]): row for row in club_records}
    linked_contracts = []
    contract_ranges = []
    for root, stride in (
        (schema["roots"]["Contract"][0], 120),
        (schema["roots"]["Contract"][1], 72),
    ):
        for row in exact_records(contract_baseline, root):
            data = row["data"]
            if u32(data, 4) != player_root_address:
                continue
            club_pointer = u32(data, 8)
            club = club_by_address.get(club_pointer)
            club_uid = u32(club["data"], 20) if club else None
            name = f"Contract root 0x{root:08X} club UID {club_uid}"
            target = {
                "name": name,
                "base": int(row["address"]),
                "start": int(row["address"]),
                "end": int(row["address"]) + stride,
                "expected": club_uid in (1759, 1708),
                "root": root,
                "club_uid": club_uid,
            }
            linked_contracts.append(target)
            contract_ranges.append(target)

    sequences: dict[str, list[dict]] = {scope: [] for scope in ("player", "contract", "club", "nation")}
    previous_paths = {
        "player": player_baseline_path,
        "contract": pool_path("contract", "contract_baseline"),
        "club": pool_path("club", "club_baseline"),
        "nation": pool_path("nation", "nation_baseline"),
    }
    ranges = {
        "player": player_ranges,
        "contract": contract_ranges,
        "club": club_ranges,
        "nation": nation_ranges,
    }
    cache: dict[Path, dict[int, int]] = {}

    def memory_map(scope: str, path: Path) -> dict[int, int]:
        if path not in cache:
            snapshot = load(path)
            cache[path] = hit_byte_map(snapshot) if scope == "player" else pool_byte_map(snapshot)
        return cache[path]

    for step in captured:
        scope = step["scope"]
        current = player_path(step["label"]) if scope == "player" else pool_path(scope, step["label"])
        before = previous_paths[scope]
        runs = change_runs(byte_changes(memory_map(scope, before), memory_map(scope, current)))
        sequences[scope].append(
            {
                **step,
                "before_snapshot": str(before.relative_to(ROOT)),
                "after_snapshot": str(current.relative_to(ROOT)),
                "changed_byte_count": sum(row["size"] for row in runs),
                "change_runs": annotate_ranges(runs, ranges[scope]),
            }
        )
        previous_paths[scope] = current

    restoration = {}
    for scope in sequences:
        baseline = player_baseline_path if scope == "player" else pool_path(scope, f"{scope}_baseline")
        final = player_path("restored_final") if scope == "player" else pool_path(scope, "restored_final")
        runs = change_runs(byte_changes(memory_map(scope, baseline), memory_map(scope, final)))
        restoration[scope] = {
            "baseline_snapshot": str(baseline.relative_to(ROOT)),
            "final_snapshot": str(final.relative_to(ROOT)),
            "changed_byte_count": sum(row["size"] for row in runs),
            "change_runs": annotate_ranges(runs, ranges[scope]),
        }

    decoded_baseline = analyze(player_baseline_path, args.fmm)
    decoded_final = analyze(player_path("restored_final"), args.fmm)
    payload = {
        "round": ROUND,
        "manifest_status": manifest["status"],
        "fmm_sha256": schema["sha256"],
        "target_build": schema["target_build"],
        "targets": {
            "player_uid": int(player_baseline["player_uid"]),
            "player_objects": {name: f"0x{address:08X}" for name, address in player_objects_found.items()},
            "player_root_address": f"0x{player_root_address:08X}",
            "sevilla_club_address": f"0x{int(sevilla['address']):08X}",
            "argentina_nation_address": f"0x{int(argentina['address']):08X}",
            "spain_nation_address": f"0x{int(spain['address']):08X}",
            "linked_contracts": [
                {
                    "name": row["name"],
                    "address": f"0x{row['base']:08X}",
                    "root": f"0x{row['root']:08X}",
                    "club_uid": row["club_uid"],
                }
                for row in linked_contracts
            ],
        },
        "steps": sequences,
        "restoration": restoration,
        "decoded_player_restored": all(
            decoded_baseline[key] == decoded_final[key]
            for key in ("player_fields", "personality", "playing_attributes")
        ),
        "decoded_player_baseline": decoded_baseline,
        "decoded_player_final": decoded_final,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with args.csv.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(
            destination,
            fieldnames=(
                "scope",
                "number",
                "label",
                "address",
                "object",
                "relative_offset",
                "inside_expected_target",
                "size",
                "before_hex",
                "after_hex",
                "before_unsigned_le",
                "after_unsigned_le",
            ),
        )
        writer.writeheader()
        for scope, steps in sequences.items():
            for step in steps:
                for run in step["change_runs"]:
                    writer.writerow(
                        {
                            "scope": scope,
                            "number": step["number"],
                            "label": step["label"],
                            **{key: value for key, value in run.items() if key != "address"},
                            "address": f"0x{int(run['address']):08X}",
                        }
                    )

    print(f"Relatório JSON: {args.output}")
    print(f"Relatório CSV: {args.csv}")
    for scope, steps in sequences.items():
        print(f"{scope}: {len(steps)} passos capturados")
        for step in steps:
            targeted = [row for row in step["change_runs"] if row.get("inside_expected_target")]
            summary = ", ".join(
                f"{row.get('object')} {row.get('relative_offset'):+} "
                f"{row['before_hex']}->{row['after_hex']}"
                for row in targeted
            ) or "nenhuma mudança no alvo"
            print(f"  {step['number']:02d} {step['label']}: {summary}")
        restored_target = [
            row for row in restoration[scope]["change_runs"] if row.get("inside_expected_target")
        ]
        print(f"  restauração: {len(restored_target)} runs residuais no alvo")


if __name__ == "__main__":
    main()
