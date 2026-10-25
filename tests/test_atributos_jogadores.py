import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import atributos_jogadores as aj  # noqa: E402

# Teste 1 de 25/10 (docs/reversing/rea-atributos.md): os 79 bytes gravados na T3 e o que o
# jogo tinha na memória logo depois do New Game (Playing+0x1C), antes do treino.
ARRASCAETA_CA = 160
ARRASCAETA_FILE = [1, 1, 1, 1, 13, 20, 1, 1, 1, 1, 1, 20, 1, 1, 1, 1, 1, 13, 1, 1, 20, 1, 1, 1, 1, 14, 17, 16, 8, 15, 3,
                   17, 20, 14, 4, 20, 1, 1, 1, 1, 1, 1, 12, 14, 1, 7, 1, 18, 19, 8, 20, 17, 15, 12, 13, 5, 1, 1, 1, 14,
                   16, 9, 14, 13, 8, 13, 7, 14, 9, 15, 8, 15, 15, 8, 12, 13, 14, 18, 13]
ARRASCAETA_MEMORY = [1, 1, 1, 1, 20, 20, 1, 1, 1, 1, 1, 20, 1, 1, 1, 1, 1, 13, 1, 1, 20, 1, 1, 1, 1, -10, 5, 0, -40, -5,
                     -65, 5, 25, 70, -60, 33, -75, -75, -75, -77, -77, -78, -20, -10, -77, -45, -78, 10, 15, 40, 100,
                     85, 75, 60, 65, 25, 5, 5, 5, 70, 80, 45, 70, 65, 40, 65, 35, 70, 45, 75, 40, 75, 75, 40, 60, 65,
                     70, 10, -15]
DANILO_CA = 152
DANILO_FILE = [1, 1, 20, 1, 1, 1, 1, 15, 1, 16, 1, 20, 1, 20, 16, 1, 1, 1, 1, 1, 1, 1, 1, 1, 15, 6, 7, 2, 15, 6, 18, 3,
               11, 7, 18, 7, 1, 1, 1, 1, 1, 1, 17, 14, 1, 16, 1, 11, 10, 8, 20, 6, 4, 14, 12, 6, 1, 1, 1, 12, 5, 15, 13,
               12, 15, 12, 8, 13, 14, 15, 13, 11, 13, 8, 14, 13, 14, 10, 14]
DANILO_MEMORY = [1, 10, 20, 1, 1, 1, 1, 15, 1, 16, 1, 20, 1, 20, 16, 1, 1, 1, 1, 1, 1, 1, 1, 1, 15, -42, -37, -62, 3,
                 -42, 18, -57, -17, 39, 18, -37, -76, -74, -72, -73, -72, -71, 13, -2, -75, 8, -73, -17, -22, 44, 100,
                 30, 24, 74, 64, 34, 5, 5, 5, 64, 29, 79, 69, 64, 79, 64, 40, 69, 74, 75, 65, 59, 65, 40, 70, 65, 70,
                 -22, -2]


def _random_in_game(i, f):
    """Os bytes que o jogo sorteia: posições genéricas, relativos 20/1 e zeros."""
    return i < 9 or (i in aj.RELATIVE and f in (1, 20)) or f == 0


@pytest.mark.parametrize("file, memory, ca", [(ARRASCAETA_FILE, ARRASCAETA_MEMORY, ARRASCAETA_CA),
                                              (DANILO_FILE, DANILO_MEMORY, DANILO_CA)])
def test_model_matches_game_memory(file, memory, ca):
    weights = aj.Weights.load()
    raw = aj.convert(file, ca)
    model = aj.fit(raw, aj.weights_for(raw, weights), ca)
    assert [i for i in range(79) if not _random_in_game(i, file[i]) and model[i] != memory[i]] == []


def test_danilo_was_moved_one_point_up():
    weights = aj.Weights.load()
    assert aj.game_shift(DANILO_FILE, DANILO_CA, weights) == 4        # CA alto para os atributos: +1 na ficha
    assert aj.game_shift(ARRASCAETA_FILE, ARRASCAETA_CA, weights) == 0


def test_convert_zidane():
    # 8076 (CA 185): Cruzamento 17 -> -7, Finta 18 -> -2, Cabeceio 14 -> -22, Passe 19 -> 2; absoluto 5*f
    values = [1] * 79
    values[25], values[26], values[28], values[32], values[63] = 17, 18, 14, 19, 14
    raw = aj.convert(values, 185)
    assert (raw[25], raw[26], raw[28], raw[32], raw[63]) == (-7, -2, -22, 2, 70)


@pytest.mark.parametrize("i, raw, ca, expected", [
    (27, -2, 168, 17), (32, 32, 168, 20), (30, -67, 168, 4),     # fichas do teste 1 (Paquetá)
    (27, -60, 152, 4), (43, 0, 152, 16), (28, 5, 152, 17),       # Danilo
    (32, -18, 154, 12), (34, -78, 154, 1),                        # Pedro
    (63, 67, 168, 13), (61, 81, 152, 16), (63, 69, 154, 14),     # absolutos
])
def test_shown_matches_screenshots(i, raw, ca, expected):
    assert aj.shown(i, raw, ca) == expected


def test_choose_ca_hits_target_shift_with_even_ca():
    weights = aj.Weights.load()
    ca, shift = aj.choose_ca(ARRASCAETA_FILE, ARRASCAETA_CA, weights)
    assert shift == aj.ALVO_AJUSTE and ca % 2 == 0
    sheet = aj.expected_sheet(ARRASCAETA_FILE, ca, weights)
    for i in range(25, 79):
        if not _random_in_game(i, ARRASCAETA_FILE[i]):
            assert sheet[i] == ARRASCAETA_FILE[i], i


def test_t3_values_maps_names():
    spec = {"name": "x", "attributes": {"Finalização": 17, "Velocidade": 9, "Left foot": 20},
            "positions": {"Att. Center": 20}}
    out = aj.t3_values(spec, bytes(79))
    assert (out[27], out[63], out[49], out[22]) == (17, 9, 20, 20)
    with pytest.raises(ValueError):
        aj.t3_values({"name": "x", "attributes": {"Passe": 21}}, bytes(79))


def _end(index, uid, following):
    """Fim da parte comum: u16 ano, 00 00 00, u32 índice, u32 UID e o u32 do índice seguinte."""
    return struct.pack("<H", 1985) + b"\0\0\0" + struct.pack("<III", index, uid, following)


def _fake_people(players, fake_end_in=None):
    """people_db mínimo no formato do banco: cabeçalho (o 5º u32 é o índice do 1º registro),
    tabela A encadeada fora de ordem, T2 e T3. ``fake_end_in``: UID cujo registro traz no
    meio um falso fim de registro."""
    order = list(range(len(players)))[::-1]               # em ordem decrescente no arquivo
    a = bytearray()
    for pos, i in enumerate(order):
        body = bytes([2]) + struct.pack("<5H", 100, 100, 50, 120, 150) + bytes(40)
        if players[i] == fake_end_in:
            body += _end(5077, 999, 5078)[:-4] + bytes([2]) + bytes([0x55] * 20)
        following = 5000 + order[pos + 1] if pos + 1 < len(order) else 0xFFFFFFFF
        a += body + _end(5000 + i, players[i], following)   # índices da tabela A na casa dos milhares
    t2 = b"".join(bytes([0]) + bytes(range(1, 9)) + struct.pack("<II", i, uid) for i, uid in enumerate(players))
    t3 = b"".join(bytes([0]) + bytes([10] * 79) + b"\0" + struct.pack("<II", i, uid) for i, uid in enumerate(players))
    n = len(players)
    head = b"\x02\x01tad.\x27\x01\x00" + struct.pack("<5I", n, n, n, 0, 5000 + order[0])
    return head + bytes(a[:-4]) + struct.pack("<I", n) + t2 + struct.pack("<I", n) + t3 + struct.pack("<I", 0)


def test_tables_and_records():
    uids = [111, 222, 333, 444]
    people = _fake_people(uids, fake_end_in=333)
    tab = aj.tables(people)
    t2 = aj.index_fixed(people, tab.t2, tab.n2, aj.T2_SIZE)
    t3 = aj.index_fixed(people, tab.t3, tab.n3, aj.T3_SIZE)
    assert list(t2) == uids and list(t3) == uids
    assert people[t2[333] + 1:t2[333] + 9] == bytes(range(1, 9))
    records = aj.person_records(people, tab.a_end)
    assert sorted(records) == uids                     # o falso fim (UID 999) não vira registro
    for uid in uids:
        start, end = records[uid]
        assert people[start] == aj.PLAYER and struct.unpack_from("<HH", people, start + aj.CA_AT) == (120, 150)
        assert struct.unpack_from("<I", people, end - 4)[0] == uid


def test_apply_moves_sets_and_clears_bits():
    moves = aj.load_moves()
    name = next(iter(moves))
    index = moves[name]
    added = aj.apply_moves(bytes(8), {"add": [name]})
    assert added[index // 8] == 1 << index % 8 and sum(added) == 1 << index % 8
    assert aj.apply_moves(added, {"remove": [index]}) == bytes(8)


def test_moves_layout_check():
    record = bytearray(200)
    for k in range(4):                                     # 4 datas "dia 0, 1900" em +71
        struct.pack_into("<HH", record, aj.MOVES_DATES_AT + 4 * k, 0, 1900)
    people = bytes(record)
    assert aj._moves_layout_ok(people, 0, aj.MOVES_AT + 8 + 12)
    assert aj._moves_layout_ok(people, 0, aj.MOVES_AT + 8 + 28)
    assert not aj._moves_layout_ok(people, 0, aj.MOVES_AT + 8 + 20)
    record[aj.MOVES_DATES_AT + 2] = 0                      # ano 0: parte variável com outro tamanho
    assert not aj._moves_layout_ok(bytes(record), 0, aj.MOVES_AT + 8 + 12)


def test_contract_writes_follow_injector_rules():
    spec = {"inicio": "2024-07-01", "fim": "2025-06-30", "numero": 21, "salario_mensal_brl": 100000}
    writes = {label.split()[0]: (at, data) for at, data, label in aj.contract_writes(bytes(64), 10, spec, -20, 0.005)}
    assert writes["salário"] == (10 + aj.CONTRACT_WAGE, struct.pack("<I", 500 * 10 + 2))
    assert writes["fim"] == (10 + aj.CONTRACT_END, struct.pack("<HH", 364, 2006))       # antes de 1/1/2006: 31/12
    assert writes["início"] == (10 + aj.CONTRACT_START, struct.pack("<HH", 182, 2004))  # 1/7/2004 (bissexto; +20 = 2024)
    assert writes["número"] == (10 + aj.CONTRACT_NUMBER, bytes([21]))


def test_main_contract_picks_block_with_end_date():
    from types import SimpleNamespace
    people = bytearray(200)
    struct.pack_into("<HH", people, 40 + aj.CONTRACT_END, 0, 1900)     # clube anterior
    struct.pack_into("<HH", people, 100 + aj.CONTRACT_END, 180, 2007)  # contrato atual
    contract = SimpleNamespace(at=40, others=(100,))
    assert aj.main_contract(bytes(people), contract, 0, 190) == 100
    assert aj.main_contract(bytes(people), SimpleNamespace(at=40, others=()), 0, 190) == 40
    struct.pack_into("<HH", people, 40 + aj.CONTRACT_END, 180, 2006)   # dois com data: ambíguo
    assert aj.main_contract(bytes(people), contract, 0, 190) is None
