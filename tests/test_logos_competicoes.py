import csv
import io
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fm06patch import estaduais, graficos  # noqa: E402

SHEET = ROOT / "data" / "brasil" / "logos_competicoes.csv"


def test_pack(tmp_path):
    image = io.BytesIO()
    Image.new("RGBA", (200, 100), (0, 140, 60, 255)).save(image, "PNG")
    assert graficos.pacote_competicoes(tmp_path, [(102423, "serie_a", image.getvalue())]) == 2
    pack = tmp_path / "data" / "graphics" / "pictures" / "logos" / "comps" / "bra2026"
    config = (pack / "config.xml").read_text(encoding="utf-8")
    assert '<record from="serie_a" to="graphics/pictures/comp/102423/logo"/>' in config
    assert '<record from="serie_a_icon" to="graphics/pictures/comp/102423/icon"/>' in config
    assert Image.open(pack / "serie_a.png").size == graficos.SIZES["logo"]


def test_sheet_uids():
    rows = list(csv.DictReader(SHEET.open(encoding="utf-8-sig")))
    uid = {row["chave"]: int(row["comp_uid"]) for row in rows}
    assert {k: v for k, v in uid.items() if k in estaduais.ID} == estaduais.ID
    assert (uid["serie_a"], uid["serie_c"], uid["libertadores"]) == (102423, 319191, 102415)
