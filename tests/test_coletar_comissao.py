import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

from coletar_comissao import staff_rows  # noqa: E402

# trecho do artigo do Boca Juniors (modelo {{Fb cs header}}, sem "{|")
FB_CS = """
===Current coaching staff===
{{Fb cs header}}
|-
| Head coach || {{flagicon|ARG}} [[Rodolfo Arruabarrena]]
|-
|Assistant coach || {{flagicon|ARG}} [[Diego Markic]]
|-
|Goalkeeping coach || {{flagicon|ARG}} [[Cristián Muñoz (footballer, born 1977)|Cristián Muñoz]]
|-
|Kinesiologist || {{flagicon|ARG}} Pablo Varela
|-
{{Fb cs footer|u= 18 June 2026 |s=[https://example.org Cuerpo técnico]}}

==Institutional==
"""

TABLE = """
==Current staff==
{| class="wikitable"
! Position !! Name
|-
| Assistant coach || {{flagicon|BRA}} Fábio Moreno
|-
| Fitness coach || {{flagicon|BRA}} Anderson Nicolau
|}
"""


def test_fb_cs_header():
    rows, updated = staff_rows(FB_CS)
    assert [(r[0], r[2], r[3]) for r in rows] == [
        ("tecnico", "Rodolfo Arruabarrena", "ARG"), ("auxiliar", "Diego Markic", "ARG"),
        ("preparador", "Cristián Muñoz", "ARG"), ("medico", "Pablo Varela", "ARG")]
    assert updated == "18 June 2026"


def test_plain_table():
    rows, _ = staff_rows(TABLE)
    assert [(r[0], r[2]) for r in rows] == [("auxiliar", "Fábio Moreno"), ("preparador", "Anderson Nicolau")]
