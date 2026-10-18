"""Gera os escudos e uniformes 2026 de todos os clubes para data\\graphics do FM06.

Uso (na pasta do repositório):
    python scripts\\gerar_graficos.py            (gera com os escudos que já estão baixados)
    python scripts\\gerar_graficos.py --baixar   (baixa antes os escudos que faltam)

Entradas:
- data/brasil/clubes/identidade_fm06.csv: UID do jogo de cada clube de 2026
  (gravado pelo aplicar_brasil_2026.py);
- data/brasil/clubes/uniformes_2026.xlsx: cores, modelo, fornecedor, patrocínio;
- data/brasil/clubes/clubes_master.xlsx e clubes_faltando.xlsx: escudo_arquivo e escudo_url;
- data/brasil/clubes/escudos/<escudo_arquivo>.png: escudos baixados (PNG, JPG ou SVG).
Saída: data/brasil/graficos_2026/data/... (copiar para a pasta do jogo):
- graphics/pictures/{logos,kits}/clubs/bra2026: escudos e uniformes;
- db/lnc/all/brasil_2026_clubes.lnc: nome de 2026 do clube do jogo que tem outro
  nome no FM06 (substitutos e renomeados), aplicado no New Game;
e data/brasil/graficos_2026/relatorio.csv (o que ficou sem escudo).
"""

from __future__ import annotations

import argparse
import csv
import io
import shutil
import sys
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import cores, graficos, identidade  # noqa: E402
from fm06patch.estaduais_clubes import normalize, same_club  # noqa: E402

CLUBES = ROOT / "data" / "brasil" / "clubes"
ESCUDOS = CLUBES / "escudos"
OUT = ROOT / "data" / "brasil" / "graficos_2026"
KIT_SIZE = 150
FORMATS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")


def _crest_files() -> dict[str, tuple[str, str]]:
    """clube -> (escudo_arquivo sem extensão, escudo_url)."""
    files = {}
    for sheet in ("clubes_master.xlsx", "clubes_faltando.xlsx"):
        for row in cores.sheet(CLUBES / sheet):
            if row.get("escudo_arquivo"):
                files[row["clube"]] = (Path(row["escudo_arquivo"]).stem, row.get("escudo_url") or "")
    return files


def _names() -> dict[str, tuple[str, str]]:
    """clube -> (nome curto, nome completo) de 2026."""
    names = {}
    for sheet in ("clubes_master.xlsx", "clubes_faltando.xlsx"):
        for row in cores.sheet(CLUBES / sheet):
            short = row.get("nome_curto_2026") or row["clube"]
            names[row["clube"]] = (short, row.get("nome_completo_2026") or short)
    return names


def lnc_clubs(renames: list[tuple[int, str, str]], colours: list[tuple[int, list]]) -> str:
    """CLUB_NAME_CHANGE etc. (unid, nome, idioma) e COLOUR_CHANGE (unid, índice, cor 1 =
    frente, cor 2 = fundo; executor em 0x00AAA1B0) com o UID do jogo."""
    lines = ["# FM06 Brasil 2026: nomes e cores de 2026 dos clubes", "# Comando\tID\tNome\tIdioma"]
    for uid, short, full in renames:
        lines += [f'"CLUB_NAME_CHANGE"\t{uid}\t"{short}"\t""',
                  f'"CLUB_SHORT_NAME_CHANGE"\t{uid}\t"{short}"\t""',
                  f'"CLUB_LONG_NAME_CHANGE"\t{uid}\t"{full}"\t""']
    lines += ["", "# Comando\tID\tÍndice\tR1 G1 B1 (frente)\tR2 G2 B2 (fundo)"]
    for uid, sets in colours:
        for index, front, back, _ in sets:
            lines.append(f'"COLOUR_CHANGE"\t{uid}\t{index}\t' + "\t".join(map(str, front + back)))
    return "\r\n".join(lines) + "\r\n"


def _crest_path(stem: str) -> Path | None:
    for ext in FORMATS:
        if (ESCUDOS / f"{stem}{ext}").exists():
            return ESCUDOS / f"{stem}{ext}"
    return None


def baixar(files: dict[str, tuple[str, str]]) -> None:
    ESCUDOS.mkdir(parents=True, exist_ok=True)
    for club, (stem, url) in sorted(files.items()):
        if not url or _crest_path(stem):
            continue
        ext = Path(url.split("?")[0]).suffix.lower()
        ext = ext if ext in FORMATS else ".png"
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(request, timeout=30).read()
        except Exception as error:                      # noqa: BLE001
            print(f"[FALHOU] {club}: {url} ({error})")
            continue
        if ext != ".svg":
            try:
                Image.open(io.BytesIO(data)).verify()
            except Exception:                           # noqa: BLE001
                print(f"[FALHOU] {club}: o link não é uma imagem ({url})")
                continue
        (ESCUDOS / f"{stem}{ext}").write_bytes(data)
        print(f"[OK] {club}")


def _kit(row: dict, n: int) -> dict | None:
    if not row.get(f"uni{n}_camisa"):
        return None
    model = row.get(f"uni{n}_modelo") or "lisa"
    return {"modelo": "lisa" if model.startswith("outro") else model, "camisa": row[f"uni{n}_camisa"],
            "secundaria": row[f"uni{n}_secundaria"], "detalhes": row[f"uni{n}_detalhes"],
            "patrocinador": row.get("patrocinador_master"), "fornecedor": row.get("fornecedor_2026")}


def _slug(uid: int, name: str) -> str:
    return f"{uid}_{normalize(name).replace(' ', '_')}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baixar", action="store_true", help="baixa os escudos que faltam")
    args = parser.parse_args()
    identities = identidade.read_report(CLUBES / "identidade_fm06.csv")
    kit_rows = cores.kit_rows(identities, cores.sheet(CLUBES / "uniformes_2026.xlsx"))
    files = _crest_files()
    names = _names()
    renames, colours = [], []
    if args.baixar:
        baixar(files)

    clubs, report = [], []
    for ident in identities:
        uid = int(ident["uid_jogo"])
        row = kit_rows.get(uid)
        name = row["clube"] if row else ident["clube_2026"]
        stem = (files.get(name) or files.get(ident["clube_2026"]) or ("", ""))[0]
        path = _crest_path(stem) if stem else None
        if path:
            try:
                graficos.logo_png(path.read_bytes(), 20)
            except Exception as error:                  # noqa: BLE001
                print(f"[AVISO] escudo de {ident['clube_2026']} não abriu ({path.name}: {error})")
                path = None
        kits = {kind: _kit(row, n) for n, kind in ((1, "home"), (2, "away"), (3, "third"))} if row else {}
        clubs.append({"uid": uid, "slug": _slug(uid, ident["clube_2026"]), "kit_size": KIT_SIZE,
                      "escudo": path.read_bytes() if path else None, "kits": kits})
        short, full = names.get(name) or names.get(ident["clube_2026"]) or (ident["clube_2026"],) * 2
        if ident["tipo"] != "vaga extra" and normalize(short) != normalize(ident["fm06_nome"]):
            renames.append((uid, short, full))
        if row and ident["tipo"] == "substituto":
            colours.append((uid, cores.club_colours(row)))
        report.append([uid, ident["clube_2026"], ident["uf"], ident["fm06_nome"],
                       "sim" if path else "NÃO", "sim" if row else "NÃO",
                       ", ".join(k for k, v in kits.items() if v)])
    shutil.rmtree(OUT / "data", ignore_errors=True)
    count = graficos.pacote(OUT, clubs)
    lnc = OUT / "data" / "db" / "lnc" / "all" / "brasil_2026_clubes.lnc"
    lnc.parent.mkdir(parents=True, exist_ok=True)
    lnc.write_bytes(lnc_clubs(renames, colours).encode("utf-16"))
    with (OUT / "relatorio.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["uid_jogo", "clube_2026", "uf", "fm06_nome", "escudo", "uniforme", "kits"])
        writer.writerows(report)
    without = [r[1] for r in report if r[4] != "sim"]
    print(f"[OK] {count} imagens de {len(clubs)} clubes em {OUT / 'data'}")
    print(f"[OK] {len(renames)} clubes com o nome de 2026 e {len(colours)} substitutos com as cores de 2026 em {lnc}")
    print(f"[OK] relatório em {OUT / 'relatorio.csv'}")
    if without:
        print(f"[AVISO] {len(without)} clubes sem escudo (rode com --baixar): " + ", ".join(without))


if __name__ == "__main__":
    main()
