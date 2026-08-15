#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]
root = Path(__file__).resolve().parents[1]
thumb = 220
label_h = 38
cols = 5
rows = (len(SONGS) + cols - 1) // cols
sheet = Image.new("RGB", (cols * thumb, rows * (thumb + label_h)), (22, 22, 25))
draw = ImageDraw.Draw(sheet)
font = ImageFont.load_default()
for i, song in enumerate(SONGS):
    path = root / "mods" / f"esperon-dano-{song}" / "images" / "freeplay" / "albumRoll" / f"esperon-{song}-art.png"
    with Image.open(path).convert("RGB") as image:
        image.thumbnail((thumb, thumb), Image.Resampling.LANCZOS)
        x = (i % cols) * thumb + (thumb - image.width) // 2
        y = (i // cols) * (thumb + label_h) + (thumb - image.height) // 2
        sheet.paste(image, (x, y))
    label = song[:31]
    tx = (i % cols) * thumb + 6
    ty = (i // cols) * (thumb + label_h) + thumb + 8
    draw.text((tx, ty), label, fill=(245, 245, 245), font=font)
out = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "freeplay-covers-contact-sheet-v261.png"
out.parent.mkdir(parents=True, exist_ok=True)
sheet.save(out, "PNG", optimize=True)
print(out)
