from __future__ import annotations

import struct
from dataclasses import dataclass

from .lang_db import ClubNameRecord, utf16_length


# Valor observado repetidamente nos registros brasileiros
# de client_db/server_db.
#
# A semântica ainda NÃO está confirmada.
# Portanto chamamos apenas de "group_marker".
BRAZIL_GROUP_MARKER = 189

MAX_CONTAINER_SPAN = 8192


@dataclass(frozen=True)
class LegacyClubContainer:
    source: str

    offset: int
    end: int

    field_a: int
    field_b: int
    group_marker: int

    @property
    def offset_hex(self) -> str:
        return f"0x{self.offset:08X}"

    @property
    def size(self) -> int:
        return self.end - self.offset


@dataclass(frozen=True)
class ClubEntityMapping:
    lang: ClubNameRecord

    client: LegacyClubContainer | None
    server: LegacyClubContainer | None

    client_candidates: int
    server_candidates: int

    @property
    def status(self) -> str:
        if (
            self.client_candidates == 1
            and self.server_candidates == 1
        ):
            return "OK"

        if (
            self.client_candidates > 1
            or self.server_candidates > 1
        ):
            return "AMBIG"

        return "PARTIAL"


def read_u32(
    data: bytes,
    offset: int,
) -> int:
    return struct.unpack_from(
        "<I",
        data,
        offset,
    )[0]


def string_token(text: str) -> bytes:
    """
    Representação observada nos bancos:

        uint32 comprimento UTF-16
        wchar[]
        00 00
    """

    encoded = text.encode("utf-16le")

    return (
        struct.pack(
            "<I",
            utf16_length(text),
        )
        + encoded
        + b"\x00\x00"
    )


def scan_group_containers(
    data: bytes,
    source: str,
    group_marker: int = BRAZIL_GROUP_MARKER,
) -> list[LegacyClubContainer]:
    """
    Detecta o cabeçalho observado em client_db/server_db:

        uint32 field_a
        uint32 field_b
        uint8  zero
        uint32 group_marker

    O significado de field_a/field_b ainda será descoberto.
    """

    marker_pattern = (
        b"\x00"
        + struct.pack(
            "<I",
            group_marker,
        )
    )

    headers: list[
        tuple[int, int, int]
    ] = []

    cursor = 0

    while True:
        marker_pos = data.find(
            marker_pattern,
            cursor,
        )

        if marker_pos == -1:
            break

        header_offset = (
            marker_pos - 8
        )

        if (
            header_offset >= 0
            and header_offset + 13 <= len(data)
        ):
            field_a = read_u32(
                data,
                header_offset,
            )

            field_b = read_u32(
                data,
                header_offset + 4,
            )

            # Os valores reais encontrados são pequenos.
            # Mantemos margem grande sem aceitar qualquer
            # sequência binária aleatória.
            if (
                1 <= field_a <= 10000
                and 1 <= field_b <= 100000
            ):
                headers.append(
                    (
                        header_offset,
                        field_a,
                        field_b,
                    )
                )

        cursor = marker_pos + 1

    # Remove duplicatas por offset.
    unique = {}

    for offset, field_a, field_b in headers:
        unique[offset] = (
            field_a,
            field_b,
        )

    ordered = sorted(
        unique.items(),
        key=lambda item: item[0],
    )

    result: list[
        LegacyClubContainer
    ] = []

    for index, (
        offset,
        fields,
    ) in enumerate(ordered):

        field_a, field_b = fields

        if index + 1 < len(ordered):
            next_offset = (
                ordered[index + 1][0]
            )
        else:
            next_offset = len(data)

        end = min(
            next_offset,
            offset + MAX_CONTAINER_SPAN,
            len(data),
        )

        result.append(
            LegacyClubContainer(
                source=source,
                offset=offset,
                end=end,
                field_a=field_a,
                field_b=field_b,
                group_marker=group_marker,
            )
        )

    return result


def container_contains_club(
    data: bytes,
    container: LegacyClubContainer,
    lang_record: ClubNameRecord,
) -> bool:

    segment = data[
        container.offset:
        container.end
    ]

    full_token = string_token(
        lang_record.full_name
    )

    short_token = string_token(
        lang_record.short_name
    )

    if full_token not in segment:
        return False

    if short_token not in segment:
        return False

    return True

def container_match_distance(
    data: bytes,
    container: LegacyClubContainer,
    lang_record: ClubNameRecord,
) -> int | None:

    segment = data[
        container.offset:
        container.end
    ]

    full_token = string_token(
        lang_record.full_name
    )

    short_token = string_token(
        lang_record.short_name
    )

    full_pos = segment.find(
        full_token
    )

    short_pos = segment.find(
        short_token
    )

    if (
        full_pos == -1
        or short_pos == -1
    ):
        return None

    return min(
        full_pos,
        short_pos,
    )

def match_record(
    data: bytes,
    containers: list[
        LegacyClubContainer
    ],
    lang_record: ClubNameRecord,
) -> list[LegacyClubContainer]:

    return [
        container
        for container in containers
        if container_contains_club(
            data,
            container,
            lang_record,
        )
    ]


def map_club_entities(
    lang_records: list[
        ClubNameRecord
    ],
    client_data: bytes,
    server_data: bytes,
) -> list[ClubEntityMapping]:

    client_containers = (
        scan_group_containers(
            client_data,
            source="client_db",
        )
    )

    server_containers = (
        scan_group_containers(
            server_data,
            source="server_db",
        )
    )

    def resolve_owners(
        data: bytes,
        containers: list[
            LegacyClubContainer
        ],
    ):
        """
        Um container real só pode pertencer a uma entidade.

        Isso também elimina o problema do último registro
        brasileiro capturar strings dos países seguintes.
        """

        owners: dict[
            int,
            tuple[
                int,
                ClubNameRecord,
                LegacyClubContainer,
            ],
        ] = {}

        for lang_record in lang_records:

            for container in containers:

                distance = (
                    container_match_distance(
                        data,
                        container,
                        lang_record,
                    )
                )

                if distance is None:
                    continue

                current = owners.get(
                    container.offset
                )

                candidate = (
                    distance,
                    lang_record,
                    container,
                )

                if current is None:
                    owners[
                        container.offset
                    ] = candidate
                    continue

                current_distance = (
                    current[0]
                )

                # O verdadeiro registro tende a estar
                # mais próximo do início do container.
                if (
                    distance
                    < current_distance
                ):
                    owners[
                        container.offset
                    ] = candidate

        by_lang: dict[
            int,
            list[
                LegacyClubContainer
            ],
        ] = {}

        for (
            _,
            lang_record,
            container,
        ) in owners.values():

            by_lang.setdefault(
                lang_record.record_id,
                [],
            ).append(
                container
            )

        return by_lang

    client_by_lang = resolve_owners(
        client_data,
        client_containers,
    )

    server_by_lang = resolve_owners(
        server_data,
        server_containers,
    )

    mappings: list[
        ClubEntityMapping
    ] = []

    for lang_record in lang_records:

        client_matches = (
            client_by_lang.get(
                lang_record.record_id,
                [],
            )
        )

        server_matches = (
            server_by_lang.get(
                lang_record.record_id,
                [],
            )
        )

        if (
            not client_matches
            and not server_matches
        ):
            continue

        client = (
            client_matches[0]
            if len(client_matches) == 1
            else None
        )

        server = (
            server_matches[0]
            if len(server_matches) == 1
            else None
        )

        mappings.append(
            ClubEntityMapping(
                lang=lang_record,
                client=client,
                server=server,
                client_candidates=len(
                    client_matches
                ),
                server_candidates=len(
                    server_matches
                ),
            )
        )

    return mappings