from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch.fmm_schema import (  # noqa: E402
    FMM2_DEFAULT,
    describe_schema,
    load_snapshot,
    object_hits,
    read_bytes,
    read_value,
)


PLAYER_FIELDS = [
    ("Fitness", -216, "u16", "MEDIUM"),
    ("Match Exercise", -214, "u16", "MEDIUM"),
    ("Jadedness", -212, "u16", "MEDIUM"),
    ("Home Rep.", -210, "u16", "MEDIUM"),
    ("Current Rep.", -208, "u16", "MEDIUM"),
    ("World Rep.", -206, "u16", "MEDIUM"),
    ("Current Ability", -204, "u16", "CONFIRMED"),
    ("Potential Ability", -202, "u16", "CONFIRMED"),
    ("Morale", -184, "u8", "MEDIUM"),
    ("Weight", -78, "u16", "HIGH"),
    ("Height", -76, "u16", "HIGH"),
    ("Nationality pointer", 64, "u32", "CONFIRMED"),
    ("Int. Caps", 72, "u8", "HIGH"),
    ("U21 Caps", 73, "u8", "CONFIRMED"),
    ("Int. Goals", 74, "u8", "HIGH"),
    ("U21 Goals", 75, "u8", "CONFIRMED"),
    ("Ask Value", -192, "u32", "CONFIRMED"),
]


PERSONALITY_FIELDS = [
    "Adaptability",
    "Ambition",
    "Loyalty",
    "Pressure",
    "Professional",
    "Sportsmanship",
    "Temperament",
    "Controversy",
]


def analyze(snapshot_path: Path, fmm_path: Path) -> dict:
    schema = describe_schema(fmm_path)
    snapshot = load_snapshot(snapshot_path)
    uid = int(snapshot["player_uid"])

    found = {
        # Player possui duas raízes adicionais em UID-224/-220; a
        # assinatura contígua imediatamente antes do UID usa as cinco primeiras.
        name: object_hits(snapshot, schema["roots"][name][:5])
        for name in ("Player", "PData", "Playing")
    }

    result = {
        "snapshot": str(snapshot_path),
        "player_uid": uid,
        "objects": {
            name: [f"0x{int(hit['uid_address']):08X}" for hit in hits]
            for name, hits in found.items()
        },
        "player_fields": [],
        "personality": [],
        "playing_attributes": [],
    }

    if len(found["Player"]) == 1:
        hit = found["Player"][0]
        for field, relative, kind, confidence in PLAYER_FIELDS:
            result["player_fields"].append(
                {
                    "field": field,
                    "relative_to_player_uid": relative,
                    "type": kind,
                    "value": read_value(hit, relative, kind),
                    "confidence": confidence,
                }
            )

    if len(found["PData"]) == 1:
        hit = found["PData"][0]
        for index, field in enumerate(PERSONALITY_FIELDS):
            result["personality"].append(
                {
                    "field": field,
                    "relative_to_pdata_uid": 8 + index,
                    "type": "u8",
                    "value": read_value(hit, 8 + index, "u8"),
                    "confidence": "HIGH",
                }
            )

    if len(found["Playing"]) == 1:
        hit = found["Playing"][0]
        raw = read_bytes(hit, 8, 79)
        names = schema["playing_attributes"]
        positions = schema["playing_position"]
        for index, (field, storage_index) in enumerate(zip(names, positions)):
            result["playing_attributes"].append(
                {
                    "fmm_index": index,
                    "field": field,
                    "storage_index": storage_index,
                    "relative_to_playing_uid": 8 + storage_index,
                    "type": "u8",
                    "raw_value": raw[storage_index],
                    "confidence": "HIGH",
                    "value_transform": "DIRECT_1_20"
                    if index >= 54
                    else "UNRESOLVED_RAW_0_255",
                }
            )

    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--fmm", type=Path, default=FMM2_DEFAULT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = analyze(args.snapshot, args.fmm)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
