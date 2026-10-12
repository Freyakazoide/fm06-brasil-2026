from __future__ import annotations

import struct
from dataclasses import dataclass


def read_u16(
    data: bytes,
    offset: int,
) -> int:
    return struct.unpack_from(
        "<H",
        data,
        offset,
    )[0]


def read_u32(
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
) -> list[int]:

    result = []
    cursor = 0

    while True:

        position = data.find(
            needle,
            cursor,
        )

        if position == -1:
            break

        result.append(
            position
        )

        cursor = (
            position + 1
        )

    return result


@dataclass(frozen=True)
class PlayerCoreRecord:
    """
    Subestrutura do people_db identificada
    através de UIDs reais mostrados pelo FM06.

    O offset principal é a posição do
    uint32 player_uid.

    Layout conhecido relativo ao UID:

        -19 u32  nation_group_id (provisório)
        -15 u32  marker_255

        -11 u16  unknown_before_year
         -9 u16  year_like
         -7 ...  ainda não decodificado
         -4 u32  unknown_before_uid

         +0 u32  player_uid
         +4 u32  unknown_reference
         +8 u8   player_type_raw

         +9 u16  reputation_1
        +11 u16  reputation_2
        +13 u16  reputation_3

        +15 u16  current_ability
        +17 u16  potential_ability
    """

    uid_offset: int

    nation_internal_id: int
    marker_255: int

    unknown_before_year: int
    year_like: int

    unknown_before_uid: int

    player_uid: int

    unknown_reference: int

    player_type_raw: int

    reputation_1: int
    reputation_2: int
    reputation_3: int

    current_ability: int
    potential_ability: int

    score: int

    @property
    def uid_offset_hex(
        self,
    ) -> str:
        return (
            f"0x{self.uid_offset:08X}"
        )


class PeopleDatabase:

    def __init__(
        self,
        data: bytes,
    ):
        self.data = data

    def _score_candidate(
        self,
        uid_offset: int,
    ) -> int:

        if (
            uid_offset < 19
            or uid_offset + 19
            >= len(self.data)
        ):
            return 0

        score = 0

        marker = read_u32(
            self.data,
            uid_offset - 15,
        )

        if marker == 255:
            score += 3

        player_type = self.data[
            uid_offset + 8
        ]

        # Já observamos 1 e 2 em registros
        # legítimos, então não limitamos a 1.
        if (
            1 <= player_type <= 10
        ):
            score += 2

        ratings = [
            read_u16(
                self.data,
                uid_offset + relative,
            )
            for relative in (
                9,
                11,
                13,
                15,
                17,
            )
        ]

        for rating in ratings:

            if (
                1 <= rating <= 200
            ):
                score += 1

        return score

    def _parse_candidate(
        self,
        uid_offset: int,
    ) -> PlayerCoreRecord:

        return PlayerCoreRecord(
            uid_offset=
                uid_offset,

            nation_internal_id=
                read_u32(
                    self.data,
                    uid_offset - 19,
                ),

            marker_255=
                read_u32(
                    self.data,
                    uid_offset - 15,
                ),

            unknown_before_year=
                read_u16(
                    self.data,
                    uid_offset - 11,
                ),

            year_like=
                read_u16(
                    self.data,
                    uid_offset - 9,
                ),

            unknown_before_uid=
                read_u32(
                    self.data,
                    uid_offset - 4,
                ),

            player_uid=
                read_u32(
                    self.data,
                    uid_offset,
                ),

            unknown_reference=
                read_u32(
                    self.data,
                    uid_offset + 4,
                ),

            player_type_raw=
                self.data[
                    uid_offset + 8
                ],

            reputation_1=
                read_u16(
                    self.data,
                    uid_offset + 9,
                ),

            reputation_2=
                read_u16(
                    self.data,
                    uid_offset + 11,
                ),

            reputation_3=
                read_u16(
                    self.data,
                    uid_offset + 13,
                ),

            current_ability=
                read_u16(
                    self.data,
                    uid_offset + 15,
                ),

            potential_ability=
                read_u16(
                    self.data,
                    uid_offset + 17,
                ),

            score=
                self._score_candidate(
                    uid_offset
                ),
        )

    def candidates_for_uid(
        self,
        player_uid: int,
    ) -> list[
        PlayerCoreRecord
    ]:

        needle = struct.pack(
            "<I",
            player_uid,
        )

        offsets = find_all(
            self.data,
            needle,
        )

        candidates = []

        for offset in offsets:

            if (
                offset < 19
                or offset + 19
                >= len(self.data)
            ):
                continue

            candidate = (
                self._parse_candidate(
                    offset
                )
            )

            candidates.append(
                candidate
            )

        candidates.sort(
            key=lambda item: (
                -item.score,
                item.uid_offset,
            )
        )

        return candidates

    def player(
        self,
        player_uid: int,
        minimum_score: int = 8,
    ) -> PlayerCoreRecord:

        candidates = (
            self.candidates_for_uid(
                player_uid
            )
        )

        strong = [
            candidate
            for candidate
            in candidates
            if (
                candidate.score
                >= minimum_score
            )
        ]

        if not strong:

            raise KeyError(
                f"Player UID "
                f"{player_uid} "
                f"não possui candidato "
                f"forte no people_db."
            )

        if len(strong) > 1:

            raise ValueError(
                f"Player UID "
                f"{player_uid} "
                f"possui "
                f"{len(strong)} "
                f"candidatos fortes."
            )

        return strong[0]