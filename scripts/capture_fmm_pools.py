from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from fm06patch.fmm_schema import FMM2_DEFAULT, describe_schema  # noqa: E402
from live_player_memory import find_process_id, kernel32, open_process  # noqa: E402
from run_fmm_manual_batch import (  # noqa: E402
    capture_player,
    capture_pool,
    discover_pool,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Captura pontual dos pools vivos do FMM2, sem roteiro interativo."
    )
    parser.add_argument("label", help="Rótulo comum para os snapshots.")
    parser.add_argument("--fmm", type=Path, default=FMM2_DEFAULT)
    parser.add_argument(
        "--scopes",
        nargs="+",
        choices=("player", "contract", "club", "nation"),
        default=("player", "contract", "club", "nation"),
    )
    args = parser.parse_args()

    schema = describe_schema(args.fmm)
    if "player" in args.scopes:
        capture_player(args.label)
    if set(args.scopes) == {"player"}:
        return

    pid = find_process_id("fm.exe")
    handle = open_process(pid)
    try:
        for scope in args.scopes:
            if scope == "player":
                continue
            print(f"Descobrindo pool {scope}...")
            records = discover_pool(handle, schema, scope)
            capture_pool(handle, scope, args.label, records)
    finally:
        kernel32.CloseHandle(handle)


if __name__ == "__main__":
    main()
