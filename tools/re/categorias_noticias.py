r"""Categoria de cada classe de notícia, lida do executável (sem o jogo aberto).

1ª vtable de cada classe (tools/imprensa/noticias_classes.json): slot 6 devolve o tipo (`mov ax, N`),
slot 10 a categoria da coluna "Tipo" da caixa (`mov al, N`; conferido: 1 Mensagens, 2 Transf.,
4 Imprensa, 7 Lesões, na ordem do filtro do jogo; as BASIC_* e algumas outras não têm categoria
fixa: deve vir de um campo). `slot11_proprio`: o slot 11 não é o padrão 0xCEF260 (devolve 0). NÃO
indica notícia com ação: TRANSFER_OFFER e CONTRACT_DECISION ficam no padrão (03/11). Grava
tools/imprensa/noticias_categorias.json.

    python tools\re\categorias_noticias.py
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "re"))

from fm06patch.exe_cave import off  # noqa: E402
import chamada_remota as cr  # noqa: E402

CATEGORIES = ["Competições", "Mensagens", "Transf.", "Contratos", "Imprensa", "Registos", "Disciplina", "Lesões"]
NO_ACTION = 0x00CEF260


def small_return(exe: bytes, f: int) -> int | None:
    at = off(f) if 0x00401000 <= f < 0x01000000 else None
    if at is None:
        return None
    code = exe[at:at + 6]
    if len(code) < 6:
        return None
    if code[:2] == b"\x66\xB8" and code[4] == 0xC3:                         # mov ax, N ; ret
        return struct.unpack_from("<H", code, 2)[0]
    if code[0] == 0xB0 and code[2] == 0xC3:                                 # mov al, N ; ret
        return code[1]
    return None


def main() -> None:
    exe = (Path(cr.json_game_dir()) / "fm.exe").read_bytes()
    classes = json.loads((ROOT / "tools" / "imprensa" / "noticias_classes.json").read_text(encoding="utf-8"))
    out = {}
    for vt_hex, name in sorted(classes.items(), key=lambda kv: kv[1]):
        vt = struct.unpack_from("<12I", exe, off(int(vt_hex, 16)))
        category = small_return(exe, vt[10])
        out[name] = {"vtable": vt_hex, "tipo": small_return(exe, vt[6]), "categoria": category,
                     "categoria_nome": CATEGORIES[category] if category is not None and category < len(CATEGORIES) else None,
                     "texto": f"0x{vt[5]:08X}", "slot11_proprio": vt[11] != NO_ACTION}
    target = ROOT / "tools" / "imprensa" / "noticias_categorias.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print(Counter(v["categoria_nome"] for v in out.values()))
    print(len(out), "classes")


if __name__ == "__main__":
    main()
