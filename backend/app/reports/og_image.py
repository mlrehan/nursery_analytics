"""Generate a 1200×630 branded social preview image (PNG) for share cards (Pillow).

Shows brand + dashboard name + a decorative chart motif. No real data — safe to be
public. Uses DejaVu fonts (installed via fonts-dejavu-core in the image)."""
from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG = (11, 16, 32)
PANEL = (18, 26, 51)
INDIGO = (79, 70, 229)
WHITE = (255, 255, 255)
MUTE = (159, 176, 204)
DIM = (107, 122, 163)
BLUE = (96, 165, 250)
LINE = (38, 49, 78)
BARS = [(59, 130, 246), (16, 185, 129), (124, 92, 246), (245, 158, 11), (34, 211, 238), (251, 146, 60)]

_FONTS = {
    "bold": ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "reg": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}


def _font(kind: str, size: int):
    for path in _FONTS[kind]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _trunc(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def build_og_image(brand_name: str, tagline: str, module_name: str) -> bytes:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # right accent panel + soft accent circles
    d.rectangle((820, 0, W, H), fill=PANEL)
    d.ellipse((980, 360, 1460, 840), fill=(27, 35, 80))
    d.ellipse((-120, -160, 320, 280), fill=(21, 25, 58))

    # brand mark tile + letter
    d.rounded_rectangle((80, 60, 140, 120), radius=14, fill=INDIGO)
    d.text((110, 90), (brand_name.strip()[:1] or "N").upper(), font=_font("bold", 34),
           fill=WHITE, anchor="mm")
    d.text((160, 66), _trunc(brand_name, 26), font=_font("bold", 38), fill=WHITE)
    d.text((162, 112), _trunc(tagline.upper(), 42), font=_font("reg", 17), fill=MUTE)

    d.line((80, 162, 1120, 162), fill=LINE, width=2)

    # eyebrow + big module title
    d.text((80, 192), "DASHBOARD  REPORT", font=_font("bold", 18), fill=BLUE)
    d.text((80, 226), _trunc(module_name, 22), font=_font("bold", 64), fill=WHITE)

    # feature line
    d.text((80, 330), "Occupancy · Revenue · Attendance · EYFS · Staffing · Compliance",
           font=_font("reg", 21), fill=MUTE)

    # decorative bar-chart motif (brand flair, no data)
    heights = [70, 120, 95, 150, 110, 175]
    base = 560
    pts = []
    for i, hgt in enumerate(heights):
        x = 80 + i * 60
        d.rounded_rectangle((x, base - hgt, x + 40, base), radius=7, fill=BARS[i % len(BARS)])
        pts.append((x + 20, base - hgt - 14))
    for a, b in zip(pts, pts[1:]):
        d.line((a[0], a[1], b[0], b[1]), fill=(52, 211, 153), width=3)

    # footer
    d.text((80, 582), "Enterprise Early-Years Intelligence", font=_font("reg", 16), fill=DIM)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
