from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(
    0,
    str(ROOT / "src"),
)

from fm06patch.entity_mapping import (
    map_club_entities,
)

from fm06patch.lang_db import (
    LangDatabase,
)


CONFIG = (
    ROOT
    / "config"
    / "local.json"
)

CSV_OUTPUT = (
    ROOT
    / "workspace"
    / "dumps"
    / "brazil_entity_map.csv"
)

JSON_OUTPUT = (
    ROOT
    / "workspace"
    / "dumps"
    / "brazil_entity_map.json"
)


def value_or_none(
    obj,
    attr: str,
):
    if obj is None:
        return None

    return getattr(
        obj,
        attr,
    )


def main():
    with CONFIG.open(
        "r",
        encoding="utf-8",
    ) as file:
        config = json.load(file)

    game_dir = Path(
        config["game_dir"]
    )

    lang_path = (
        game_dir
        / "data"
        / "db"
        / "lang_db.dat"
    )

    client_path = (
        game_dir
        / "data"
        / "db"
        / "client_db.dat"
    )

    server_path = (
        game_dir
        / "data"
        / "db"
        / "server_db.dat"
    )

    print("=" * 110)
    print(
        " FM06 BRASIL 2026 - ENTITY MAPPING"
    )
    print("=" * 110)
    print()

    lang_db = LangDatabase.load(
        lang_path
    )

    lang_records = lang_db.clubs()

    client_data = (
        client_path.read_bytes()
    )

    server_data = (
        server_path.read_bytes()
    )

    mappings = map_club_entities(
        lang_records,
        client_data,
        server_data,
    )

    rows = []

    for mapping in mappings:

        lang = mapping.lang
        client = mapping.client
        server = mapping.server

        client_field_a = value_or_none(
            client,
            "field_a",
        )

        client_field_b = value_or_none(
            client,
            "field_b",
        )

        server_field_a = value_or_none(
            server,
            "field_a",
        )

        server_field_b = value_or_none(
            server,
            "field_b",
        )

        field_a_same = (
            client is not None
            and server is not None
            and client.field_a
            == server.field_a
        )

        field_b_same = (
            client is not None
            and server is not None
            and client.field_b
            == server.field_b
        )

        lang_minus_client_b = (
            lang.record_id
            - client.field_b
            if client is not None
            else None
        )

        lang_minus_server_b = (
            lang.record_id
            - server.field_b
            if server is not None
            else None
        )

        row = {
            "status": mapping.status,

            "lang_id": lang.record_id,
            "lang_id_hex": (
                lang.record_id_hex
            ),

            "full_name": (
                lang.full_name
            ),

            "short_name": (
                lang.short_name
            ),

            "lang_offset": (
                lang.offset_hex
            ),

            "client_candidates": (
                mapping.client_candidates
            ),

            "client_offset": (
                client.offset_hex
                if client
                else None
            ),

            "client_field_a": (
                client_field_a
            ),

            "client_field_b": (
                client_field_b
            ),

            "server_candidates": (
                mapping.server_candidates
            ),

            "server_offset": (
                server.offset_hex
                if server
                else None
            ),

            "server_field_a": (
                server_field_a
            ),

            "server_field_b": (
                server_field_b
            ),

            "field_a_same": (
                field_a_same
            ),

            "field_b_same": (
                field_b_same
            ),

            "lang_minus_client_b": (
                lang_minus_client_b
            ),

            "lang_minus_server_b": (
                lang_minus_server_b
            ),
        }

        rows.append(row)

    print(
        f"{'STATUS':<8}"
        f"{'LANG':>7}  "
        f"{'A':>5} "
        f"{'B':>5}  "
        f"{'CLIENT':>12}  "
        f"{'SERVER':>12}  "
        f"CLUBE"
    )

    print("-" * 110)

    for row in rows:

        field_a = (
            row["client_field_a"]
            if row["client_field_a"]
            is not None
            else row["server_field_a"]
        )

        field_b = (
            row["client_field_b"]
            if row["client_field_b"]
            is not None
            else row["server_field_b"]
        )

        print(
            f"{row['status']:<8}"
            f"{row['lang_id']:>7}  "
            f"{str(field_a):>5} "
            f"{str(field_b):>5}  "
            f"{str(row['client_offset']):>12}  "
            f"{str(row['server_offset']):>12}  "
            f"{row['full_name']} "
            f"-> "
            f"{row['short_name']}"
        )

    print()
    print("=" * 110)

    ok = sum(
        1
        for row in rows
        if row["status"] == "OK"
    )

    partial = sum(
        1
        for row in rows
        if row["status"] == "PARTIAL"
    )

    ambiguous = sum(
        1
        for row in rows
        if row["status"] == "AMBIG"
    )

    print(
        f"Mapeamentos: {len(rows)}"
    )

    print(
        f"OK:           {ok}"
    )

    print(
        f"Parciais:     {partial}"
    )

    print(
        f"Ambíguos:     {ambiguous}"
    )

    CSV_OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = list(
        rows[0].keys()
    ) if rows else []

    if rows:
        with CSV_OUTPUT.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
                delimiter=";",
            )

            writer.writeheader()
            writer.writerows(rows)

    with JSON_OUTPUT.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            rows,
            file,
            ensure_ascii=False,
            indent=4,
        )

    print()
    print("CSV:")
    print(CSV_OUTPUT)

    print()
    print("JSON:")
    print(JSON_OUTPUT)


if __name__ == "__main__":
    main()