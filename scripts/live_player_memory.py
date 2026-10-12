from __future__ import annotations

import argparse
import ctypes
import json
import struct
from ctypes import wintypes
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_ROOT = ROOT / "workspace" / "live_memory"


# ============================================================
# WIN32 CONSTANTS
# ============================================================

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400

MEM_COMMIT = 0x1000

PAGE_NOACCESS = 0x01
PAGE_GUARD = 0x100

TH32CS_SNAPPROCESS = 0x00000002

INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


kernel32 = ctypes.WinDLL(
    "kernel32",
    use_last_error=True,
)


# ============================================================
# STRUCTURES
# ============================================================

class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]


# ============================================================
# API SIGNATURES
# ============================================================

kernel32.CreateToolhelp32Snapshot.argtypes = [
    wintypes.DWORD,
    wintypes.DWORD,
]
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE

kernel32.Process32FirstW.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(PROCESSENTRY32W),
]
kernel32.Process32FirstW.restype = wintypes.BOOL

kernel32.Process32NextW.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(PROCESSENTRY32W),
]
kernel32.Process32NextW.restype = wintypes.BOOL

kernel32.OpenProcess.argtypes = [
    wintypes.DWORD,
    wintypes.BOOL,
    wintypes.DWORD,
]
kernel32.OpenProcess.restype = wintypes.HANDLE

kernel32.CloseHandle.argtypes = [
    wintypes.HANDLE,
]
kernel32.CloseHandle.restype = wintypes.BOOL

kernel32.ReadProcessMemory.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
kernel32.ReadProcessMemory.restype = wintypes.BOOL

kernel32.VirtualQueryEx.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    ctypes.POINTER(MEMORY_BASIC_INFORMATION),
    ctypes.c_size_t,
]
kernel32.VirtualQueryEx.restype = ctypes.c_size_t


# ============================================================
# PROCESS
# ============================================================

def find_process_id(
    executable_name: str,
) -> int:

    snapshot = kernel32.CreateToolhelp32Snapshot(
        TH32CS_SNAPPROCESS,
        0,
    )

    if snapshot == INVALID_HANDLE_VALUE:
        raise OSError(
            ctypes.get_last_error(),
            "CreateToolhelp32Snapshot falhou",
        )

    try:

        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(
            entry
        )

        ok = kernel32.Process32FirstW(
            snapshot,
            ctypes.byref(entry),
        )

        target = executable_name.casefold()

        while ok:

            if (
                entry.szExeFile.casefold()
                == target
            ):
                return int(
                    entry.th32ProcessID
                )

            ok = kernel32.Process32NextW(
                snapshot,
                ctypes.byref(entry),
            )

    finally:
        kernel32.CloseHandle(
            snapshot
        )

    raise RuntimeError(
        f"Processo {executable_name!r} "
        f"não encontrado."
    )


def open_process(
    pid: int,
):
    handle = kernel32.OpenProcess(
        PROCESS_QUERY_INFORMATION
        | PROCESS_VM_READ,
        False,
        pid,
    )

    if not handle:
        error = ctypes.get_last_error()

        raise OSError(
            error,
            (
                "OpenProcess falhou. "
                "Tente abrir o PowerShell "
                "como Administrador."
            ),
        )

    return handle


# ============================================================
# MEMORY
# ============================================================

def readable_region(
    mbi: MEMORY_BASIC_INFORMATION,
) -> bool:

    if mbi.State != MEM_COMMIT:
        return False

    if mbi.Protect & PAGE_GUARD:
        return False

    if mbi.Protect & PAGE_NOACCESS:
        return False

    return True


def read_memory(
    handle,
    address: int,
    size: int,
) -> bytes | None:

    if size <= 0:
        return b""

    buffer = ctypes.create_string_buffer(
        size
    )

    read = ctypes.c_size_t()

    ok = kernel32.ReadProcessMemory(
        handle,
        ctypes.c_void_p(address),
        buffer,
        size,
        ctypes.byref(read),
    )

    if not ok:
        return None

    return buffer.raw[
        :read.value
    ]


def iter_regions(
    handle,
):

    address = 0

    # FM06 é um processo Win32.
    max_address = 0x7FFFFFFF

    mbi = MEMORY_BASIC_INFORMATION()

    while address < max_address:

        result = kernel32.VirtualQueryEx(
            handle,
            ctypes.c_void_p(address),
            ctypes.byref(mbi),
            ctypes.sizeof(mbi),
        )

        if not result:
            address += 0x1000
            continue

        base = int(
            mbi.BaseAddress or 0
        )

        size = int(
            mbi.RegionSize
        )

        if size <= 0:
            address += 0x1000
            continue

        if readable_region(
            mbi
        ):
            yield (
                base,
                size,
            )

        next_address = (
            base + size
        )

        if next_address <= address:
            address += 0x1000
        else:
            address = next_address


def scan_value(
    handle,
    needle: bytes,
) -> list[int]:

    hits: list[int] = []

    chunk_size = 1024 * 1024

    for base, region_size in (
        iter_regions(handle)
    ):

        offset = 0
        overlap = b""

        while offset < region_size:

            amount = min(
                chunk_size,
                region_size - offset,
            )

            data = read_memory(
                handle,
                base + offset,
                amount,
            )

            if data is None:
                break

            combined = (
                overlap + data
            )

            combined_base = (
                base
                + offset
                - len(overlap)
            )

            cursor = 0

            while True:

                pos = combined.find(
                    needle,
                    cursor,
                )

                if pos == -1:
                    break

                absolute = (
                    combined_base + pos
                )

                if absolute not in hits:
                    hits.append(
                        absolute
                    )

                cursor = pos + 1

            keep = max(
                0,
                len(needle) - 1,
            )

            if keep:
                overlap = combined[
                    -keep:
                ]
            else:
                overlap = b""

            offset += amount

    hits.sort()

    return hits


# ============================================================
# SNAPSHOT
# ============================================================

def make_snapshot(
    player_uid: int,
    label: str,
    radius: int,
):

    pid = find_process_id(
        "fm.exe"
    )

    handle = open_process(
        pid
    )

    try:

        needle = struct.pack(
            "<I",
            player_uid,
        )

        print("=" * 90)
        print(
            " FM06 LIVE PLAYER MEMORY"
        )
        print("=" * 90)

        print(
            f"PID        : {pid}"
        )

        print(
            f"Player UID : {player_uid}"
        )

        print(
            "Scanning..."
        )

        hits = scan_value(
            handle,
            needle,
        )

        print(
            f"UID hits   : {len(hits)}"
        )

        snapshots = []

        for index, address in enumerate(
            hits,
            start=1,
        ):

            start = max(
                0,
                address - radius,
            )

            size = (
                radius
                + 4
                + radius
            )

            data = read_memory(
                handle,
                start,
                size,
            )

            if data is None:
                continue

            uid_offset = (
                address - start
            )

            print(
                f"#{index:02d} "
                f"UID @ 0x{address:08X} "
                f"window @ 0x{start:08X} "
                f"size={len(data)}"
            )

            snapshots.append(
                {
                    "uid_address":
                        address,

                    "window_address":
                        start,

                    "uid_offset":
                        uid_offset,

                    "size":
                        len(data),

                    "data_hex":
                        data.hex(),
                }
            )

        destination = (
            OUTPUT_ROOT
            / str(player_uid)
        )

        destination.mkdir(
            parents=True,
            exist_ok=True,
        )

        output = (
            destination
            / f"{label}.json"
        )

        payload = {
            "pid":
                pid,

            "player_uid":
                player_uid,

            "label":
                label,

            "radius":
                radius,

            "hits":
                snapshots,
        }

        output.write_text(
            json.dumps(
                payload,
                indent=2,
            ),
            encoding="utf-8",
        )

        print()
        print(
            f"Snapshot salvo em:"
        )

        print(
            output
        )

    finally:
        kernel32.CloseHandle(
            handle
        )


# ============================================================
# DIFF
# ============================================================

def load_snapshot(
    player_uid: int,
    label: str,
):

    path = (
        OUTPUT_ROOT
        / str(player_uid)
        / f"{label}.json"
    )

    if not path.exists():
        raise FileNotFoundError(
            path
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def contiguous_groups(
    positions: list[int],
):

    if not positions:
        return []

    positions = sorted(
        positions
    )

    groups = []

    start = positions[0]
    previous = positions[0]

    for value in positions[1:]:

        if value == previous + 1:
            previous = value
            continue

        groups.append(
            (
                start,
                previous,
            )
        )

        start = value
        previous = value

    groups.append(
        (
            start,
            previous,
        )
    )

    return groups


def transition_matches(
    old: bytes,
    new: bytes,
    expected_old: int,
    expected_new: int,
):

    result = []

    for width, fmt in (
        (1, "<B"),
        (2, "<H"),
        (4, "<I"),
    ):

        if (
            expected_old
            >= 1 << (width * 8)
            or expected_new
            >= 1 << (width * 8)
        ):
            continue

        limit = min(
            len(old),
            len(new),
        ) - width + 1

        for offset in range(
            max(0, limit)
        ):

            old_value = struct.unpack_from(
                fmt,
                old,
                offset,
            )[0]

            if old_value != expected_old:
                continue

            new_value = struct.unpack_from(
                fmt,
                new,
                offset,
            )[0]

            if new_value != expected_new:
                continue

            result.append(
                (
                    offset,
                    width,
                )
            )

    return result


def diff_snapshots(
    player_uid: int,
    label_a: str,
    label_b: str,
    expected_old: int | None,
    expected_new: int | None,
):

    a = load_snapshot(
        player_uid,
        label_a,
    )

    b = load_snapshot(
        player_uid,
        label_b,
    )

    hits_a = {
        item["uid_address"]:
            item
        for item in a["hits"]
    }

    hits_b = {
        item["uid_address"]:
            item
        for item in b["hits"]
    }

    common = sorted(
        set(hits_a)
        & set(hits_b)
    )

    print("=" * 100)
    print(
        " FM06 LIVE MEMORY DIFF"
    )
    print("=" * 100)

    print(
        f"Player UID : {player_uid}"
    )

    print(
        f"A          : {label_a}"
    )

    print(
        f"B          : {label_b}"
    )

    print(
        f"Common hits: {len(common)}"
    )

    if (
        expected_old is not None
        and expected_new is not None
    ):
        print(
            f"Expected   : "
            f"{expected_old} -> "
            f"{expected_new}"
        )

    total_changed = 0

    for hit_number, address in enumerate(
        common,
        start=1,
    ):

        item_a = hits_a[
            address
        ]

        item_b = hits_b[
            address
        ]

        old = bytes.fromhex(
            item_a["data_hex"]
        )

        new = bytes.fromhex(
            item_b["data_hex"]
        )

        length = min(
            len(old),
            len(new),
        )

        changed = [
            index
            for index in range(length)
            if old[index] != new[index]
        ]

        if not changed:
            continue

        total_changed += len(
            changed
        )

        uid_offset = int(
            item_a["uid_offset"]
        )

        base_address = int(
            item_a["window_address"]
        )

        print()
        print("-" * 100)

        print(
            f"HIT #{hit_number} "
            f"UID @ 0x{address:08X}"
        )

        print(
            f"Changed bytes: "
            f"{len(changed)}"
        )

        if (
            expected_old is not None
            and expected_new is not None
        ):

            matches = transition_matches(
                old,
                new,
                expected_old,
                expected_new,
            )

            if matches:

                print()
                print(
                    "EXACT VALUE TRANSITIONS:"
                )

                for offset, width in (
                    matches[:50]
                ):

                    absolute = (
                        base_address
                        + offset
                    )

                    relative = (
                        offset
                        - uid_offset
                    )

                    print(
                        f"  width={width} "
                        f"abs=0x{absolute:08X} "
                        f"rel_uid={relative:+d} "
                        f"{expected_old}"
                        f" -> "
                        f"{expected_new}"
                    )

        print()
        print(
            "CHANGED GROUPS:"
        )

        groups = contiguous_groups(
            changed
        )

        for group_start, group_end in (
            groups[:60]
        ):

            length_group = (
                group_end
                - group_start
                + 1
            )

            absolute = (
                base_address
                + group_start
            )

            relative = (
                group_start
                - uid_offset
            )

            old_bytes = old[
                group_start:
                group_end + 1
            ]

            new_bytes = new[
                group_start:
                group_end + 1
            ]

            print(
                f"  abs=0x{absolute:08X} "
                f"rel_uid={relative:+d} "
                f"len={length_group:<3} "
                f"{old_bytes.hex(' ')} "
                f"-> "
                f"{new_bytes.hex(' ')}"
            )

    print()
    print("=" * 100)

    print(
        f"Total changed bytes "
        f"em hits comuns: "
        f"{total_changed}"
    )


# ============================================================
# CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    snapshot = sub.add_parser(
        "snapshot"
    )

    snapshot.add_argument(
        "player_uid",
        type=int,
    )

    snapshot.add_argument(
        "--label",
        required=True,
    )

    snapshot.add_argument(
        "--radius",
        type=int,
        default=4096,
    )

    diff = sub.add_parser(
        "diff"
    )

    diff.add_argument(
        "player_uid",
        type=int,
    )

    diff.add_argument(
        "label_a",
    )

    diff.add_argument(
        "label_b",
    )

    diff.add_argument(
        "--old",
        type=int,
        default=None,
    )

    diff.add_argument(
        "--new",
        type=int,
        default=None,
    )

    args = parser.parse_args()

    if args.command == "snapshot":

        make_snapshot(
            args.player_uid,
            args.label,
            args.radius,
        )

        return

    if args.command == "diff":

        diff_snapshots(
            args.player_uid,
            args.label_a,
            args.label_b,
            args.old,
            args.new,
        )

        return


if __name__ == "__main__":
    main()