import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import people_contracts  # noqa: E402

ORIGINAL = ROOT / "workspace" / "baseline" / "people_db.original.dat"


@pytest.mark.skipif(not ORIGINAL.exists(), reason="sem o people_db original em workspace/baseline")
def test_every_block_belongs_to_the_person_in_it():
    """O bloco (64, u32 pessoa, 00, u32 clube...) é da pessoa do próprio bloco. Até 25/10 2.682
    contratos de um bloco eram de outra pessoa e o reforço trocava clubes (Ribeiro)."""
    people = ORIGINAL.read_bytes()
    found = people_contracts.contracts(people, multi=True)
    assert len(found) > 150_000
    for contract in found.values():
        for at in (contract.at, *contract.others):
            assert people[at - 6] == 0x64
            assert struct.unpack_from("<I", people, at - 5)[0] == contract.index
    # Ribeiro (137569) e os doadores do Central/Ferroviária não têm bloco próprio reconhecível
    assert 137569 not in found and 310790 not in found
