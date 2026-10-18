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

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

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


# Camisa no espaço 0..100 (frente; esquerda da imagem = lado direito do jogador).
BODY = [(38, 9), (31, 11), (24, 14), (26, 24), (28, 34), (28.5, 60), (27.5, 91), (39, 92.6), (50, 93.2),
        (61, 92.6), (72.5, 91), (71.5, 60), (72, 34), (74, 24), (76, 14), (69, 11), (62, 9),
        (56, 13.6), (50, 15.6), (44, 13.6)]
SLEEVE = [(24, 14), (16, 17.5), (9.5, 24), (4, 37), (17, 45), (23, 40), (28, 34), (26, 24)]
CUFF = [(4, 37), (17, 45), (18.6, 43.4), (5.3, 34)]
NECK_IN = [(38, 9), (44, 13.6), (50, 15.6), (56, 13.6), (62, 9), (56, 7.6), (50, 7.1), (44, 7.6)]
COLLAR = NECK_IN[:5]
BACK_COLLAR = [(38, 9), (44, 7.6), (50, 7.1), (56, 7.6), (62, 9)]
SEAM = [(24, 14), (26, 24), (28, 34)]
FONTS = ("/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf", "arialbd.ttf", "DejaVuSans-Bold.ttf")


def _mirror(points):
    return [(100 - x, y) for x, y in points]


def _scaled(points, s):
    return [(x * s, y * s) for x, y in points]


def _mask(n, points, s) -> Image.Image:
    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).polygon(_scaled(points, s), fill=255)
    return mask


def _pattern(model, main, second, n, s) -> Image.Image:
    image = Image.new("RGB", (n, n), main)
    d = ImageDraw.Draw(image)
    if model in ("listras verticais", "listras verticais finas"):
        width = 4.6 if model.endswith("finas") else 7.6
        x = 50 + width / 2                      # listra da cor principal no centro
        while x < 100:
            d.rectangle([x * s, 0, (x + width) * s, n], fill=second)
            d.rectangle([(100 - x - width) * s, 0, (100 - x) * s, n], fill=second)
            x += 2 * width
    elif model == "listras horizontais":
        for y in range(11, 100, 15):
            d.rectangle([0, y * s, n, (y + 7.5) * s], fill=second)
    elif model == "faixa horizontal":
        d.rectangle([0, 38 * s, n, 50 * s], fill=second)
    elif model == "faixa diagonal":
        d.polygon(_scaled([(24, 12), (36, 12), (78, 92), (66, 92)], s), fill=second)
    elif model == "metade/metade":
        d.rectangle([50 * s, 0, n, n], fill=second)
    elif model == "xadrez":
        for i in range(12):
            for j in range(12):
                if (i + j) % 2:
                    d.rectangle([i * 9 * s, j * 9 * s, (i + 1) * 9 * s, (j + 1) * 9 * s], fill=second)
    elif model == "degradê":
        t = np.linspace(0, 1, n)[:, None, None]
        rows = np.array(main)[None, None] * (1 - t) + np.array(second)[None, None] * t
        image = Image.fromarray(np.broadcast_to(rows, (n, n, 3)).astype("uint8"))
    return image


def _soft_lines(n, s, lines, width, radius) -> np.ndarray:
    layer = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(layer)
    for points, value in lines:
        d.line(_scaled(points, s), fill=value, width=max(1, int(width * s)), joint="curve")
    return np.asarray(layer.filter(ImageFilter.GaussianBlur(radius * s)), dtype=float) / 255


def _shading(n, s, body, sleeves) -> np.ndarray:
    """Luz por pixel (1 = cor original): corpo cilíndrico, luz do alto à esquerda,
    brilho no peito, mangas escuras embaixo, dobras e sombra nas bordas."""
    yy, xx = np.mgrid[0:n, 0:n] / s
    u = np.clip((xx - 50) / 24, -1.3, 1.3)
    light = 1 - 0.30 * u ** 2 - 0.07 * u - 0.05 * (yy - 40) / 50
    light += 0.10 * np.exp(-(((xx - 41) / 9) ** 2 + ((yy - 30) / 12) ** 2))
    sleeve = np.asarray(sleeves, float) / 255
    down = np.clip((yy - 14) / 30, 0, 1)
    light = light * (1 - sleeve) + sleeve * (1.02 - 0.28 * down - 0.08 * np.abs(xx - 50) / 50)
    folds = [([(28, 35), (35, 46), (41, 53)], 255), ([(36, 78), (38, 92)], 200), ([(48, 70), (50, 92)], 120),
             (SEAM, 230), ([(14, 27), (17, 38)], 150)]
    folds += [(_mirror(points), value) for points, value in folds if points[0][0] != 48]
    ridges = [([(31, 37), (38, 48), (44, 55)], 255), ([(40, 80), (41.5, 92)], 160)]
    ridges += [(_mirror(points), value) for points, value in ridges]
    light -= 0.22 * _soft_lines(n, s, folds + [([(40, 15), (50, 19), (60, 15)], 200)], 2.4, 1.8)
    light += 0.10 * _soft_lines(n, s, ridges, 2.0, 1.6)
    shirt = Image.fromarray(np.maximum(np.asarray(body), np.asarray(sleeves)))
    edge = np.asarray(shirt.filter(ImageFilter.GaussianBlur(2.2 * s)), float) / 255
    return light * (0.70 + 0.30 * np.clip(edge * 2 - 0.6, 0, 1) ** 0.6)


def _lit(image, light) -> np.ndarray:
    a = np.asarray(image, float)
    l = light[..., None]
    return np.clip(np.where(l <= 1, a * l, a + (255 - a) * (l - 1)), 0, 255)


def _contrast(color) -> tuple[int, int, int]:
    return (255, 255, 255) if 0.3 * color[0] + 0.59 * color[1] + 0.11 * color[2] < 150 else (20, 20, 20)


def _font(size):
    for name in FONTS:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def kit_png(kit: dict, size: int = KIT_SIZE, style: str = "3d", crest: Image.Image | None = None,
            sponsor: str | None = None, supplier: str | None = None) -> Image.Image:
    """Camisa com volume. kit: modelo, camisa, secundaria, detalhes (gola e punhos).
    style "3d" desenha em 4x e reduz (suave); "pixel" desenha em 40x40 com 4 tons e amplia.
    crest: escudo no peito; sponsor: patrocínio master; supplier: fornecedor (Adidas = 3 listras)."""
    main, second = _rgb(kit.get("camisa")), _rgb(kit.get("secundaria"), "#FFFFFF")
    detail = _rgb(kit.get("detalhes") or kit.get("secundaria"), "#FFFFFF")
    model = (kit.get("modelo") or "lisa").strip().lower()
    pixel = style == "pixel"
    n = 40 if pixel else size * 4
    s = n / 100
    body = _mask(n, BODY, s)
    sleeves = Image.new("L", (n, n), 0)
    for side in (SLEEVE, _mirror(SLEEVE)):
        sleeves.paste(255, (0, 0), _mask(n, side, s))
    sleeves = Image.fromarray(np.minimum(np.asarray(sleeves), 255 - np.asarray(body)))
    cloth = _pattern(model, main, second, n, s)
    if model == "mangas de outra cor":
        cloth.paste(second, (0, 0), sleeves)
    d = ImageDraw.Draw(cloth)
    for cuff in (CUFF, _mirror(CUFF)):
        d.polygon(_scaled(cuff, s), fill=detail)
    d.line(_scaled(COLLAR, s), fill=detail, width=max(1, round(2.6 * s)), joint="curve")
    d.line(_scaled(BACK_COLLAR, s), fill=detail, width=max(1, round(1.4 * s)), joint="curve")
    if (supplier or "").strip().lower() == "adidas":
        for side in (1, -1):
            for i in range(3):
                stripe = [(50 - side * 11.5, 9.4 + i * 1.9), (50 - side * 25.5, 14.4 + i * 1.9),
                          (50 - side * 41, 33.5 + i * 1.6)]
                d.line([(x * s, y * s) for x, y in stripe], fill=detail, width=max(1, round(1.0 * s)))
    light = _shading(n, s, body, sleeves)
    inside = np.asarray(_mask(n, NECK_IN, s)) > 128
    light[inside] = (0.55 + 0.25 * np.mgrid[0:n, 0:n][0] / n)[inside]   # interior da gola, na sombra
    if pixel:
        tones = np.array([0.62, 0.80, 0.95, 1.10])
        light = tones[np.abs(light[..., None] - tones).argmin(-1)]
    pixels = _lit(cloth, light).astype("uint8")
    shirt = Image.fromarray(pixels).convert("RGBA")
    shirt.putalpha(Image.fromarray(np.maximum(np.asarray(body), np.asarray(sleeves))))
    d = ImageDraw.Draw(shirt)
    if crest is not None:
        badge = crest.copy()
        badge.thumbnail((int(11 * s), int(11 * s)), Image.LANCZOS)
        shirt.alpha_composite(badge, (int(61 * s - badge.width / 2), int(25 * s - badge.height / 2)))
    if supplier and supplier.strip().lower() != "adidas" and not pixel:
        d.ellipse(_scaled([(36.5, 23.5), (41, 27)], s), fill=_contrast(main) + (255,))
    if sponsor and not pixel:
        text = sponsor.strip().upper()
        behind = pixels[int(44 * s):int(50 * s), int(36 * s):int(64 * s)].reshape(-1, 3).mean(0)
        ink = _contrast(tuple(behind))
        font = _font(int(7.5 * s))
        width = d.textlength(text, font=font)
        if width > 38 * s:
            font = _font(int(7.5 * s * 38 * s / width))
        d.text((50 * s, 47 * s), text, font=font, fill=ink + (255,), anchor="mm",
               stroke_width=max(1, round(0.5 * s)), stroke_fill=tuple(255 - c for c in ink) + (110,))
    outline = (40, 40, 40, 235) if sum(main) > 600 else tuple(int(c * 0.30) for c in main) + (235,)
    for part in (BODY, SLEEVE, _mirror(SLEEVE)):
        d.line(_scaled(part + part[:1], s), fill=outline, width=1 if pixel else round(1.1 * s), joint="curve")
    if not pixel:
        for seam in (SEAM, _mirror(SEAM)):
            d.line(_scaled(seam, s), fill=(0, 0, 0, 70), width=round(0.6 * s))
    shirt = shirt.resize((size, size), Image.NEAREST if pixel else Image.LANCZOS)
    shadow = Image.new("RGBA", shirt.size, (0, 0, 0, 0))
    shadow.putalpha(shirt.getchannel("A").point(lambda v: int(v * 0.35)).filter(ImageFilter.GaussianBlur(1.4)))
    shadow = shadow.transform(shirt.size, Image.AFFINE, (1, 0, -1, 0, 1, -1.5))
    out = Image.new("RGBA", shirt.size, (0, 0, 0, 0))
    out.alpha_composite(shadow)
    out.alpha_composite(shirt)
    return out


def _config(records: list[tuple[str, str]]) -> str:
    lines = [f'\t\t<record from="{name}" to="{key}"/>' for name, key in records]
    return ('<record>\n\t<boolean id="preload" value="false"/>\n\t<boolean id="amap" value="false"/>\n'
            '\t<list id="maps">\n' + "\n".join(lines) + '\n\t</list>\n</record>\n')


def pacote(out: Path, clubs: list[dict], pack: str = "bra2026") -> int:
    """clubs: uid, slug, escudo (bytes ou None), logo_size (opcional) e kits
    {"home": dict, "away": dict}; cada kit pode ter estilo, patrocinador e fornecedor.
    Grava out/data/graphics/pictures/{logos,kits}/clubs/<pack>/. Devolve o nº de imagens."""
    logos = out / "data" / "graphics" / "pictures" / "logos" / "clubs" / pack
    kits = out / "data" / "graphics" / "pictures" / "kits" / "clubs" / pack
    logos.mkdir(parents=True, exist_ok=True)
    kits.mkdir(parents=True, exist_ok=True)
    logo_records, kit_records, count = [], [], 0
    for club in clubs:
        uid, slug = club["uid"], club["slug"]
        crest = logo_png(club["escudo"], 120) if club.get("escudo") else None
        if crest is not None:
            sizes = dict(SIZES, logo=club.get("logo_size", SIZES["logo"]))
            for kind, size in sizes.items():
                name = slug if kind == "logo" else f"{slug}_{kind}"
                logo_png(club["escudo"], size).save(logos / f"{name}.png")
                logo_records.append((name, f"graphics/pictures/club/{uid}/{kind}"))
                count += 1
        for kind, kit in club.get("kits", {}).items():
            if kit and kit.get("camisa"):
                name = f"{slug}_{kind}"
                kit_png(kit, style=kit.get("estilo", "3d"), crest=crest, sponsor=kit.get("patrocinador"),
                        supplier=kit.get("fornecedor")).save(kits / f"{name}.png")
                kit_records.append((name, f"graphics/pictures/team/{uid}/kits/{kind}"))
                count += 1
    (logos / "config.xml").write_text(_config(logo_records), encoding="utf-8")
    (kits / "config.xml").write_text(_config(kit_records), encoding="utf-8")
    return count
