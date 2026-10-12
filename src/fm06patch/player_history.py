from __future__ import annotations

import struct
from collections import defaultdict
from dataclasses import dataclass


# ============================================================
# FORMATOS DOS TRÊS ARQUIVOS
# ============================================================

# pl_hist_index.dat
#
# header:
#   0x00 .. 0x08
#
# +0x09:
#   uint32 quantidade de entradas
#
# +0x0D:
#   registros de 8 bytes:
#
#   uint32 player_uid
#   uint32 history_slot
#
INDEX_COUNT_OFFSET = 9
INDEX_DATA_START = 13
INDEX_RECORD_SIZE = 8


# pl_hist_id.dat
#
# header:
#   0x00 .. 0x08
#
# +0x09:
#   para cada history_slot:
#
#   uint32 start_relative
#   uint32 end_relative
#
# Ambos apontam para posições relativas
# dentro do payload de pl_hist_dt.dat.
#
SPAN_DATA_START = 9
SPAN_RECORD_SIZE = 8


# pl_hist_dt.dat
#
# header:
#   0x00 .. 0x08
#
# +0x09:
#   registros fixos de 17 bytes.
#
HISTORY_DATA_START = 9
HISTORY_RECORD_SIZE = 17


UINT32_NULL = 0xFFFFFFFF


# ============================================================
# HELPERS
# ============================================================

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


# ============================================================
# INDEX
# ============================================================

@dataclass(frozen=True)
class PlayerHistoryIndexEntry:
    """
    Uma entrada do pl_hist_index.dat.

    Estrutura confirmada:

        uint32 player_uid
        uint32 history_slot
    """

    ordinal: int
    file_offset: int

    player_uid: int
    history_slot: int

    @property
    def file_offset_hex(
        self,
    ) -> str:
        return (
            f"0x{self.file_offset:08X}"
        )


# ============================================================
# SPAN
# ============================================================

@dataclass(frozen=True)
class PlayerHistorySpan:
    """
    Entrada correspondente do pl_hist_id.dat.

    start_relative e end_relative são offsets
    relativos ao payload do pl_hist_dt.dat.

    O end_relative aponta para o INÍCIO do último
    registro, portanto o intervalo é inclusivo.
    """

    history_slot: int

    start_relative: int
    end_relative: int

    @property
    def record_count(
        self,
    ) -> int:

        difference = (
            self.end_relative
            - self.start_relative
        )

        return (
            difference
            // HISTORY_RECORD_SIZE
        ) + 1


# ============================================================
# REGISTRO DE 17 BYTES
# ============================================================

@dataclass(frozen=True)
class PlayerHistoryRecord:
    """
    Registro individual do histórico de carreira.

    Layout já confirmado:

        +0x00 uint16 year

        +0x02 uint8  flag_raw
              Semântica ainda não confirmada.
              Pode representar empréstimo em certos casos,
              mas NÃO vamos nomear isso ainda.

        +0x03 uint8  appearances

        +0x04 uint8  goals

        +0x05 uint32 transfer_fee_raw

              Valor monetário interno usado pelo FM.
              O jogo aplica conversão para a moeda
              configurada pelo usuário.

              Exemplo confirmado:

                  Fred / Cruzeiro / 2005
                  raw = 10.344.827

                  interface:
                  Lyon -> R$ 52,5M

        +0x09 uint32 club_uid

        +0x0D uint32 next_relative_offset

              Offset relativo do próximo registro.

              FFFFFFFF = fim da lista.
    """

    player_uid: int
    history_slot: int

    sequence: int

    relative_offset: int
    file_offset: int

    year: int

    flag_raw: int

    appearances: int
    goals: int

    transfer_fee_raw: int

    club_uid: int

    next_relative_offset: int | None

    data: bytes

    # --------------------------------------------------------
    # COMPATIBILIDADE
    # --------------------------------------------------------

    @property
    def amount_raw(
        self,
    ) -> int:
        """
        Mantido para o export_player_history.py
        já criado anteriormente.
        """

        return self.transfer_fee_raw

    # --------------------------------------------------------
    # HELPERS
    # --------------------------------------------------------

    @property
    def file_offset_hex(
        self,
    ) -> str:
        return (
            f"0x{self.file_offset:08X}"
        )

    @property
    def relative_offset_hex(
        self,
    ) -> str:
        return (
            f"0x{self.relative_offset:X}"
        )

    @property
    def is_last(
        self,
    ) -> bool:
        return (
            self.next_relative_offset
            is None
        )

    @property
    def has_transfer_fee(
        self,
    ) -> bool:
        """
        FFFFFFFF significa ausência de valor registrado.

        Zero é um valor válido e deve ser preservado.
        """

        return (
            self.transfer_fee_raw
            != UINT32_NULL
        )

    @property
    def expected_next_relative_offset(
        self,
    ) -> int:
        return (
            self.relative_offset
            + HISTORY_RECORD_SIZE
        )


# ============================================================
# DATABASE
# ============================================================

class PlayerHistoryDatabase:

    def __init__(
        self,
        index_data: bytes,
        spans_data: bytes,
        history_data: bytes,
    ):

        self.index_data = (
            index_data
        )

        self.spans_data = (
            spans_data
        )

        self.history_data = (
            history_data
        )

        self.entries = (
            self._parse_index()
        )

        self.spans = (
            self._parse_spans()
        )

        self._validate_database()

        by_uid = defaultdict(
            list
        )

        for entry in self.entries:

            by_uid[
                entry.player_uid
            ].append(
                entry
            )

        self.by_uid = dict(
            by_uid
        )

    # ========================================================
    # INDEX PARSER
    # ========================================================

    def _parse_index(
        self,
    ) -> list[
        PlayerHistoryIndexEntry
    ]:

        if (
            len(self.index_data)
            < INDEX_DATA_START
        ):
            raise ValueError(
                "pl_hist_index.dat "
                "muito pequeno."
            )

        declared_count = read_u32(
            self.index_data,
            INDEX_COUNT_OFFSET,
        )

        payload_size = (
            len(self.index_data)
            - INDEX_DATA_START
        )

        if (
            payload_size
            % INDEX_RECORD_SIZE
            != 0
        ):
            raise ValueError(
                "pl_hist_index.dat "
                "não possui framing "
                "de 8 bytes."
            )

        actual_count = (
            payload_size
            // INDEX_RECORD_SIZE
        )

        if (
            declared_count
            != actual_count
        ):
            raise ValueError(
                "Quantidade declarada "
                "em pl_hist_index.dat "
                "não confere: "
                f"header={declared_count}, "
                f"real={actual_count}"
            )

        result = []

        for ordinal in range(
            actual_count
        ):

            offset = (
                INDEX_DATA_START
                + ordinal
                * INDEX_RECORD_SIZE
            )

            player_uid = read_u32(
                self.index_data,
                offset,
            )

            history_slot = read_u32(
                self.index_data,
                offset + 4,
            )

            result.append(
                PlayerHistoryIndexEntry(
                    ordinal=ordinal,
                    file_offset=offset,
                    player_uid=player_uid,
                    history_slot=
                        history_slot,
                )
            )

        return result

    # ========================================================
    # SPAN PARSER
    # ========================================================

    def _parse_spans(
        self,
    ) -> list[
        PlayerHistorySpan
    ]:

        if (
            len(self.spans_data)
            < SPAN_DATA_START
        ):
            raise ValueError(
                "pl_hist_id.dat "
                "muito pequeno."
            )

        payload_size = (
            len(self.spans_data)
            - SPAN_DATA_START
        )

        if (
            payload_size
            % SPAN_RECORD_SIZE
            != 0
        ):
            raise ValueError(
                "pl_hist_id.dat "
                "não possui pares "
                "u32 completos."
            )

        count = (
            payload_size
            // SPAN_RECORD_SIZE
        )

        result = []

        for history_slot in range(
            count
        ):

            offset = (
                SPAN_DATA_START
                + history_slot
                * SPAN_RECORD_SIZE
            )

            start_relative = read_u32(
                self.spans_data,
                offset,
            )

            end_relative = read_u32(
                self.spans_data,
                offset + 4,
            )

            result.append(
                PlayerHistorySpan(
                    history_slot=
                        history_slot,

                    start_relative=
                        start_relative,

                    end_relative=
                        end_relative,
                )
            )

        return result

    # ========================================================
    # VALIDAÇÃO GERAL
    # ========================================================

    def _validate_database(
        self,
    ) -> None:

        # ----------------------------------------------------
        # Há exatamente um span para cada history_slot.
        # ----------------------------------------------------

        if (
            len(self.entries)
            != len(self.spans)
        ):
            raise ValueError(
                "pl_hist_index.dat e "
                "pl_hist_id.dat possuem "
                "quantidades diferentes: "
                f"{len(self.entries)} "
                f"vs "
                f"{len(self.spans)}"
            )

        # ----------------------------------------------------
        # A coluna history_slot do index deve formar
        # uma permutação completa:
        #
        # 0 .. quantidade-1
        # ----------------------------------------------------

        expected_slots = set(
            range(
                len(self.entries)
            )
        )

        actual_slots = {
            entry.history_slot
            for entry
            in self.entries
        }

        if (
            actual_slots
            != expected_slots
        ):
            raise ValueError(
                "history_slot do "
                "pl_hist_index.dat "
                "não forma uma permutação "
                "completa."
            )

        # ----------------------------------------------------
        # pl_hist_dt.dat é composto por registros
        # fixos de 17 bytes.
        # ----------------------------------------------------

        history_payload_size = (
            len(self.history_data)
            - HISTORY_DATA_START
        )

        if (
            history_payload_size
            % HISTORY_RECORD_SIZE
            != 0
        ):
            raise ValueError(
                "pl_hist_dt.dat "
                "não possui framing "
                "de 17 bytes."
            )

        # ----------------------------------------------------
        # Todos os spans devem apontar para limites
        # válidos de registro.
        # ----------------------------------------------------

        for span in self.spans:

            start = (
                span.start_relative
            )

            end = (
                span.end_relative
            )

            if (
                start
                % HISTORY_RECORD_SIZE
                != 0
            ):
                raise ValueError(
                    "Start de histórico "
                    "não é múltiplo de 17: "
                    f"slot="
                    f"{span.history_slot}, "
                    f"value="
                    f"{start}"
                )

            if (
                end
                % HISTORY_RECORD_SIZE
                != 0
            ):
                raise ValueError(
                    "End de histórico "
                    "não é múltiplo de 17: "
                    f"slot="
                    f"{span.history_slot}, "
                    f"value="
                    f"{end}"
                )

            if (
                end < start
            ):
                raise ValueError(
                    "Span invertido: "
                    f"slot="
                    f"{span.history_slot}"
                )

            if (
                end
                + HISTORY_RECORD_SIZE
                > history_payload_size
            ):
                raise ValueError(
                    "Span aponta além "
                    "do pl_hist_dt.dat: "
                    f"slot="
                    f"{span.history_slot}"
                )

    # ========================================================
    # CONSULTAS
    # ========================================================

    def entries_for_uid(
        self,
        player_uid: int,
    ) -> list[
        PlayerHistoryIndexEntry
    ]:

        return list(
            self.by_uid.get(
                player_uid,
                [],
            )
        )

    def player_exists(
        self,
        player_uid: int,
    ) -> bool:

        return (
            player_uid
            in self.by_uid
        )

    def span(
        self,
        history_slot: int,
    ) -> PlayerHistorySpan:

        if not (
            0
            <= history_slot
            < len(self.spans)
        ):
            raise KeyError(
                "History slot "
                f"{history_slot} "
                "inválido."
            )

        return self.spans[
            history_slot
        ]

    # ========================================================
    # RECORD PARSER
    # ========================================================

    def records_for_entry(
        self,
        entry:
            PlayerHistoryIndexEntry,
    ) -> list[
        PlayerHistoryRecord
    ]:

        span = self.span(
            entry.history_slot
        )

        result = []

        sequence = 0

        for relative_offset in range(
            span.start_relative,
            span.end_relative
            + HISTORY_RECORD_SIZE,
            HISTORY_RECORD_SIZE,
        ):

            file_offset = (
                HISTORY_DATA_START
                + relative_offset
            )

            data = (
                self.history_data[
                    file_offset:
                    file_offset
                    + HISTORY_RECORD_SIZE
                ]
            )

            if (
                len(data)
                != HISTORY_RECORD_SIZE
            ):
                raise ValueError(
                    "Registro de histórico "
                    "truncado: "
                    f"player="
                    f"{entry.player_uid}, "
                    f"slot="
                    f"{entry.history_slot}, "
                    f"offset="
                    f"0x{file_offset:X}"
                )

            # ------------------------------------------------
            # +0x00 uint16 YEAR
            # ------------------------------------------------

            year = read_u16(
                data,
                0,
            )

            # ------------------------------------------------
            # +0x02 uint8 FLAG
            #
            # Semântica ainda não confirmada.
            # ------------------------------------------------

            flag_raw = data[
                2
            ]

            # ------------------------------------------------
            # +0x03 APPEARANCES
            # ------------------------------------------------

            appearances = data[
                3
            ]

            # ------------------------------------------------
            # +0x04 GOALS
            # ------------------------------------------------

            goals = data[
                4
            ]

            # ------------------------------------------------
            # +0x05 TRANSFER FEE
            #
            # Valor monetário interno.
            #
            # FFFFFFFF = sem valor.
            # ------------------------------------------------

            transfer_fee_raw = read_u32(
                data,
                5,
            )

            # ------------------------------------------------
            # +0x09 CLUB UID
            # ------------------------------------------------

            club_uid = read_u32(
                data,
                9,
            )

            # ------------------------------------------------
            # +0x0D NEXT
            # ------------------------------------------------

            next_raw = read_u32(
                data,
                13,
            )

            if (
                next_raw
                == UINT32_NULL
            ):
                next_relative_offset = (
                    None
                )
            else:
                next_relative_offset = (
                    next_raw
                )

            record = (
                PlayerHistoryRecord(
                    player_uid=
                        entry.player_uid,

                    history_slot=
                        entry.history_slot,

                    sequence=
                        sequence,

                    relative_offset=
                        relative_offset,

                    file_offset=
                        file_offset,

                    year=
                        year,

                    flag_raw=
                        flag_raw,

                    appearances=
                        appearances,

                    goals=
                        goals,

                    transfer_fee_raw=
                        transfer_fee_raw,

                    club_uid=
                        club_uid,

                    next_relative_offset=
                        next_relative_offset,

                    data=
                        data,
                )
            )

            result.append(
                record
            )

            sequence += 1

        # ----------------------------------------------------
        # VALIDA O ENCADEAMENTO INTERNO
        # ----------------------------------------------------

        self._validate_record_chain(
            entry,
            result,
        )

        return result

    # ========================================================
    # LINKED LIST VALIDATION
    # ========================================================

    def _validate_record_chain(
        self,
        entry:
            PlayerHistoryIndexEntry,

        records:
            list[
                PlayerHistoryRecord
            ],
    ) -> None:

        if not records:
            raise ValueError(
                "History span vazio: "
                f"player="
                f"{entry.player_uid}"
            )

        for index, record in enumerate(
            records
        ):

            is_last = (
                index
                == len(records) - 1
            )

            if is_last:

                if (
                    record.next_relative_offset
                    is not None
                ):
                    raise ValueError(
                        "Último registro "
                        "não termina em "
                        "FFFFFFFF: "
                        f"player="
                        f"{entry.player_uid}, "
                        f"sequence="
                        f"{record.sequence}"
                    )

                continue

            expected = (
                records[
                    index + 1
                ].relative_offset
            )

            actual = (
                record.next_relative_offset
            )

            if (
                actual
                != expected
            ):
                raise ValueError(
                    "Ponteiro NEXT "
                    "não aponta para o "
                    "registro seguinte: "
                    f"player="
                    f"{entry.player_uid}, "
                    f"sequence="
                    f"{record.sequence}, "
                    f"expected="
                    f"0x{expected:X}, "
                    f"actual="
                    f"{'None' if actual is None else hex(actual)}"
                )

    # ========================================================
    # TODOS OS REGISTROS DO JOGADOR
    # ========================================================

    def records(
        self,
        player_uid: int,
    ) -> list[
        PlayerHistoryRecord
    ]:

        entries = (
            self.entries_for_uid(
                player_uid
            )
        )

        if not entries:
            raise KeyError(
                "Player UID "
                f"{player_uid} "
                "não encontrado no "
                "pl_hist_index.dat."
            )

        result = []

        for entry in entries:

            result.extend(
                self.records_for_entry(
                    entry
                )
            )

        return result