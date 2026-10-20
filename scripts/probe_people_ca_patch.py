from pathlib import Path
import hashlib
import struct
import shutil


GAME_DB = Path(r"C:\Games\Football Manager 2006\data\db")
PROJECT = Path(r"C:\Users\Pichau\Desktop\fm06-brasil-2026")

SOURCE = GAME_DB / "people_db.dat"

OUT_DIR = PROJECT / "workspace" / "experiments"
BACKUP_DIR = PROJECT / "workspace" / "backups"

OUT_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

PATCHED = OUT_DIR / "people_db_saviola_ca111.dat"
BACKUP = BACKUP_DIR / "people_db_before_ca_test.dat"


PLAYER_UID = 3100367
UID_OFFSET = 0x03B71E4E

CA_OFFSET = UID_OFFSET + 15
PA_OFFSET = UID_OFFSET + 17

EXPECTED_CA = 160
EXPECTED_PA = 180

NEW_CA = 111


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


data = bytearray(SOURCE.read_bytes())

uid = struct.unpack_from("<I", data, UID_OFFSET)[0]
ca = struct.unpack_from("<H", data, CA_OFFSET)[0]
pa = struct.unpack_from("<H", data, PA_OFFSET)[0]

print("=" * 80)
print("FM06 DATABASE PATCH PROBE")
print("=" * 80)

print(f"UID encontrado : {uid}")
print(f"CA original    : {ca}")
print(f"PA original    : {pa}")

if uid != PLAYER_UID:
    raise RuntimeError(
        f"UID inesperado em 0x{UID_OFFSET:08X}: "
        f"esperado {PLAYER_UID}, encontrado {uid}"
    )

if ca != EXPECTED_CA:
    raise RuntimeError(
        f"CA inesperado: esperado {EXPECTED_CA}, encontrado {ca}"
    )

if pa != EXPECTED_PA:
    raise RuntimeError(
        f"PA inesperado: esperado {EXPECTED_PA}, encontrado {pa}"
    )

if not BACKUP.exists():
    shutil.copy2(SOURCE, BACKUP)
    print(f"\nBackup criado:\n{BACKUP}")
else:
    print(f"\nBackup já existe:\n{BACKUP}")

before_hash = sha256(data)

struct.pack_into(
    "<H",
    data,
    CA_OFFSET,
    NEW_CA,
)

patched_ca = struct.unpack_from(
    "<H",
    data,
    CA_OFFSET,
)[0]

PATCHED.write_bytes(data)

after_hash = sha256(data)

print()
print(f"CA novo        : {patched_ca}")
print(f"Offset CA      : 0x{CA_OFFSET:08X}")

print()
print(f"SHA original   : {before_hash}")
print(f"SHA modificado : {after_hash}")

print()
print(f"Arquivo criado:\n{PATCHED}")

print()
print("Bytes alterados:")
print(
    f"0x{CA_OFFSET:08X}: "
    f"{EXPECTED_CA:04X} -> {NEW_CA:04X}"
)

print()
print("NÃO houve alteração automática no arquivo do jogo.")