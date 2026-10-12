from __future__ import annotations

import argparse
import json
import struct
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

CONFIG = (
    ROOT
    / "config"
    / "local.json"
)


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

        result.append(
            pos
        )

        cursor = pos + 1

    return result


def signature_score(
    data: bytes,
    uid_offset: int,
) -> int:

    if (
        uid_offset < 19
        or uid_offset + 19
        >= len(data)
    ):
        return 0

    score = 0

    # Essa constante apareceu nas três
    # âncoras brasileiras.
    if u32(
        data,
        uid_offset - 15,
    ) == 255:

        score += 3

    # Também apareceu nas três âncoras.
    if data[
        uid_offset + 8
    ] == 1:

        score += 2

    # Cinco valores consecutivos na faixa
    # plausível 1..250.
    #
    # Ainda não atribuímos semântica.
    for relative in (
        9,
        11,
        13,
        15,
        17,
    ):

        value = u16(
            data,
            uid_offset + relative,
        )

        if (
            1 <= value <= 250
        ):
            score += 1

    return score


def print_signature(
    data: bytes,
    uid_offset: int,
):

    print(
        f"    -19 u32 = "
        f"{u32(data, uid_offset - 19)}"
    )

    print(
        f"    -15 u32 = "
        f"{u32(data, uid_offset - 15)}"
    )

    print(
        f"    -11 u16 = "
        f"{u16(data, uid_offset - 11)}"
    )

    print(
        f"     -9 u16 = "
        f"{u16(data, uid_offset - 9)}"
    )

    print(
        f"     -4 u32 = "
        f"{u32(data, uid_offset - 4)}"
    )

    print(
        f"     +0 u32 = "
        f"{u32(data, uid_offset)} "
        f"<UID>"
    )

    print(
        f"     +4 u32 = "
        f"{u32(data, uid_offset + 4)}"
    )

    print(
        f"     +8 u8  = "
        f"{data[uid_offset + 8]}"
    )

    for relative in (
        9,
        11,
        13,
        15,
        17,
    ):

        print(
            f"    +{relative:<2} u16 = "
            f"{u16(data, uid_offset + relative)}"
        )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "uid",
        type=int,
    )

    parser.add_argument(
        "--name",
        default="",
    )

    parser.add_argument(
        "--min-score",
        type=int,
        default=8,
    )

    parser.add_argument(
        "--top",
        type=int,
        default=10,
    )

    args = parser.parse_args()

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

    needle = struct.pack(
        "<I",
        args.uid,
    )

    raw_hits = find_all(
        people,
        needle,
    )

    candidates = []

    for offset in raw_hits:

        score = signature_score(
            people,
            offset,
        )

        candidates.append(
            {
                "offset":
                    offset,

                "score":
                    score,
            }
        )

    candidates.sort(
        key=lambda item: (
            -item[
                "score"
            ],
            item[
                "offset"
            ],
        )
    )

    score_distribution = Counter(
        item[
            "score"
        ]
        for item in candidates
    )

    strong = [
        item
        for item in candidates
        if (
            item[
                "score"
            ]
            >= args.min_score
        )
    ]

    print("=" * 95)
    print(
        " FM06 BRASIL 2026 - "
        "PERSON UID PROBE"
    )
    print("=" * 95)

    print()
    print(
        f"Nome         : "
        f"{args.name or '-'}"
    )

    print(
        f"UID          : "
        f"{args.uid}"
    )

    print(
        f"Raw hits     : "
        f"{len(raw_hits):,}"
    )

    print(
        f"Strong hits  : "
        f"{len(strong):,} "
        f"(score >= "
        f"{args.min_score})"
    )

    print()

    print(
        "Distribuição:"
    )

    for score in sorted(
        score_distribution,
        reverse=True,
    ):

        print(
            f"  score "
            f"{score:>2}: "
            f"{score_distribution[score]:,}"
        )

    # Se houver candidatos fortes,
    # imprime SOMENTE eles.
    #
    # Se não houver, imprime somente
    # os melhores N para diagnóstico.
    if strong:

        display = strong[
            :args.top
        ]

    else:

        print()
        print(
            "Nenhum candidato atingiu "
            "o score mínimo."
        )

        print(
            f"Mostrando os "
            f"{args.top} melhores."
        )

        display = candidates[
            :args.top
        ]

    for index, item in enumerate(
        display,
        start=1,
    ):

        offset = item[
            "offset"
        ]

        print()
        print("-" * 95)

        print(
            f"#{index} "
            f"0x{offset:08X} "
            f"score="
            f"{item['score']}"
        )

        print_signature(
            people,
            offset,
        )

    if (
        len(strong)
        > args.top
    ):

        print()
        print(
            f"... "
            f"{len(strong)-args.top} "
            f"candidato(s) forte(s) "
            f"omitidos."
        )


if __name__ == "__main__":
    main()