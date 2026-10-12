"""Edita jogadores direto na memória do FM06 aberto.

Fluxo: New Game -> rodar este script -> conferir no jogo -> salvar o jogo.

    python scripts/live_player_editor.py data/live_edits/teste_saviola.json
    python scripts/live_player_editor.py data/live_edits/teste_saviola.json --apply
    python scripts/live_player_editor.py --restore workspace/live_edits/<arquivo>.json
    python scripts/live_player_editor.py --show 3100367

Sem --apply nada é gravado: o script só mostra o que mudaria.
Cada --apply salva os bytes originais em workspace/live_edits/ para --restore.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import sys
import time
from ctypes import wintypes
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from fm06patch.live_player import (  # noqa: E402
    OBJECT_SPAN,
    LivePlayer,
    signature_needle,
)
from live_player_memory import (  # noqa: E402
    find_process_id,
    iter_regions,
    kernel32,
    read_memory,
)


BACKUP_DIR = ROOT / "workspace" / "live_edits"

PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_QUERY_INFORMATION = 0x0400

kernel32.WriteProcessMemory.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
kernel32.WriteProcessMemory.restype = wintypes.BOOL


def open_for_write(pid: int):
    handle = kernel32.OpenProcess(
        PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION,
        False,
        pid,
    )
    if not handle:
        raise OSError(ctypes.get_last_error(), "OpenProcess falhou. Abra o PowerShell como Administrador.")
    return handle


def write_memory(handle, address: int, data: bytes) -> None:
    written = ctypes.c_size_t()
    buffer = ctypes.create_string_buffer(data, len(data))
    ok = kernel32.WriteProcessMemory(handle, ctypes.c_void_p(address), buffer, len(data), ctypes.byref(written))
    if not ok or written.value != len(data):
        raise OSError(ctypes.get_last_error(), f"WriteProcessMemory falhou em 0x{address:08X}")


def find_objects(handle, uids: list[int]) -> dict[int, dict[str, list[int]]]:
    """Endereço do UID de cada objeto (Player, PData, Playing) de cada jogador."""
    needles = {(uid, kind): signature_needle(kind, uid) for uid in uids for kind in OBJECT_SPAN}
    found: dict[int, dict[str, list[int]]] = {uid: {kind: [] for kind in OBJECT_SPAN} for uid in uids}
    chunk = 4 * 1024 * 1024
    keep = max(len(n) for n in needles.values()) - 1
    for base, size in iter_regions(handle):
        offset, tail = 0, b""
        while offset < size:
            data = read_memory(handle, base + offset, min(chunk, size - offset))
            if not data:
                break
            blob, blob_base = tail + data, base + offset - len(tail)
            for (uid, kind), needle in needles.items():
                pos = blob.find(needle)
                while pos >= 0:
                    address = blob_base + pos + 20  # endereço do UID
                    if address not in found[uid][kind]:
                        found[uid][kind].append(address)
                    pos = blob.find(needle, pos + 1)
            tail = blob[-keep:]
            offset += len(data)
    return found


def load_player(handle, uid: int, addresses: dict[str, int]) -> LivePlayer:
    blocks, uid_at = {}, {}
    for kind, (before, after) in OBJECT_SPAN.items():
        data = read_memory(handle, addresses[kind] - before, before + after)
        if not data or len(data) != before + after:
            raise RuntimeError(f"Não consegui ler {kind} do UID {uid}")
        blocks[kind], uid_at[kind] = data, before
    return LivePlayer(uid, blocks, uid_at)


def resolve(handle, uids: list[int]) -> dict[int, dict[str, int]]:
    print(f"Procurando {len(uids)} jogador(es) na memória...", flush=True)
    found = find_objects(handle, uids)
    result = {}
    for uid in uids:
        for kind, hits in found[uid].items():
            if len(hits) != 1:
                raise RuntimeError(
                    f"UID {uid}: {len(hits)} objetos {kind} encontrados (esperado 1). "
                    "O jogador está carregado nesta partida?"
                )
        result[uid] = {kind: hits[0] for kind, hits in found[uid].items()}
    return result


def show_summary(title: str, player: LivePlayer) -> None:
    s = player.summary()
    print(f"\n--- {title} (UID {s['uid']}) ---")
    print(f"CA {s['ca']}  PA {s['pa']}  altura {s['height']}  peso {s['weight']}  nascido {s['born']}")
    print(f"reputação casa/atual/mundial {s['home_reputation']}/{s['current_reputation']}/{s['world_reputation']}")
    print("personalidade:", s["personality"])
    print("atributos:", s["attributes"])
    print("preferred moves ativos:", s["preferred_moves"])


def cmd_edit(spec_path: Path, apply: bool) -> None:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    year_shift = int(spec.get("year_shift", 0))
    players = spec["players"]
    handle = open_for_write(find_process_id("fm.exe"))
    addresses = resolve(handle, [int(p["uid"]) for p in players])

    backup = {"created": time.strftime("%Y-%m-%d %H:%M:%S"), "spec": str(spec_path), "objects": []}
    for entry in players:
        uid = int(entry["uid"])
        player = load_player(handle, uid, addresses[uid])
        show_summary(f"ANTES {entry.get('name', '')}", player)
        writes = player.plan(entry, year_shift=year_shift)
        print(f"\n{len(writes)} alteração(ões):")
        for w in writes:
            print(f"  {w.obj:8} UID{w.rel:+5d}  {w.old.hex()} -> {w.new.hex()}  {w.label}")
        if not apply or not writes:
            continue
        for kind, (before, after) in OBJECT_SPAN.items():
            original = read_memory(handle, addresses[uid][kind] - before, before + after)
            backup["objects"].append({
                "uid": uid, "kind": kind,
                "address": addresses[uid][kind] - before,
                "data": original.hex(),
            })
        for w in writes:
            write_memory(handle, addresses[uid][w.obj] + w.rel, w.new)
        show_summary("DEPOIS (lido de volta da memória)", load_player(handle, uid, addresses[uid]))

    if apply and backup["objects"]:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        path = BACKUP_DIR / f"backup_{time.strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(backup, indent=1), encoding="utf-8")
        print(f"\nBackup dos bytes originais: {path}")
        print("Confira no jogo. Para desfazer nesta mesma partida: --restore", path)
    elif not apply:
        print("\nNada foi gravado. Rode de novo com --apply para aplicar.")


def cmd_restore(path: Path) -> None:
    backup = json.loads(path.read_text(encoding="utf-8"))
    handle = open_for_write(find_process_id("fm.exe"))
    for item in backup["objects"]:
        data = bytes.fromhex(item["data"])
        before = OBJECT_SPAN[item["kind"]][0]
        current = read_memory(handle, item["address"], len(data))
        if not current or current[before:before + 4] != data[before:before + 4]:
            raise RuntimeError(
                f"UID {item['uid']} não está mais em 0x{item['address']:08X}. "
                "O backup só vale para a mesma partida aberta."
            )
        write_memory(handle, item["address"], data)
        print(f"restaurado {item['kind']:8} UID {item['uid']}")


def cmd_show(uid: int) -> None:
    handle = open_for_write(find_process_id("fm.exe"))
    show_summary("ATUAL", load_player(handle, uid, resolve(handle, [uid])[uid]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spec", nargs="?", type=Path, help="JSON com os jogadores a editar")
    parser.add_argument("--apply", action="store_true", help="grava de verdade")
    parser.add_argument("--restore", type=Path, help="desfaz usando um backup")
    parser.add_argument("--show", type=int, metavar="UID", help="só mostra os dados atuais")
    args = parser.parse_args()
    if args.restore:
        cmd_restore(args.restore)
    elif args.show:
        cmd_show(args.show)
    elif args.spec:
        cmd_edit(args.spec, args.apply)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
