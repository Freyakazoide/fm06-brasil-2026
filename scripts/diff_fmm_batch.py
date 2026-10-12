from __future__ import annotations

import argparse
import csv
import json
import struct
from pathlib import Path


KINDS = (("u8", 1, "<B"), ("u16", 2, "<H"), ("u32", 4, "<I"))


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def transition_candidates(old: bytes, new: bytes, old_value: int, new_value: int):
    candidates = []
    for kind, width, fmt in KINDS:
        if old_value >= 1 << (width * 8) or new_value >= 1 << (width * 8):
            continue
        for offset in range(0, min(len(old), len(new)) - width + 1):
            if (
                struct.unpack_from(fmt, old, offset)[0] == old_value
                and struct.unpack_from(fmt, new, offset)[0] == new_value
            ):
                candidates.append((offset, kind, width))
    return candidates


def compare(a: dict, b: dict, old_value: int, new_value: int) -> list[dict]:
    by_address_a = {int(hit["uid_address"]): hit for hit in a["hits"]}
    by_address_b = {int(hit["uid_address"]): hit for hit in b["hits"]}
    rows = []
    for uid_address in sorted(set(by_address_a) & set(by_address_b)):
        hit_a = by_address_a[uid_address]
        hit_b = by_address_b[uid_address]
        old = bytes.fromhex(hit_a["data_hex"])
        new = bytes.fromhex(hit_b["data_hex"])
        changed = [i for i, (left, right) in enumerate(zip(old, new)) if left != right]
        for offset, kind, width in transition_candidates(old, new, old_value, new_value):
            absolute = int(hit_a["window_address"]) + offset
            relative = offset - int(hit_a["uid_offset"])
            rows.append(
                {
                    "uid_address": f"0x{uid_address:08X}",
                    "absolute_address": f"0x{absolute:08X}",
                    "relative_to_uid": relative,
                    "type": kind,
                    "width": width,
                    "old": old_value,
                    "new": new_value,
                    "old_bytes": old[offset : offset + width].hex(" "),
                    "new_bytes": new[offset : offset + width].hex(" "),
                    "changed_bytes_in_window": len(changed),
                    "score": 100 + (20 if len(changed) <= width else 0),
                    "confidence": "CONFIRMED" if len(changed) <= width else "HIGH",
                }
            )
    rows.sort(key=lambda row: (-row["score"], row["uid_address"], row["relative_to_uid"]))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--old", type=int, required=True)
    parser.add_argument("--new", type=int, required=True)
    parser.add_argument("--field", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows = compare(load(args.before), load(args.after), args.old, args.new)
    payload = {
        "field": args.field,
        "before": str(args.before),
        "after": str(args.after),
        "expected": {"old": args.old, "new": args.new},
        "candidates": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    csv_path = args.output.with_suffix(".csv")
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8-sig") as target:
            writer = csv.DictWriter(target, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(f"{len(rows)} candidato(s) -> {args.output}")


if __name__ == "__main__":
    main()
