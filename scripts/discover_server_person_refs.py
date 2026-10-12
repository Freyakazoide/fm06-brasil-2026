from __future__ import annotations

import csv
import json
import struct
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(
    0,
    str(ROOT / "src"),
)

from fm06patch.server_db import scan_serialized_strings


CONFIG = ROOT / "config" / "local.json"

MAP_FILE = (
    ROOT
    / "workspace"
    / "dumps"
    / "brazil_entity_map.csv"
)


def parse_hex(value: str) -> int:
    return int(value, 16)


def u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        return -1

    return struct.unpack_from(
        "<I",
        data,
        offset,
    )[0]


def server_only_tokens(
    server_tokens,
    client_tokens,
):
    """
    Preserva ordem e multiplicidade.

    Se uma string existe uma vez no client e duas no server,
    uma ocorrência continua sendo considerada server-only.
    """

    remaining = Counter(
        token.text
        for token in client_tokens
    )

    result = []

    for token in server_tokens:

        if remaining[token.text] > 0:
            remaining[token.text] -= 1
        else:
            result.append(token)

    return result


def main():

    with CONFIG.open(
        "r",
        encoding="utf-8",
    ) as file:
        config = json.load(file)

    game_dir = Path(
        config["game_dir"]
    )

    server = (
        game_dir
        / "data"
        / "db"
        / "server_db.dat"
    ).read_bytes()

    client = (
        game_dir
        / "data"
        / "db"
        / "client_db.dat"
    ).read_bytes()

    with MAP_FILE.open(
        "r",
        encoding="utf-8-sig",
    ) as file:

        rows = [
            row
            for row in csv.DictReader(
                file,
                delimiter=";",
            )
            if (
                row["status"] == "OK"
                and row["server_offset"]
                and row["client_offset"]
            )
        ]

    rows.sort(
        key=lambda row:
        parse_hex(
            row["server_offset"]
        )
    )

    clubs = []

    print("=" * 110)
    print(
        " FM06 BRASIL 2026 - "
        "SERVER HISTORICAL PERSON REFERENCES"
    )
    print("=" * 110)

    for row in rows:

        name = row["short_name"]

        server_offset = parse_hex(
            row["server_offset"]
        )

        client_offset = parse_hex(
            row["client_offset"]
        )

        server_tokens = scan_serialized_strings(
            server,
            server_offset,
            min(
                len(server),
                server_offset + 0x220,
            ),
        )

        client_tokens = scan_serialized_strings(
            client,
            client_offset,
            min(
                len(client),
                client_offset + 0x180,
            ),
        )

        extra = server_only_tokens(
            server_tokens,
            client_tokens,
        )

        # Os quatro primeiros extras observados representam:
        #
        # pessoa 1: nome + sobrenome
        # pessoa 2: nome + sobrenome
        #
        # Ainda não sabemos a semântica da relação.
        person_tokens = extra[:4]

        if len(person_tokens) < 2:
            continue

        clubs.append(
            {
                "name": name,
                "server_offset":
                    server_offset,
                "tokens":
                    person_tokens,
            }
        )

        formatted = []

        for token in person_tokens:

            formatted.append(
                f"+0x"
                f"{token.prefix_offset-server_offset:X} "
                f"{token.text!r}"
            )

        print()
        print(name)
        print(
            "  "
            + " | ".join(
                formatted
            )
        )

    print()
    print("=" * 110)
    print(
        " CANDIDATOS U32 ANTES DA PRIMEIRA PESSOA"
    )
    print("=" * 110)
    print()

    candidates = []

    for relative in range(
        -48,
        1,
    ):

        values = []

        for club in clubs:

            first_token = (
                club["tokens"][0]
            )

            position = (
                first_token.prefix_offset
                + relative
            )

            value = u32(
                server,
                position,
            )

            values.append(value)

        plausible = [
            value
            for value in values
            if (
                0 < value
                < 50_000_000
            )
        ]

        if len(plausible) < 20:
            continue

        unique = set(
            plausible
        )

        if len(unique) < 5:
            continue

        candidates.append(
            (
                relative,
                len(plausible),
                len(unique),
                min(unique),
                max(unique),
                values,
            )
        )

    candidates.sort(
        key=lambda item: (
            -item[1],
            -item[2],
            item[0],
        )
    )

    interesting = {
        "Flamengo",
        "Corinthians",
        "Palmeiras",
        "São Paulo",
    }

    for (
        relative,
        valid_count,
        unique_count,
        minimum,
        maximum,
        values,
    ) in candidates[:30]:

        print(
            f"{relative:+4}  "
            f"valid={valid_count:>2}  "
            f"unique={unique_count:>2}  "
            f"min={minimum:<9} "
            f"max={maximum:<9}"
        )

        for club, value in zip(
            clubs,
            values,
        ):
            if club["name"] in interesting:
                print(
                    f"       "
                    f"{club['name']:<12} "
                    f"{value}"
                )

    print()
    print("=" * 110)
    print(
        " CAMPOS QUE SE REPETEM QUANDO A MESMA "
        "PESSOA APARECE DUAS VEZES"
    )
    print("=" * 110)
    print()

    duplicate_clubs = []

    for club in clubs:

        tokens = club["tokens"]

        if len(tokens) < 4:
            continue

        if (
            tokens[0].text
            == tokens[2].text
            and tokens[1].text
            == tokens[3].text
        ):
            duplicate_clubs.append(
                club
            )

    print(
        "Clubes com pessoa duplicada:",
        ", ".join(
            club["name"]
            for club in duplicate_clubs
        )
        or "(nenhum)",
    )

    print()

    repeat_candidates = []

    for relative in range(
        -48,
        1,
    ):

        equal = 0
        compared = 0
        values = []

        for club in duplicate_clubs:

            tokens = club["tokens"]

            first = u32(
                server,
                tokens[0].prefix_offset
                + relative,
            )

            second = u32(
                server,
                tokens[2].prefix_offset
                + relative,
            )

            compared += 1

            if first == second:
                equal += 1

            values.append(
                (
                    club["name"],
                    first,
                    second,
                )
            )

        if (
            compared
            and equal
            == compared
        ):
            repeat_candidates.append(
                (
                    relative,
                    values,
                )
            )

    for (
        relative,
        values,
    ) in repeat_candidates:

        print(
            f"relative={relative:+4}"
        )

        for (
            club_name,
            first,
            second,
        ) in values:

            print(
                f"    {club_name:<12} "
                f"{first} == {second}"
            )


if __name__ == "__main__":
    main()