from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FMM2_DEFAULT = Path(r"C:\Games\Programas\FMM2\FMM.txt")
TARGET_VERSION_ROW = 2  # zero based: terceira linha, FM 6.0.2


@dataclass(frozen=True)
class FmmSection:
    name: str
    lines: tuple[str, ...]
    occurrence: int


def parse_fmm(path: Path = FMM2_DEFAULT) -> list[FmmSection]:
    """Parseia FMM.txt preservando seções duplicadas e a ordem original."""
    text = path.read_text(encoding="cp1252")
    sections: list[FmmSection] = []
    current_name: str | None = None
    current_lines: list[str] = []
    occurrences: dict[str, int] = {}

    def flush() -> None:
        nonlocal current_name, current_lines
        if current_name is None:
            return
        occurrence = occurrences.get(current_name, 0)
        occurrences[current_name] = occurrence + 1
        sections.append(
            FmmSection(current_name, tuple(current_lines), occurrence)
        )

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("[") and line.endswith("]"):
            flush()
            current_name = line[1:-1]
            current_lines = []
        elif current_name is not None and line:
            current_lines.append(line)
    flush()
    return sections


def section(
    sections: list[FmmSection], name: str, occurrence: int = 0
) -> FmmSection:
    for item in sections:
        if item.name == name and item.occurrence == occurrence:
            return item
    raise KeyError(f"Seção [{name}] ocorrência {occurrence} ausente")


def counted_values(item: FmmSection) -> list[str]:
    if not item.lines:
        return []
    count = int(item.lines[0])
    values = list(item.lines[1:])
    if len(values) != count:
        raise ValueError(
            f"[{item.name}] declara {count}, mas contém {len(values)} valores"
        )
    return values


def address_rows(item: FmmSection) -> list[list[int]]:
    rows: list[list[int]] = []
    for line in item.lines:
        tokens = line.split()
        if not tokens or not all(len(token) == 8 for token in tokens):
            break
        try:
            rows.append([int(token, 16) for token in tokens])
        except ValueError:
            break
    return rows


def target_roots(
    sections: list[FmmSection], name: str, row: int = TARGET_VERSION_ROW
) -> list[int]:
    rows = address_rows(section(sections, name))
    if row >= len(rows):
        raise IndexError(f"[{name}] não possui a linha {row + 1}")
    return rows[row]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_snapshot(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def hit_bytes(hit: dict[str, Any]) -> tuple[bytes, int]:
    return bytes.fromhex(hit["data_hex"]), int(hit["uid_offset"])


def root_signature(roots: list[int]) -> bytes:
    return b"".join(struct.pack("<I", value) for value in roots)


def object_hits(
    snapshot: dict[str, Any], roots: list[int], signature_rel_uid: int = -20
) -> list[dict[str, Any]]:
    signature = root_signature(roots)
    result: list[dict[str, Any]] = []
    for hit in snapshot["hits"]:
        data, uid_offset = hit_bytes(hit)
        start = uid_offset + signature_rel_uid
        if start < 0 or start + len(signature) > len(data):
            continue
        if data[start : start + len(signature)] == signature:
            result.append(hit)
    return result


def read_value(hit: dict[str, Any], relative: int, kind: str) -> int:
    formats = {"u8": "<B", "u16": "<H", "u32": "<I"}
    data, uid_offset = hit_bytes(hit)
    return int(struct.unpack_from(formats[kind], data, uid_offset + relative)[0])


def read_bytes(hit: dict[str, Any], relative: int, size: int) -> bytes:
    data, uid_offset = hit_bytes(hit)
    start = uid_offset + relative
    return data[start : start + size]


def describe_schema(path: Path = FMM2_DEFAULT) -> dict[str, Any]:
    sections = parse_fmm(path)
    roots = {
        name: target_roots(sections, name)
        for name in (
            "City",
            "Club",
            "Club Team",
            "Coaching",
            "Contract",
            "Division",
            "Finance",
            "Gamer",
            "Nation",
            "Nation Team",
            "Person Name",
            "PData",
            "Player",
            "Player Staff",
            "Playing",
            "Stadium",
            "Staff",
        )
    }
    return {
        "source": str(path),
        "sha256": sha256(path),
        "target_build": "6.0.2f72973",
        "target_row_zero_based": TARGET_VERSION_ROW,
        "target_row_human": TARGET_VERSION_ROW + 1,
        "roots": roots,
        "playing_attributes": counted_values(section(sections, "Playing Attrib")),
        "personal_info_primary": counted_values(section(sections, "Personal Info", 0)),
        "personal_info_alternate": counted_values(section(sections, "Personal Info", 1)),
        "contract_info": counted_values(section(sections, "Contract Info")),
        "nation_info": counted_values(section(sections, "Nation Info")),
        "club_info": counted_values(section(sections, "Club Info")),
        # [Playing Position] é uma permutação de 79 entradas e, ao
        # contrário das listas vizinhas, não possui uma linha de contagem.
        "playing_position": [
            int(value) for value in section(sections, "Playing Position").lines
        ],
        "preferred_moves": counted_values(section(sections, "Preferred Moves")),
    }
