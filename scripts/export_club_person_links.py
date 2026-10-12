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

from fm06patch.server_db import (
    scan_serialized_strings,
)


CONFIG = (
    ROOT
    / "config"
    / "local.json"
)

MAP_FILE = (
    ROOT
    / "workspace"
    / "dumps"
    / "brazil_entity_map.csv"
)

OUTPUT = (
    ROOT
    / "workspace"
    / "dumps"
    / "club_person_links.csv"
)


# IDs confirmados manualmente pelo próprio FM06
# através de Opções -> Mostrar ID.
KNOWN_UIDS = {
    "Flamengo": {
        1: 104318,   # Sávio
        2: 104318,   # Sávio
    },

    "Cruzeiro": {
        2: 321081,   # Fred
    },

    "São Paulo": {
        1: 3300977,  # Rogério Ceni
    },
}


def u16(
    data: bytes,
    offset: int,
) -> int:
    return struct.unpack_from(
        "<H",
        data,
        offset,
    )[0]


def u32(
    data: bytes,
    offset: int,
) -> int:
    return struct.unpack_from(
        "<I",
        data,
        offset,
    )[0]


def parse_hex(
    value: str,
) -> int:
    return int(
        value,
        16,
    )


def server_only_tokens(
    server_tokens,
    client_tokens,
):
    """
    Remove do server as strings também existentes
    no registro correspondente do client.

    Preserva:
    - ordem
    - multiplicidade

    Exemplo:
    se "Sávio" aparece 2 vezes no server e 0 no client,
    as duas ocorrências permanecem.
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
            result.append(
                token
            )

    return result


def full_name(
    first_token,
    last_token,
) -> str:
    return (
        f"{first_token.text} "
        f"{last_token.text}"
    ).strip()


def main():

    with CONFIG.open(
        "r",
        encoding="utf-8",
    ) as file:
        config = json.load(
            file
        )

    db_dir = (
        Path(
            config["game_dir"]
        )
        / "data"
        / "db"
    )

    server = (
        db_dir
        / "server_db.dat"
    ).read_bytes()

    client = (
        db_dir
        / "client_db.dat"
    ).read_bytes()

    with MAP_FILE.open(
        "r",
        encoding="utf-8-sig",
    ) as file:

        mappings = [
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

    # Os 26 clubes brasileiros estão na mesma ordem
    # em client_db e server_db.
    mappings.sort(
        key=lambda row:
        parse_hex(
            row["server_offset"]
        )
    )

    results = []

    checks = 0
    passed = 0

    print("=" * 120)
    print(
        " FM06 BRASIL 2026 - "
        "CLUB PERSON LINKS"
    )
    print("=" * 120)

    for index, row in enumerate(
        mappings
    ):

        club = row[
            "short_name"
        ]

        # A coluna ainda se chama lang_id no CSV antigo,
        # mas já confirmamos no jogo que é o Unique ID
        # real do clube.
        club_uid = int(
            row[
                "lang_id"
            ]
        )

        server_offset = parse_hex(
            row[
                "server_offset"
            ]
        )

        client_offset = parse_hex(
            row[
                "client_offset"
            ]
        )

        # ---------------------------------------------
        # LIMITE DO REGISTRO SERVER
        # ---------------------------------------------

        if index + 1 < len(
            mappings
        ):

            next_server_offset = parse_hex(
                mappings[
                    index + 1
                ][
                    "server_offset"
                ]
            )

            server_end = min(
                next_server_offset,
                server_offset + 0x300,
            )

        else:

            # Vitória: evita engolir clubes búlgaros.
            server_end = min(
                len(server),
                server_offset + 0x220,
            )

        # ---------------------------------------------
        # LIMITE DO REGISTRO CLIENT
        # ---------------------------------------------

        if index + 1 < len(
            mappings
        ):

            next_client_offset = parse_hex(
                mappings[
                    index + 1
                ][
                    "client_offset"
                ]
            )

            client_end = min(
                next_client_offset,
                client_offset + 0x200,
            )

        else:

            # Mesmo cuidado para Vitória.
            client_end = min(
                len(client),
                client_offset + 0x180,
            )

        # ---------------------------------------------
        # STRINGS SERIALIZADAS
        # ---------------------------------------------

        server_tokens = (
            scan_serialized_strings(
                server,
                server_offset,
                server_end,
            )
        )

        client_tokens = (
            scan_serialized_strings(
                client,
                client_offset,
                client_end,
            )
        )

        extra_tokens = (
            server_only_tokens(
                server_tokens,
                client_tokens,
            )
        )

        # Nos 26 clubes analisados, os quatro primeiros
        # extras correspondem a:
        #
        # pessoa 1:
        #   nome
        #   sobrenome
        #
        # pessoa 2:
        #   nome
        #   sobrenome
        #
        if len(
            extra_tokens
        ) < 4:

            print()
            print(
                f"[WARN] {club}: "
                f"apenas "
                f"{len(extra_tokens)} "
                f"strings exclusivas "
                f"encontradas."
            )

            continue

        person_tokens = (
            extra_tokens[:4]
        )

        first_prefix = (
            person_tokens[
                0
            ].prefix_offset
        )

        # ---------------------------------------------
        # LAYOUT DESCOBERTO
        #
        # first_prefix - 12:
        #     uint32 person_1_uid
        #
        # first_prefix - 8:
        #     uint16 relation_1_raw
        #
        # first_prefix - 6:
        #     uint32 person_2_uid
        #
        # first_prefix - 2:
        #     uint16 relation_2_raw
        #
        # first_prefix:
        #     string first_name_1
        # ---------------------------------------------

        person_1_uid = u32(
            server,
            first_prefix - 12,
        )

        person_1_relation_raw = u16(
            server,
            first_prefix - 8,
        )

        person_2_uid = u32(
            server,
            first_prefix - 6,
        )

        person_2_relation_raw = u16(
            server,
            first_prefix - 2,
        )

        person_1_name = full_name(
            person_tokens[0],
            person_tokens[1],
        )

        person_2_name = full_name(
            person_tokens[2],
            person_tokens[3],
        )

        result = {
            "club_uid":
                club_uid,

            "club":
                club,

            "server_offset":
                row[
                    "server_offset"
                ],

            "person_block_offset":
                (
                    f"0x"
                    f"{first_prefix-12:08X}"
                ),

            "person_1_uid":
                person_1_uid,

            "person_1_relation_raw":
                person_1_relation_raw,

            "person_1_name":
                person_1_name,

            "person_2_uid":
                person_2_uid,

            "person_2_relation_raw":
                person_2_relation_raw,

            "person_2_name":
                person_2_name,
        }

        results.append(
            result
        )

        print()
        print(
            f"{club} "
            f"(club_uid={club_uid})"
        )

        print(
            f"  link 1: "
            f"{person_1_uid:<8} "
            f"raw="
            f"{person_1_relation_raw:<5} "
            f"{person_1_name}"
        )

        print(
            f"  link 2: "
            f"{person_2_uid:<8} "
            f"raw="
            f"{person_2_relation_raw:<5} "
            f"{person_2_name}"
        )

        # ---------------------------------------------
        # VALIDAÇÃO COM IDs MOSTRADOS PELO JOGO
        # ---------------------------------------------

        expected = (
            KNOWN_UIDS.get(
                club,
                {},
            )
        )

        for (
            slot,
            expected_uid,
        ) in expected.items():

            checks += 1

            if slot == 1:
                actual_uid = (
                    person_1_uid
                )
            elif slot == 2:
                actual_uid = (
                    person_2_uid
                )
            else:
                raise RuntimeError(
                    f"Slot inválido: "
                    f"{slot}"
                )

            if (
                actual_uid
                == expected_uid
            ):

                passed += 1

                print(
                    f"    [OK] "
                    f"slot {slot} "
                    f"confirmado pelo jogo"
                )

            else:

                print(
                    f"    [ERRO] "
                    f"slot {slot}: "
                    f"esperado "
                    f"{expected_uid}, "
                    f"encontrado "
                    f"{actual_uid}"
                )

    # -------------------------------------------------
    # CSV
    # -------------------------------------------------

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if results:

        with OUTPUT.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=list(
                    results[
                        0
                    ].keys()
                ),
                delimiter=";",
            )

            writer.writeheader()

            writer.writerows(
                results
            )

    print()
    print("=" * 120)

    print(
        f"Clubes exportados: "
        f"{len(results)}"
    )

    print(
        f"Âncoras confirmadas: "
        f"{passed}/{checks}"
    )

    print()
    print(
        "CSV:"
    )

    print(
        OUTPUT
    )


if __name__ == "__main__":
    main()