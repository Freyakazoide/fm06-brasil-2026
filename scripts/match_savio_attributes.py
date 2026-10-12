from __future__ import annotations

import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

CONFIG = (
    ROOT
    / "config"
    / "local.json"
)


PLAYER_UID = 104318


ATTRIBUTE_GROUPS = {
    "technical": [
        11,  # Cabeceamento
        15,  # Cantos
        16,  # Cruzamentos
        10,  # Desarme
        15,  # Finalização
        20,  # Finta
        7,   # Lançamentos Longos
        16,  # Livres
        8,   # Marcação
        16,  # Penalties
        18,  # Passe
        18,  # Primeiro Toque
        14,  # Remates Longe
        19,  # Técnica
    ],

    "mental": [
        10,  # Agressividade
        13,  # Antecipação
        12,  # Bravura
        17,  # Compostura
        13,  # Concentração
        17,  # Criatividade
        15,  # Decisões
        15,  # Determinação
        14,  # Influência
        16,  # Instinto
        12,  # Posicionamento
        18,  # Sem Bola
        12,  # Trabalho Equipa
        13,  # Índice Trabalho
    ],

    "physical": [
        19,  # Aceleração
        17,  # Agilidade
        11,  # Balance
        12,  # Condição Física Natural
        11,  # Força
        12,  # Impulsão
        14,  # Resistência
        18,  # Velocidade
    ],
}


def find_all(
    data: bytes,
    needle: bytes,
):
    result = []
    cursor = 0

    while True:

        pos = data.find(
            needle,
            cursor,
        )

        if pos == -1:
            break

        result.append(pos)

        cursor = pos + 1

    return result


def make_ngrams(
    values: list[int],
    size: int,
):
    return [
        bytes(
            values[
                index:
                index + size
            ]
        )
        for index in range(
            0,
            len(values)
            - size
            + 1,
        )
    ]


def score_window(
    data: bytes,
    center: int,
    radius: int = 4096,
):
    start = max(
        0,
        center - radius,
    )

    end = min(
        len(data),
        center + radius,
    )

    block = data[
        start:end
    ]

    result = {
        "score4":
            0,

        "score5":
            0,

        "matches":
            [],
    }

    seen = set()

    for group_name, values in (
        ATTRIBUTE_GROUPS.items()
    ):

        for size in (
            4,
            5,
        ):

            for index, pattern in enumerate(
                make_ngrams(
                    values,
                    size,
                )
            ):

                key = (
                    group_name,
                    size,
                    index,
                )

                cursor = 0

                while True:

                    local = block.find(
                        pattern,
                        cursor,
                    )

                    if local == -1:
                        break

                    absolute = (
                        start + local
                    )

                    match_key = (
                        key,
                        absolute,
                    )

                    if match_key not in seen:

                        seen.add(
                            match_key
                        )

                        result[
                            "matches"
                        ].append(
                            {
                                "group":
                                    group_name,

                                "size":
                                    size,

                                "attribute_index":
                                    index,

                                "absolute":
                                    absolute,

                                "relative":
                                    absolute
                                    - center,

                                "values":
                                    list(pattern),
                            }
                        )

                        if size == 4:
                            result[
                                "score4"
                            ] += 1

                        else:
                            result[
                                "score5"
                            ] += 1

                    cursor = (
                        local + 1
                    )

    result[
        "total_score"
    ] = (
        result[
            "score4"
        ]
        + result[
            "score5"
        ] * 3
    )

    return result


def main():

    with CONFIG.open(
        "r",
        encoding="utf-8",
    ) as file:

        config = json.load(
            file
        )

    people = (
        Path(
            config["game_dir"]
        )
        / "data"
        / "db"
        / "people_db.dat"
    ).read_bytes()

    uid_bytes = struct.pack(
        "<I",
        PLAYER_UID,
    )

    hits = find_all(
        people,
        uid_bytes,
    )

    ranked = []

    for hit in hits:

        result = score_window(
            people,
            hit,
        )

        ranked.append(
            {
                "offset":
                    hit,

                **result,
            }
        )

    ranked.sort(
        key=lambda item: (
            -item[
                "total_score"
            ],
            item[
                "offset"
            ],
        )
    )

    print("=" * 110)
    print(
        " FM06 BRASIL 2026 - "
        "SÁVIO ATTRIBUTE MATCHER"
    )
    print("=" * 110)

    print()
    print(
        f"UID hits: "
        f"{len(hits)}"
    )

    print()
    print(
        f"{'#':>2} "
        f"{'OFFSET':>12} "
        f"{'4-BYTE':>8} "
        f"{'5-BYTE':>8} "
        f"{'SCORE':>8}"
    )

    print("-" * 110)

    for index, item in enumerate(
        ranked,
        start=1,
    ):

        print(
            f"{index:>2} "
            f"0x{item['offset']:08X} "
            f"{item['score4']:>8} "
            f"{item['score5']:>8} "
            f"{item['total_score']:>8}"
        )

    print()
    print("=" * 110)
    print(
        " MELHOR CANDIDATO"
    )
    print("=" * 110)

    if not ranked:
        return

    best = ranked[0]

    print()
    print(
        f"UID offset: "
        f"0x{best['offset']:08X}"
    )

    print(
        f"score: "
        f"{best['total_score']}"
    )

    print()

    matches = sorted(
        best[
            "matches"
        ],
        key=lambda item: (
            item[
                "absolute"
            ],
            -item[
                "size"
            ],
        )
    )

    # Evita outra explosão de terminal.
    for item in matches[:40]:

        print(
            f"{item['group']:<10} "
            f"n={item['size']} "
            f"attr_index="
            f"{item['attribute_index']:<2} "
            f"rel="
            f"{item['relative']:+6} "
            f"abs="
            f"0x{item['absolute']:08X} "
            f"{item['values']}"
        )

    if len(matches) > 40:

        print()
        print(
            f"... "
            f"{len(matches)-40} "
            f"matches omitidos."
        )


if __name__ == "__main__":
    main()