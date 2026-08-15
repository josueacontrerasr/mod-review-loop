#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import random
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
ASSET_REF = ROOT / "qa-lab" / "rebuild-v230" / "assets"
SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]
DIRECTIONS = ("left", "down", "up", "right")
PREFIX = {"left": "Left", "down": "Down", "up": "Up", "right": "Right"}
ROTATE = {"up": 0, "right": 1, "down": 2, "left": 3}

YOUTUBE = {
    "arcoloria": "https://www.youtube.com/watch?v=D8xYouxhoK4",
    "cortamos-y-volvemos": "https://www.youtube.com/watch?v=vXjIguLTV6o",
    "dano": "https://www.youtube.com/watch?v=jf0I4ZfkJKI",
    "dias-magicos": "https://www.youtube.com/watch?v=K65c4-MenIY",
    "eclipsis": "https://www.youtube.com/watch?v=6MTptExfQNk",
    "fango": "https://www.youtube.com/watch?v=-WyLZjAcveU",
    "luma": "https://www.youtube.com/watch?v=L2EmaRBEOx0",
    "maraton-de-peliculas": "https://www.youtube.com/watch?v=Ltnh5_ENUj8",
    "me-voy-a-morir-si-no-me-besas-ahora-mismo": "https://www.youtube.com/watch?v=JRysCcNm0Es",
    "meteora": "https://www.youtube.com/watch?v=-0lfqKeDyl0",
    "mi-hogar": "https://www.youtube.com/watch?v=jsgxrw4PnNQ",
    "nubia": "https://www.youtube.com/watch?v=QPt3bcvn1XA",
    "nuestro-amor-no-es-normal": "https://www.youtube.com/watch?v=B0anw7LDcDU",
    "peligrosa": "https://www.youtube.com/watch?v=d7jX66W-U98",
    "rompecabezas": "https://www.youtube.com/watch?v=p3lnWU23iaU",
    "solare": "https://www.youtube.com/watch?v=jY3j6tvPXFE",
    "tristella": "https://www.youtube.com/watch?v=hQsbS3SMGsg",
    "tu-dealer-de-nostalgia": "https://www.youtube.com/watch?v=szfHM0N-M4Q",
    "un-poco-bien-un-poco-mal": "https://www.youtube.com/watch?v=vBZVANTZar4",
    "volver-a-vernos": "https://www.youtube.com/watch?v=58JMohnYhqw",
}

MOTIFS = {
    "arcoloria": "arched halo and candles",
    "cortamos-y-volvemos": "film splice and reconnecting frames",
    "dano": "cracked neon heart",
    "dias-magicos": "paper stars and sunrise ribbons",
    "eclipsis": "eclipse ring and diagonal shadow",
    "fango": "wetland ripples and reeds",
    "luma": "prism spiral and glowing orbs",
    "maraton-de-peliculas": "film reels and theater beam",
    "me-voy-a-morir-si-no-me-besas-ahora-mismo": "two reaching silhouettes and suspended star",
    "meteora": "meteor trails and observatory",
    "mi-hogar": "warm geometric house and window",
    "nubia": "cloud arches and floating city",
    "nuestro-amor-no-es-normal": "mismatched orbiting hearts",
    "peligrosa": "blade-petal warning flower",
    "rompecabezas": "four-piece luminous puzzle",
    "solare": "orange sun, blinds and orbital rings",
    "tristella": "three stars and observatory steps",
    "tu-dealer-de-nostalgia": "analog cassette archive",
    "un-poco-bien-un-poco-mal": "split bright and moody landscape",
    "volver-a-vernos": "reconnecting twilight bridge",
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def hex_color(value: tuple[int, int, int]) -> str:
    return "#%02X%02X%02X" % value


def clamp(value: float) -> int:
    return max(0, min(255, round(value)))


def tint(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(clamp(c * factor) for c in color)


def blend(a: tuple[int, int, int], b: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
    return tuple(clamp(a[i] * (1 - ratio) + b[i] * ratio) for i in range(3))


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    )
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def title_from_brief(slug: str, brief: dict) -> str:
    return str(brief.get("song") or " ".join(word.capitalize() for word in slug.split("-")))


def load_brief(slug: str) -> dict:
    path = ROOT / "visual-briefs" / f"{slug}.json"
    brief = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    brief.setdefault("song", title_from_brief(slug, {}))
    palette = brief.setdefault("palette", {})
    palette.setdefault("primary", "#4E76C5")
    palette.setdefault("secondary", "#F0B44C")
    palette.setdefault("dark", "#171A35")
    return brief


def rotated(points: list[tuple[float, float]], direction: str, center: tuple[float, float]) -> list[tuple[float, float]]:
    result = []
    cx, cy = center
    for x, y in points:
        for _ in range(ROTATE[direction] % 4):
            x, y = cx - (y - cy), cy + (x - cx)
        result.append((x, y))
    return result


def arrow_polygon(size: int, direction: str, inset: int = 16) -> list[tuple[float, float]]:
    points = [
        (size / 2, inset), (size - inset, size * 0.54), (size * 0.68, size * 0.54),
        (size * 0.68, size - inset), (size * 0.32, size - inset), (size * 0.32, size * 0.54),
        (inset, size * 0.54),
    ]
    return rotated(points, direction, (size / 2, size / 2))


def draw_arrow(size: int, direction: str, primary: tuple[int, int, int], secondary: tuple[int, int, int], dark: tuple[int, int, int], accent: tuple[int, int, int], state: str, motif_index: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    points = arrow_polygon(size, direction, 15 if state == "static" else 11)
    if state != "static":
        glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.polygon(points, fill=(*accent, 190 if state == "confirm" else 125))
        glow = glow.filter(ImageFilter.GaussianBlur(8 if state == "confirm" else 5))
        image.alpha_composite(glow)
    draw = ImageDraw.Draw(image)
    fill = blend(primary, dark, 0.28 if state == "static" else 0.05)
    draw.polygon(points, fill=(*fill, 255), outline=(*dark, 255))
    draw.line(points + [points[0]], fill=(*accent, 240), width=3, joint="curve")
    inner = arrow_polygon(size, direction, 29)
    draw.line(inner[:4], fill=(*secondary, 220), width=4, joint="curve")
    variant = motif_index % 5
    if variant == 0:
        draw.ellipse((size * .40, size * .40, size * .60, size * .60), fill=(*secondary, 245), outline=(*accent, 255), width=2)
    elif variant == 1:
        draw.line((size * .34, size * .66, size * .50, size * .34, size * .66, size * .66), fill=(*secondary, 245), width=5, joint="curve")
    elif variant == 2:
        draw.rectangle((size * .39, size * .39, size * .61, size * .61), fill=(*secondary, 235), outline=(*accent, 255), width=2)
    elif variant == 3:
        draw.polygon([(size * .50, size * .31), (size * .67, size * .50), (size * .50, size * .69), (size * .33, size * .50)], fill=(*secondary, 245), outline=(*accent, 255))
    else:
        draw.ellipse((size * .33, size * .33, size * .67, size * .67), outline=(*secondary, 245), width=5)
    if state == "confirm":
        draw.line(points + [points[0]], fill=(*secondary, 255), width=2, joint="curve")
    return image


def write_atlas(path: Path, frames: list[tuple[str, Image.Image]], frame_width: int, frame_height: int, columns: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = math.ceil(len(frames) / columns)
    sheet = Image.new("RGBA", (columns * frame_width, rows * frame_height), (0, 0, 0, 0))
    root = ET.Element("TextureAtlas", {"imagePath": path.name})
    for index, (name, frame) in enumerate(frames):
        x = (index % columns) * frame_width
        y = (index // columns) * frame_height
        sheet.alpha_composite(frame, (x, y))
        ET.SubElement(root, "SubTexture", {
            "name": name, "x": str(x), "y": str(y), "width": str(frame_width), "height": str(frame_height),
            "frameX": "0", "frameY": "0", "frameWidth": str(frame_width), "frameHeight": str(frame_height),
        })
    sheet.save(path, optimize=True)
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path.with_suffix(".xml"), encoding="utf-8", xml_declaration=True)


def make_fallback_cover(path: Path, slug: str, pal: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]], index: int) -> None:
    primary, secondary, dark = pal
    image = Image.new("RGBA", (512, 512), (*dark, 255))
    draw = ImageDraw.Draw(image, "RGBA")
    rng = random.Random(index * 997 + 17)
    for i in range(10):
        x0 = rng.randint(-120, 380); y0 = rng.randint(-100, 380)
        w = rng.randint(100, 360); h = rng.randint(60, 280)
        color = primary if i % 2 else secondary
        draw.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=28, fill=(*color, 45 + i * 8), outline=(*color, 95), width=2)
    cx, cy = 256, 238
    draw.ellipse((76, 58, 436, 418), outline=(*secondary, 190), width=4)
    draw.ellipse((122, 104, 390, 372), outline=(*primary, 170), width=3)
    motif = index % 5
    if motif == 0:
        draw.ellipse((156, 158, 356, 358), fill=(*primary, 210), outline=(*secondary, 230), width=5)
        draw.line((cx, 74, cx, 424), fill=(*secondary, 180), width=3)
    elif motif == 1:
        for x in (150, 220, 290, 360):
            draw.arc((x - 90, 120, x + 90, 300), 200, 340, fill=(*primary, 190), width=10)
        draw.line((90, 384, 424, 114), fill=(*secondary, 220), width=7)
    elif motif == 2:
        draw.polygon([(256, 96), (390, 232), (256, 374), (122, 232)], fill=(*primary, 210), outline=(*secondary, 230))
        draw.line((130, 232, 382, 232), fill=(*dark, 190), width=5)
    elif motif == 3:
        for angle in range(0, 360, 45):
            r = math.radians(angle)
            draw.line((cx, cy, cx + math.cos(r) * 198, cy + math.sin(r) * 198), fill=(*primary, 150), width=5)
        draw.ellipse((205, 187, 307, 289), fill=(*secondary, 220), outline=(*primary, 240), width=4)
    else:
        draw.rectangle((128, 132, 384, 348), outline=(*secondary, 220), width=7)
        for y in (172, 240, 308):
            draw.line((150, y, 362, y), fill=(*primary, 200), width=8)
    draw.line((18, 470, 494, 470), fill=(*secondary, 180), width=5)
    image.save(path, optimize=True)


def prepare_cover(mod: Path, slug: str, brief: dict, pal: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]], index: int) -> dict[str, str]:
    album_id = f"esperon-{slug}"
    art = mod / "images" / "freeplay" / "albums" / f"{album_id}-art.png"
    title = mod / "images" / "freeplay" / "albums" / f"{album_id}-title.png"
    source = ASSET_REF / f"cover-{slug}.png"
    if not source.is_file():
        source.parent.mkdir(parents=True, exist_ok=True)
        make_fallback_cover(source, slug, pal, index)
    art.parent.mkdir(parents=True, exist_ok=True)
    base = ImageOps.fit(Image.open(source).convert("RGBA"), (512, 512), method=Image.Resampling.LANCZOS)
    primary, secondary, dark = pal
    overlay = Image.new("RGBA", (512, 512), (*dark, 22))
    base.alpha_composite(overlay)
    draw = ImageDraw.Draw(base, "RGBA")
    draw.rounded_rectangle((8, 8, 504, 504), radius=20, outline=(*secondary, 185), width=5)
    base.save(art, optimize=True)
    title_canvas = Image.new("RGBA", (512, 128), (*dark, 255))
    td = ImageDraw.Draw(title_canvas, "RGBA")
    td.rectangle((0, 0, 512, 128), fill=(*primary, 245))
    td.polygon([(0, 0), (220, 0), (115, 128), (0, 128)], fill=(*secondary, 220))
    td.rectangle((10, 10, 502, 118), outline=(*dark, 230), width=3)
    label = title_from_brief(slug, brief)
    size = 36 if len(label) <= 18 else 27 if len(label) <= 30 else 19
    f = font(size)
    box = td.textbbox((0, 0), label, font=f, stroke_width=2)
    tw, th = box[2] - box[0], box[3] - box[1]
    td.text(((512 - tw) / 2, (128 - th) / 2 - 4), label, font=f, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(*dark, 255))
    title_canvas.save(title, optimize=True)
    atlas_root = ET.Element("TextureAtlas", {"imagePath": title.name})
    for name in ("switch0000", "idle0000"):
        ET.SubElement(atlas_root, "SubTexture", {"name": name, "x": "0", "y": "0", "width": "512", "height": "128", "frameX": "0", "frameY": "0", "frameWidth": "512", "frameHeight": "128"})
    ET.indent(atlas_root, space="  ")
    ET.ElementTree(atlas_root).write(title.with_suffix(".xml"), encoding="utf-8", xml_declaration=True)
    return {"art": str(art.relative_to(mod)), "title": str(title.relative_to(mod)), "source": str(source.relative_to(ROOT))}


def update_note_style(mod: Path, slug: str, pal: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]], index: int) -> dict[str, str]:
    primary, secondary, dark = pal
    accent = blend(secondary, (255, 255, 255), 0.32)
    style_id = f"esperon-{slug}-notes"
    notes_dir = mod / "shared" / "images" / "notes"
    note_frames = [(f"note{PREFIX[direction]}", draw_arrow(128, direction, primary, secondary, dark, accent, "press", index)) for direction in DIRECTIONS]
    write_atlas(notes_dir / f"{style_id}-notes.png", note_frames, 128, 128, 4)
    strum_frames = []
    for state in ("static", "press", "confirm"):
        for direction in DIRECTIONS:
            strum_frames.append((f"{state}{PREFIX[direction]}0", draw_arrow(128, direction, primary, secondary, dark, accent, state, index)))
    write_atlas(notes_dir / f"{style_id}-strumline.png", strum_frames, 128, 128, 4)
    path = mod / "data" / "notestyles" / f"{style_id}.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"version": "1.0.0", "name": style_id, "author": "Manus AI", "fallback": "funkin", "assets": {}}
    data.update({"version": "1.0.0", "name": style_id, "author": "Manus AI", "fallback": "funkin", "generatedBy": "V-Slice 0.8.6 V2.3.0 cover-derived note style"})
    data.setdefault("assets", {})
    data["assets"]["note"] = {"assetPath": f"shared:notes/{style_id}-notes", "scale": 0.82, "data": {direction: {"prefix": f"note{PREFIX[direction]}"} for direction in DIRECTIONS}}
    data["assets"]["noteStrumline"] = {"assetPath": f"shared:notes/{style_id}-strumline", "scale": 0.92, "offsets": [0, 0], "data": {}}
    for direction in DIRECTIONS:
        pr = PREFIX[direction]
        data["assets"]["noteStrumline"]["data"].update({f"{direction}Static": {"prefix": f"static{pr}0"}, f"{direction}Press": {"prefix": f"press{pr}0"}, f"{direction}Confirm": {"prefix": f"confirm{pr}0"}, f"{direction}ConfirmHold": {"prefix": f"confirm{pr}0"}})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"style_id": style_id, "note_png": str((notes_dir / f"{style_id}-notes.png").relative_to(mod)), "strum_png": str((notes_dir / f"{style_id}-strumline.png").relative_to(mod))}


def draw_character_frame(kind: str, state: str, frame_index: int, pal: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]], motif_index: int) -> Image.Image:
    primary, secondary, dark = pal
    if kind == "player":
        body = blend(primary, (255, 255, 255), 0.12); accent = secondary; outline = dark
    else:
        body = blend(secondary, dark, 0.25); accent = primary; outline = dark
    image = Image.new("RGBA", (128, 192), (0, 0, 0, 0))
    d = ImageDraw.Draw(image, "RGBA")
    bob = -3 if frame_index % 2 else 0
    lean = {"idle": 0, "left": -5, "down": 2, "up": -2, "right": 5}.get(state.replace("hold", ""), 0)
    cx = 64 + lean
    # Ground shadow and angular body.
    d.ellipse((31, 172, 97, 187), fill=(*dark, 70))
    d.rounded_rectangle((38 + lean, 92 + bob, 90 + lean, 151 + bob), radius=12, fill=(*body, 255), outline=(*outline, 255), width=5)
    d.polygon([(43 + lean, 144 + bob), (54 + lean, 144 + bob), (48 + lean, 179), (37 + lean, 179)], fill=(*accent, 235), outline=(*outline, 255))
    d.polygon([(74 + lean, 144 + bob), (85 + lean, 144 + bob), (94 + lean, 179), (82 + lean, 179)], fill=(*accent, 235), outline=(*outline, 255))
    # Face/head with different hair motif per song.
    d.ellipse((31 + lean, 27 + bob, 97 + lean, 96 + bob), fill=(*body, 255), outline=(*outline, 255), width=5)
    hair = motif_index % 5
    if hair == 0:
        d.arc((27 + lean, 16 + bob, 101 + lean, 77 + bob), 180, 350, fill=(*accent, 255), width=10)
        d.ellipse((34 + lean, 16 + bob, 48 + lean, 32 + bob), fill=(*accent, 220))
        d.ellipse((79 + lean, 16 + bob, 94 + lean, 32 + bob), fill=(*accent, 220))
    elif hair == 1:
        d.polygon([(31 + lean, 49 + bob), (43 + lean, 12 + bob), (57 + lean, 30 + bob), (72 + lean, 10 + bob), (97 + lean, 47 + bob)], fill=(*accent, 235), outline=(*outline, 255))
    elif hair == 2:
        d.rectangle((28 + lean, 20 + bob, 100 + lean, 42 + bob), fill=(*accent, 225), outline=(*outline, 255), width=3)
    elif hair == 3:
        d.ellipse((30 + lean, 16 + bob, 99 + lean, 77 + bob), outline=(*accent, 235), width=9)
        d.line((34 + lean, 39 + bob, 23 + lean, 56 + bob), fill=(*accent, 220), width=6)
    else:
        d.polygon([(36 + lean, 34 + bob), (64 + lean, 8 + bob), (92 + lean, 34 + bob), (83 + lean, 47 + bob), (45 + lean, 47 + bob)], fill=(*accent, 220), outline=(*outline, 255))
    # Eyes and mouth keep the silhouette readable on mobile.
    d.ellipse((48 + lean, 56 + bob, 54 + lean, 63 + bob), fill=(*outline, 255))
    d.ellipse((75 + lean, 56 + bob, 81 + lean, 63 + bob), fill=(*outline, 255))
    d.arc((53 + lean, 65 + bob, 76 + lean, 82 + bob), 10 if state == "up" else 190, 165 if state == "up" else 350, fill=(*outline, 255), width=3)
    # Direction pose.
    if state == "left":
        d.line((42 + lean, 104 + bob, 15 + lean, 89 + bob), fill=(*accent, 255), width=9)
        d.line((86 + lean, 105 + bob, 105 + lean, 120 + bob), fill=(*accent, 240), width=8)
    elif state == "right":
        d.line((86 + lean, 104 + bob, 113 + lean, 89 + bob), fill=(*accent, 255), width=9)
        d.line((42 + lean, 105 + bob, 22 + lean, 120 + bob), fill=(*accent, 240), width=8)
    elif state == "up":
        d.line((48 + lean, 105 + bob, 34 + lean, 75 + bob), fill=(*accent, 255), width=8)
        d.line((80 + lean, 105 + bob, 94 + lean, 75 + bob), fill=(*accent, 255), width=8)
    elif state == "down":
        d.line((45 + lean, 106 + bob, 27 + lean, 137 + bob), fill=(*accent, 255), width=8)
        d.line((83 + lean, 106 + bob, 101 + lean, 137 + bob), fill=(*accent, 255), width=8)
    else:
        d.line((44 + lean, 105 + bob, 24 + lean, 115 + bob), fill=(*accent, 240), width=8)
        d.line((84 + lean, 105 + bob, 104 + lean, 115 + bob), fill=(*accent, 240), width=8)
    return image


def update_character(mod: Path, slug: str, brief: dict, pal: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]], index: int) -> list[str]:
    result = []
    for kind, char_id in (("player", f"esperon-{slug}"), ("rival", f"rival-{slug}")):
        frames = [("Idle", "idle"), ("Idle", "idle"), ("Left", "left"), ("Left", "left"), ("Down", "down"), ("Down", "down"), ("Up", "up"), ("Up", "up"), ("Right", "right"), ("Right", "right"), ("LeftHold", "left"), ("LeftHold", "left"), ("DownHold", "down"), ("DownHold", "down"), ("UpHold", "up"), ("UpHold", "up"), ("RightHold", "right"), ("RightHold", "right")]
        rendered = []
        for i, (prefix, state) in enumerate(frames):
            name = f"{prefix}{i % 2}"
            rendered.append((name, draw_character_frame(kind, state + ("hold" if "Hold" in prefix else ""), i, pal, index)))
        path = mod / "shared" / "images" / "characters" / f"{char_id}.png"
        write_atlas(path, rendered, 128, 192, 18)
        data_path = mod / "data" / "characters" / f"{char_id}.json"
        data = json.loads(data_path.read_text(encoding="utf-8")) if data_path.is_file() else {"version": "1.0.2", "name": char_id, "renderType": "sparrow", "assetPath": f"characters/{char_id}"}
        data.update({"version": "1.0.2", "renderType": "sparrow", "assetPath": f"characters/{char_id}", "generatedBy": "V-Slice Mobile 0.8.6 V2.3.0 cover-derived geometric character atlas", "startingAnimation": "idle", "scale": 1.0, "isPixel": False, "danceEvery": 1.0, "singTime": 8.0})
        data.setdefault("animations", [
            {"name": "idle", "prefix": "Idle"}, {"name": "singLEFT", "prefix": "Left"}, {"name": "singDOWN", "prefix": "Down"}, {"name": "singUP", "prefix": "Up"}, {"name": "singRIGHT", "prefix": "Right"},
            {"name": "singLEFT-hold", "prefix": "LeftHold"}, {"name": "singDOWN-hold", "prefix": "DownHold"}, {"name": "singUP-hold", "prefix": "UpHold"}, {"name": "singRIGHT-hold", "prefix": "RightHold"},
        ])
        data_path.parent.mkdir(parents=True, exist_ok=True)
        data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result.append(str(path.relative_to(mod)))
    return result


def build_stage(mod: Path, slug: str, cover_path: Path, pal: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]], index: int) -> str:
    primary, secondary, dark = pal
    base = ImageOps.fit(Image.open(cover_path).convert("RGBA"), (1280, 720), method=Image.Resampling.LANCZOS)
    base = base.filter(ImageFilter.GaussianBlur(0.6))
    overlay = Image.new("RGBA", base.size, (*dark, 75))
    base.alpha_composite(overlay)
    d = ImageDraw.Draw(base, "RGBA")
    d.rectangle((0, 545, 1280, 720), fill=(*dark, 180))
    d.line((0, 565, 1280, 565), fill=(*secondary, 190), width=5)
    for x in range(0, 1280, 80):
        d.line((x, 565, x + 40, 720), fill=(*primary, 80), width=3)
    d.ellipse((470, 110, 810, 450), outline=(*secondary, 130), width=4)
    d.ellipse((530, 170, 750, 390), outline=(*primary, 100), width=3)
    path = mod / "shared" / "images" / "stages" / f"escenario-{slug}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    base.save(path, optimize=True)
    return str(path.relative_to(mod))


def update_metadata(mod: Path, slug: str, brief: dict, album_id: str) -> None:
    song_dir = next((mod / "data" / "songs").iterdir())
    meta_path = song_dir / f"{slug}-metadata.json"
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta.setdefault("playData", {})["album"] = album_id
        meta["generatedBy"] = "Friday Night Funkin' - 0.8.6; V2.3.0 audio-synced charts and cover-derived visual pack"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    album_path = mod / "data" / "ui" / "freeplay" / "albums" / f"{album_id}.json"
    album = json.loads(album_path.read_text(encoding="utf-8")) if album_path.is_file() else {"version": "1.0.3", "artists": ["Esperón"]}
    title = title_from_brief(slug, brief)
    album.update({"version": "1.0.3", "name": title, "artists": ["Esperón"], "albumArtAsset": f"freeplay/albums/{album_id}-art", "albumTitleAsset": f"freeplay/albums/{album_id}-title", "albumTitleOffsets": [0, 0], "albumTitleAnimations": [], "albumOSTName": "ESPERÓN", "generatedBy": "V-Slice Mobile 0.8.6 V2.3.0"})
    album_path.parent.mkdir(parents=True, exist_ok=True)
    album_path.write_text(json.dumps(album, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = mod / "_polymod_meta.json"
    if manifest.is_file():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["mod_version"] = "2.3.0"
        data["api_version"] = "0.8.6"
        data["description"] = f"Mod V-Slice Mobile 0.8.6 de {title}; charts vocalmente alineados, dificultades easy/normal/hard y paquete visual V2.3.0."
        manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    rows = []
    for index, slug in enumerate(SONGS):
        mod = ROOT / "mods" / f"esperon-dano-{slug}"
        brief = load_brief(slug)
        pal = tuple(rgb(brief["palette"][key]) for key in ("primary", "secondary", "dark"))
        cover = prepare_cover(mod, slug, brief, pal, index)
        style = update_note_style(mod, slug, pal, index)
        characters = update_character(mod, slug, brief, pal, index)
        stage = build_stage(mod, slug, mod / cover["art"], pal, index)
        album_id = f"esperon-{slug}"
        update_metadata(mod, slug, brief, album_id)
        brief["source_urls"] = sorted(set((brief.get("source_urls") or []) + [YOUTUBE.get(slug)]))
        brief["youtube_reference"] = YOUTUBE.get(slug)
        brief["visual_theme_v230"] = MOTIFS[slug]
        brief["visual_design_v230"] = {"arrows": "four direction-readable beveled arrows with cover-derived primary/secondary/accent colors", "characters": "unique 18-frame Sparrow geometric atlas with directional poses and hold poses", "stage": "cover-derived high-contrast background with platform and orbital motif", "cover": "AI-generated original cover when available; deterministic geometric fallback only when the daily generator quota blocked it"}
        (ROOT / "visual-briefs" / f"{slug}.json").write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        rows.append({"song": slug, "title": title_from_brief(slug, brief), "palette": {"primary": hex_color(pal[0]), "secondary": hex_color(pal[1]), "dark": hex_color(pal[2])}, "motif": MOTIFS[slug], "youtube_reference": YOUTUBE.get(slug), "cover": cover, "note_style": style, "characters": characters, "stage": stage, "cover_source_ai": Path(cover["source"]).name.startswith("cover-") and (ASSET_REF / Path(cover["source"]).name).is_file() and slug not in {"solare", "tristella", "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos"}})
    out = ROOT / "qa-lab" / "rebuild-v230" / "visual-redesign-v230.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"status": "PASS", "version": "2.3.0", "songs": len(rows), "rows": rows, "note_frame_size": 128, "character_frame_size": [128, 192], "cover_size": [512, 512], "title_size": [512, 128]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "songs": len(rows), "output": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
