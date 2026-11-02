"""Telas novas do mod nos XML de interface do jogo (ficha T1).

    python scripts\\aplicar_telas.py            (mostra o que muda)
    python scripts\\aplicar_telas.py --apply    (grava; guarda os originais na primeira vez)
    python scripts\\aplicar_telas.py --restore  (volta os originais)

A interface do FM06 é XML em <jogo>/data: sections.xml (árvore do menu lateral) e
screens/*.xml (cada código de seção ligado a uma classe de painel do executável). O script parte
sempre das cópias originais em workspace/baseline/telas e acrescenta os itens do mod.

Etapa 1, teste 1: item "Centro de Desenvolvimento" (código tcdv) no menu do clube, ligado à lista
de jogadores da busca (person_search_panel, tipo 1), que não depende do time aberto.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "workspace" / "baseline" / "telas"
FILES = ("sections.xml", "screens/team.xml")

SECTION = "tcdv"
TITLE = "Centro de Desenvolvimento"
MENU_AFTER = '<record id="tcip" section="tcip" text="Information" ndrq="false" help_page="club_info"/>'
MENU_ITEM = f'\n                <record id="{SECTION}" section="{SECTION}" text="{TITLE}" ndrq="true"/>'
SCREEN_AFTER = '<widget class="team_information_panel" id="tcip" title="Information" late_loading="true" />'
SCREEN_ITEM = (f'\n\t<widget class="person_search_panel" id="{SECTION}" title="{TITLE}" '
               f'person_list_view_menu="play" type="1" late_loading="true"/>')


def game_data() -> Path:
    return Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"]) / "data"


def insert_after(text: str, anchor: str, addition: str, name: str) -> str:
    if text.count(anchor) != 1:
        raise SystemExit(f"[ERRO] {name}: âncora não achada (ou repetida): {anchor[:60]}...")
    if addition.strip() in text:
        return text
    return text.replace(anchor, anchor + addition)


def build(originals: dict[str, str]) -> dict[str, str]:
    return {
        "sections.xml": insert_after(originals["sections.xml"], MENU_AFTER, MENU_ITEM, "sections.xml"),
        "screens/team.xml": insert_after(originals["screens/team.xml"], SCREEN_AFTER, SCREEN_ITEM,
                                         "screens/team.xml"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    data = game_data()
    if args.restore:
        for name in FILES:
            shutil.copy2(BASELINE / name, data / name)
        print("[OK] XML originais de volta")
        return
    for name in FILES:                                   # cópia dos originais, uma vez só
        target = BASELINE / name
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(data / name, target)
            print(f"[OK] original guardado em {target}")
    originals = {name: (BASELINE / name).read_text(encoding="utf-8") for name in FILES}
    new = build(originals)
    for name in FILES:
        added = len(new[name]) - len(originals[name])
        print(f"{name}: +{added} caracteres")
    if not args.apply:
        print("(simulação: rode com --apply para gravar)")
        return
    for name in FILES:
        (data / name).write_text(new[name], encoding="utf-8")
    print(f"[OK] gravado em {data}. Abra o jogo de novo para ler os XML.")


if __name__ == "__main__":
    sys.exit(main())
