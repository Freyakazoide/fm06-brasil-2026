"""Escudos e uniformes 2026 para a pasta graphics do FM06.

Uniforme: camisa desenhada a partir de data/brasil/clubes/uniformes_2026.xlsx
(modelo, camisa, secundária, detalhes, calção). Escudo: SVG ou PNG convertido
para PNG com fundo transparente.

O formato do caminho que o FM06 usa para a imagem de cada clube ainda não está
confirmado: o exe registra os tipos (0x00A10D40: 'logo', 'icon', 'kits/home',
'kits/away', 'kits/third'...) e as chaves começam por "pictures/" (ex.:
"pictures/kits/default/<n>"), mas o caminho completo é montado em tempo de
execução. pacote_teste() grava o mesmo clube em vários formatos, cada um com
uma letra, para ver no jogo qual deles vale.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZES = {"logo": 180, "icon": 25}
KIT_SIZE = 100


def _rgb(hex_color: str | None, default: str = "#FFFFFF") -> tuple[int, int, int]:
    value = (hex_color or default).strip().lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def logo_png(source: bytes, size: int) -> Image.Image:
    """SVG ou imagem -> quadrado size x size, transparente, centralizado."""
    if b"<svg" in source[:2000]:
        import cairosvg

        source = cairosvg.svg2png(bytestring=source, output_width=size * 4)
    image = Image.open(io.BytesIO(source)).convert("RGBA")
    image.thumbnail((size, size), Image.LANCZOS)
    square = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    square.paste(image, ((size - image.width) // 2, (size - image.height) // 2), image)
    return square


def _shirt_mask(size: int) -> Image.Image:
    s = size / 100
    points = [(30, 8), (42, 12), (58, 12), (70, 8), (92, 22), (84, 40), (74, 36), (74, 92),
              (26, 92), (26, 36), (16, 40), (8, 22)]
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).polygon([(x * s, y * s) for x, y in points], fill=255)
    return mask


def kit_png(kit: dict, size: int = KIT_SIZE) -> Image.Image:
    """Camisa 2D: modelo + cores. kit: modelo, camisa, secundaria, detalhes."""
    main, second = _rgb(kit.get("camisa")), _rgb(kit.get("secundaria"), "#FFFFFF")
    detail = _rgb(kit.get("detalhes") or kit.get("secundaria"), "#FFFFFF")
    model = (kit.get("modelo") or "lisa").strip().lower()
    body = Image.new("RGBA", (size, size), main + (255,))
    d = ImageDraw.Draw(body)
    s = size / 100
    if model in ("listras verticais", "listras verticais finas"):
        width = 6 if model.endswith("finas") else 10
        for x in range(26 + width, 74, 2 * width):
            d.rectangle([x * s, 0, (x + width) * s, size], fill=second)
    elif model == "listras horizontais":
        for y in range(20, 92, 16):
            d.rectangle([0, y * s, size, (y + 8) * s], fill=second)
    elif model == "faixa horizontal":
        d.rectangle([0, 40 * s, size, 54 * s], fill=second)
    elif model == "faixa diagonal":
        d.polygon([(20 * s, 20 * s), (36 * s, 12 * s), (80 * s, 80 * s), (64 * s, 92 * s)], fill=second)
    elif model == "metade/metade":
        d.rectangle([50 * s, 0, size, size], fill=second)
    elif model == "mangas de outra cor":
        d.polygon([(0, 0), (30 * s, 0), (26 * s, 40 * s), (0, 40 * s)], fill=second)
        d.polygon([(70 * s, 0), (size, 0), (size, 40 * s), (74 * s, 40 * s)], fill=second)
    elif model == "xadrez":
        for x in range(0, 100, 12):
            for y in range(0, 100, 12):
                if (x // 12 + y // 12) % 2:
                    d.rectangle([x * s, y * s, (x + 12) * s, (y + 12) * s], fill=second)
    elif model == "degradê":
        for y in range(size):
            t = y / size
            d.line([(0, y), (size, y)], fill=tuple(int(main[i] * (1 - t) + second[i] * t) for i in range(3)))
    shirt = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shirt.paste(body, (0, 0), _shirt_mask(size))
    outline = ImageDraw.Draw(shirt)
    outline.arc([40 * s, 4 * s, 60 * s, 18 * s], 0, 180, fill=detail, width=max(1, int(3 * s)))  # gola
    return shirt


def label(image: Image.Image, text: str) -> Image.Image:
    """Letra grande no canto, para identificar a variante no jogo."""
    out = image.copy()
    d = ImageDraw.Draw(out)
    size = max(10, out.width // 3)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        font = ImageFont.load_default()
    d.rectangle([0, 0, size, size], fill=(255, 255, 0, 255))
    d.text((size // 6, -size // 10), text, fill=(0, 0, 0, 255), font=font)
    return out


# Formatos de caminho testados (letra: (como o arquivo entra, caminho))
#   "config": arquivo na pasta do pacote + registro no config.xml com o caminho em "to"
#   "arquivo": arquivo gravado direto nesse caminho dentro de graphics/
VARIANTS = {
    "A": ("config", "graphics/pictures/team/{uid}/{kind}"),
    "B": ("config", "graphics/pictures/club/{uid}/{kind}"),
    "C": ("config", "pictures/team/{uid}/{kind}"),
    "D": ("config", "pictures/club/{uid}/{kind}"),
    "E": ("config", "graphics/pictures/{uid}/{kind}"),
    "F": ("arquivo", "pictures/team/{uid}/{kind}"),
    "G": ("arquivo", "pictures/club/{uid}/{kind}"),
}


def pacote_teste(out: Path, clubs: list[dict]) -> list[str]:
    """clubs: uid, nome, escudo (bytes), kit (dict). Grava out/graphics/..."""
    pack = out / "graphics" / "brasil2026_teste"
    pack.mkdir(parents=True, exist_ok=True)
    records = []
    written = []
    for club in clubs:
        images = {kind: logo_png(club["escudo"], size) for kind, size in SIZES.items()}
        images["kits/home"] = kit_png(club["kit"])
        for letter, (how, pattern) in VARIANTS.items():
            for kind, image in images.items():
                path = pattern.format(uid=club["uid"], kind=kind)
                tagged = label(image, letter)
                if how == "config":
                    name = f"{club['uid']}_{letter}_{kind.replace('/', '_')}"
                    tagged.save(pack / f"{name}.png")
                    records.append(f'\t\t<record from="{name}" to="{path}"/>')
                else:
                    target = out / "graphics" / f"{path}.png"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    tagged.save(target)
                    written.append(str(target.relative_to(out)))
    config = ("<record>\n\t<boolean id=\"preload\" value=\"false\"/>\n\t<boolean id=\"auto_map\" value=\"false\"/>\n"
              "\t<list id=\"mappings\">\n" + "\n".join(records) + "\n\t</list>\n"
              "\t<list id=\"maps\">\n" + "\n".join(records) + "\n\t</list>\n</record>\n")
    (pack / "config.xml").write_text(config, encoding="utf-8")
    return written
