"""Telas novas do mod nos XML de interface do jogo (ficha T1).

    python scripts\\aplicar_telas.py            (mostra o que muda)
    python scripts\\aplicar_telas.py --apply    (grava; guarda os originais na primeira vez)
    python scripts\\aplicar_telas.py --restore  (volta os originais)

A interface do FM06 é XML em <jogo>/data: sections.xml (árvore do menu lateral) e
screens/*.xml (cada código de seção ligado a uma classe de painel do executável). O script parte
sempre das cópias originais em workspace/baseline/telas e acrescenta os itens do mod.

Etapa 1: item "Centro de Desenvolvimento" (código tcdv) no menu do clube, ligado à lista de
jogadores da busca (person_search_panel, tipo 1), e a visão "Desenvolvimento" (CA, PA...) no menu
"Vêr" dessa lista.

Skin do mod: data/skins/brasil 2026, que herda da "Aurora 2006 // Flow (Left)" (prnt "aurora 2006
left - flow" -> "aurora 2006 left" -> "aurora 2006" -> padrão) e traz os painéis do mod, sem mexer
nas skins originais. Escolha "Brasil 2026" em Preferências > Interface. Os painéis do mod também
vão para o padrão do jogo (data/panels), para quem não usa skin.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "workspace" / "baseline" / "telas"
FILES = ("sections.xml", "screens/team.xml", "panels/person search list.xml")
SKIN = "brasil 2026"
SKIN_PARENT = "aurora 2006 left - flow"
SKIN_SOURCES = ("skins/aurora 2006/panels/person search list.xml", f"skins/{SKIN_PARENT}/config.xml")
SKIN_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE propertylist SYSTEM "http://www.sigames.com/dtds/propertylist.dtd">

	<!-- skin do mod fm06-brasil-2026: herda da Aurora 2006 Flow (Left) e traz os paineis do mod -->

<properties version="1.0">

	<string id="name" value="Brasil 2026 (Aurora Flow Left)"/>
	<string id="auth" value="fm06-brasil-2026"/>
	<string id="desc">Aurora 2006 // Flow (Left) com as telas do mod Brasil 2026.</string>
	<string id="vers" value="1.0"/>

	<flags id="prnt" value="{SKIN_PARENT}"/>

</properties>
"""

SECTION = "tcdv"
TITLE = "Centro de Desenvolvimento"
MENU_AFTER = '<record id="tcip" section="tcip" text="Information" ndrq="false" help_page="club_info"/>'
MENU_ITEM = f'\n                <record id="{SECTION}" section="{SECTION}" text="{TITLE}" ndrq="true"/>'
SCREEN_AFTER = '<widget class="team_information_panel" id="tcip" title="Information" late_loading="true" />'
SCREEN_ITEM = (f'\n\t<widget class="person_search_panel" id="{SECTION}" title="{TITLE}" '
               f'person_list_view_menu="play" type="1" late_loading="true"/>')


# visão "Desenvolvimento" no menu "Vêr" das listas de jogadores da busca (person search list.xml,
# widget "play"): colunas por código de propriedade (person list table.xml); PCAB/PPAB são o CA e
# o PA, que o jogo só mostrava numa visão de depuração
VIEW_BEFORE = '<record id="geni"> '
VIEW_ITEM = '''<record id="dsnv">
						<string id="name" value="Desenvolvimento"/>
						<record id="view">
							<flags id="Pnfo"/> <!-- status -->
							<flags id="Pnam"/> <!-- nome -->
							<flags id="Page"/> <!-- idade -->
							<flags id="Ppos"/> <!-- posicao -->
							<flags id="Pclb"/> <!-- clube -->
							<flags id="PCAB"/> <!-- CA -->
							<flags id="PPAB"/> <!-- PA -->
							<flags id="Pdva"/> <!-- valor -->
						</record>
					</record>

					'''


def game_data() -> Path:
    return Path(json.loads((ROOT / "config" / "local.json").read_text(encoding="utf-8"))["game_dir"]) / "data"


def insert_after(text: str, anchor: str, addition: str, name: str) -> str:
    if text.count(anchor) != 1:
        raise SystemExit(f"[ERRO] {name}: âncora não achada (ou repetida): {anchor[:60]}...")
    if addition.strip() in text:
        return text
    return text.replace(anchor, anchor + addition)


def insert_before(text: str, anchor: str, addition: str, name: str) -> str:
    if text.count(anchor) != 1:
        raise SystemExit(f"[ERRO] {name}: âncora não achada (ou repetida): {anchor[:60]}...")
    return text.replace(anchor, addition + anchor)


def build(originals: dict[str, str]) -> dict[str, str]:
    """Os XML do jogo com os itens do mod e os arquivos da skin do mod (caminhos a partir de data)."""
    return {
        f"skins/{SKIN}/{SKIN}.xml": SKIN_XML,
        f"skins/{SKIN}/config.xml": originals[f"skins/{SKIN_PARENT}/config.xml"],
        f"skins/{SKIN}/panels/person search list.xml": insert_before(
            originals["skins/aurora 2006/panels/person search list.xml"], VIEW_BEFORE, VIEW_ITEM,
            "aurora 2006/person search list.xml"),
        "panels/person search list.xml": insert_before(originals["panels/person search list.xml"], VIEW_BEFORE,
                                                       VIEW_ITEM, "person search list.xml"),
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
        shutil.rmtree(data / "skins" / SKIN, ignore_errors=True)
        print("[OK] XML originais de volta e skin do mod apagada")
        return
    for name in FILES + SKIN_SOURCES:                    # cópia dos originais, uma vez só
        target = BASELINE / name
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(data / name, target)
            print(f"[OK] original guardado em {target}")
    originals = {name: (BASELINE / name).read_text(encoding="utf-8") for name in FILES + SKIN_SOURCES}
    new = build(originals)
    for name, text in new.items():
        if not text.isascii():
            raise SystemExit(f"[ERRO] {name}: o jogo lê os XML como ASCII")
        added = len(text) - len(originals.get(name, ""))
        print(f"{name}: +{added} caracteres")
    if not args.apply:
        print("(simulação: rode com --apply para gravar)")
        return
    for name, text in new.items():
        (data / name).parent.mkdir(parents=True, exist_ok=True)
        (data / name).write_text(text, encoding="utf-8")
    print(f"[OK] gravado em {data}. Abra o jogo de novo para ler os XML.")


if __name__ == "__main__":
    sys.exit(main())
