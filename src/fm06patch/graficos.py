"""Escudos e uniformes 2026 para a pasta data\\graphics do FM06.

Formato do FM05/06 (pesquisa com tutoriais e packs da época, confirmado pelas
chaves que o exe registra em 0x00A10D40: 'logo', 'icon', 'kits/home'...):
- arquivos em data/graphics/pictures/<qualquer subpasta>/ com um config.xml;
- config.xml: <list id="maps"> com <record from="<arquivo sem .png>" to="<chave>"/>;
- escudo: graphics/pictures/club/<UID>/logo (grande) e .../icon (pequeno);
- uniforme: graphics/pictures/team/<UID>/kits/home, away, third.
UID = o do jogo (CLUB+0x14; server_teams.clubs_by_uid), não o do repositório.
Uniforme desenhado a partir de data/brasil/clubes/uniformes_2026.xlsx.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZES = {"logo": (120, 120), "icon": (20, 18)}
KIT_SIZE = 80


def _rgb(hex_color: str | None, default: str = "#FFFFFF") -> tuple[int, int, int]:
    value = (hex_color or default).strip().lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def logo_png(source: bytes, size) -> Image.Image:
    """SVG ou imagem -> size (lado ou (largura, altura)), transparente, centralizado."""
    width, height = (size, size) if isinstance(size, int) else size
    if b"<svg" in source[:2000]:
        import cairosvg

        source = cairosvg.svg2png(bytestring=source, output_width=max(width, height) * 4)
    image = Image.open(io.BytesIO(source)).convert("RGBA")
    image.thumbnail((width, height), Image.LANCZOS)
    square = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    square.paste(image, ((width - image.width) // 2, (height - image.height) // 2), image)
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


def _config(records: list[tuple[str, str]]) -> str:
    lines = [f'\t\t<record from="{name}" to="{key}"/>' for name, key in records]
    return ('<record>\n\t<boolean id="preload" value="false"/>\n\t<boolean id="amap" value="false"/>\n'
            '\t<list id="maps">\n' + "\n".join(lines) + '\n\t</list>\n</record>\n')


def pacote(out: Path, clubs: list[dict], pack: str = "bra2026") -> int:
    """clubs: uid, slug, escudo (bytes ou None), kits {"home": dict, "away": dict}.
    Grava out/data/graphics/pictures/{logos,kits}/clubs/<pack>/. Devolve o nº de imagens."""
    logos = out / "data" / "graphics" / "pictures" / "logos" / "clubs" / pack
    kits = out / "data" / "graphics" / "pictures" / "kits" / "clubs" / pack
    logos.mkdir(parents=True, exist_ok=True)
    kits.mkdir(parents=True, exist_ok=True)
    logo_records, kit_records, count = [], [], 0
    for club in clubs:
        uid, slug = club["uid"], club["slug"]
        if club.get("escudo"):
            for kind, size in SIZES.items():
                name = slug if kind == "logo" else f"{slug}_icon"
                logo_png(club["escudo"], size).save(logos / f"{name}.png")
                logo_records.append((name, f"graphics/pictures/club/{uid}/{kind}"))
                count += 1
        for kind, kit in club.get("kits", {}).items():
            if kit and kit.get("camisa"):
                name = f"{slug}_{kind}"
                kit_png(kit).save(kits / f"{name}.png")
                kit_records.append((name, f"graphics/pictures/team/{uid}/kits/{kind}"))
                count += 1
    (logos / "config.xml").write_text(_config(logo_records), encoding="utf-8")
    (kits / "config.xml").write_text(_config(kit_records), encoding="utf-8")
    return count
