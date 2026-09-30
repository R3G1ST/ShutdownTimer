"""Генератор иконки приложения resources/icon.ico из Pillow-примитивов."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "resources"
OUT_PATH = OUT_DIR / "icon.ico"
SIZES = [16, 24, 32, 48, 64, 128, 256]

SIZE = 256
SCALE = 4
BIG = SIZE * SCALE
RADIUS = 52 * SCALE

TOP_COLOR = (18, 20, 28)
BOTTOM_COLOR = (27, 36, 54)
ACCENT = (79, 140, 255)

SYMBOL_R = 62 * SCALE
SYMBOL_W = 14 * SCALE
GAP_DEG = 26


def make_gradient() -> Image.Image:
    strip = Image.new("RGB", (1, BIG))
    pix = strip.load()
    for y in range(BIG):
        t = y / (BIG - 1)
        pix[0, y] = (
            round(TOP_COLOR[0] + (BOTTOM_COLOR[0] - TOP_COLOR[0]) * t),
            round(TOP_COLOR[1] + (BOTTOM_COLOR[1] - TOP_COLOR[1]) * t),
            round(TOP_COLOR[2] + (BOTTOM_COLOR[2] - TOP_COLOR[2]) * t),
        )
    return strip.resize((BIG, BIG), Image.Resampling.BILINEAR)


def make_mask() -> Image.Image:
    mask = Image.new("L", (BIG, BIG), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, BIG - 1, BIG - 1], radius=RADIUS, fill=255)
    return mask


def make_glow() -> Image.Image:
    glow = Image.new("RGBA", (BIG, BIG), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    cx = BIG // 2
    cy = int(BIG * 0.34)
    r = int(BIG * 0.40)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*ACCENT, 78))
    cy2 = int(BIG * 0.78)
    r2 = int(BIG * 0.34)
    draw.ellipse([cx - r2, cy2 - r2, cx + r2, cy2 + r2], fill=(*ACCENT, 34))
    return glow.filter(ImageFilter.GaussianBlur(BIG * 0.055))


def make_border() -> Image.Image:
    layer = Image.new("RGBA", (BIG, BIG), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    w = max(2, 2 * SCALE)
    half = w / 2
    draw.rounded_rectangle(
        [half, half, BIG - 1 - half, BIG - 1 - half],
        radius=RADIUS - half,
        outline=(*ACCENT, 140),
        width=w,
    )
    return layer


def make_symbol() -> Image.Image:
    layer = Image.new("RGBA", (BIG, BIG), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    cx = BIG / 2
    cy = BIG / 2
    start = -90 + GAP_DEG
    end = -90 - GAP_DEG + 360
    steps = 320
    points = []
    for i in range(steps + 1):
        angle = math.radians(start + (end - start) * i / steps)
        points.append((cx + SYMBOL_R * math.cos(angle), cy + SYMBOL_R * math.sin(angle)))
    draw.line(points, fill=(255, 255, 255, 255), width=SYMBOL_W, joint="curve")
    for point in (points[0], points[-1]):
        draw.ellipse(
            [point[0] - SYMBOL_W / 2, point[1] - SYMBOL_W / 2, point[0] + SYMBOL_W / 2, point[1] + SYMBOL_W / 2],
            fill=(255, 255, 255, 255),
        )
    top = cy - SYMBOL_R - SYMBOL_W * 0.4
    draw.line([(cx, top), (cx, cy)], fill=(255, 255, 255, 255), width=SYMBOL_W)
    for point in ((cx, top), (cx, cy)):
        draw.ellipse(
            [point[0] - SYMBOL_W / 2, point[1] - SYMBOL_W / 2, point[0] + SYMBOL_W / 2, point[1] + SYMBOL_W / 2],
            fill=(255, 255, 255, 255),
        )
    return layer


def build_icon() -> Image.Image:
    mask = make_mask()
    icon = Image.new("RGBA", (BIG, BIG), (0, 0, 0, 0))
    icon.paste(make_gradient(), (0, 0), mask)
    icon = Image.alpha_composite(icon, make_glow())
    icon = Image.alpha_composite(icon, make_border())
    icon = Image.alpha_composite(icon, make_symbol())
    alpha = icon.getchannel("A")
    alpha = Image.composite(alpha, Image.new("L", (BIG, BIG), 0), mask)
    icon.putalpha(alpha)
    return icon.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    image = build_icon()
    image.save(OUT_PATH, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"saved {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
