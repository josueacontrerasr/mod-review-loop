#!/usr/bin/env python3
"""Integra personalización visual V2 en un mod FNF V-Slice sin editar contenido musical.

Genera sprites geométricos originales para notes, receptores, juicios y combo;
crea un note style con fallback `funkin`; actualiza solo playData.noteStyle y los
metadatos de versión de distribución. Nunca modifica audio, charts, BPM, offsets
ni timeChanges.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DIRECTIONS = ("left", "down", "up", "right")
DIRECTION_PREFIX = {"left": "Left", "down": "Down", "up": "Up", "right": "Right"}
STATE_ORDER = ("static", "press", "confirm")
QUALITY_VERSION = "1.1.0"

# Motivos distintos derivados de cada título; su índice determina la construcción geométrica.
MOTIFS = {
    "arcoloria": ("pétalos cromáticos", 0),
    "cortamos-y-volvemos": ("corte de película", 1),
    "dano": ("neón herido", 2),
    "dias-magicos": ("destello de amanecer", 3),
    "eclipsis": ("corona eclipsada", 4),
    "fango": ("gota luminosa", 5),
    "luma": ("prisma luminoso", 6),
    "maraton-de-peliculas": ("sala de proyección", 7),
    "me-voy-a-morir-si-no-me-besas-ahora-mismo": ("latido urgente", 8),
    "meteora": ("trazo meteórico", 9),
    "mi-hogar": ("refugio cálido", 10),
    "nubia": ("nube estelar", 11),
    "nuestro-amor-no-es-normal": ("amor asimétrico", 12),
    "peligrosa": ("señal de peligro", 13),
    "rompecabezas": ("pieza encajable", 14),
    "solare": ("rayo solar", 15),
    "tristella": ("triple estrella", 16),
    "tu-dealer-de-nostalgia": ("cinta analógica", 17),
    "un-poco-bien-un-poco-mal": ("dualidad equilibrada", 18),
    "volver-a-vernos": ("reencuentro crepuscular", 19),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def blend(a: tuple[int, int, int], b: tuple[int, int, int], portion: float) -> tuple[int, int, int]:
    return tuple(round(a[i] * (1 - portion) + b[i] * portion) for i in range(3))


def rgba(color: tuple[int, int, int], alpha: int = 255) -> tuple[int, int, int, int]:
    return color + (alpha,)


def rotate_point(point: tuple[float, float], turns: int, centre: tuple[float, float]) -> tuple[float, float]:
    x, y = point
    cx, cy = centre
    for _ in range(turns % 4):
        x, y = cx - (y - cy), cy + (x - cx)
    return x, y


def arrow_polygon(size: int, direction: str, inset: int = 18) -> list[tuple[float, float]]:
    # La forma de base mira hacia arriba; se rota de modo determinista por dirección.
    base = [(size / 2, inset), (size - inset, size * 0.57), (size * 0.69, size * 0.57), (size * 0.69, size - inset), (size * 0.31, size - inset), (size * 0.31, size * 0.57), (inset, size * 0.57)]
    turns = {"up": 0, "right": 1, "down": 2, "left": 3}[direction]
    return [rotate_point(p, turns, (size / 2, size / 2)) for p in base]


def draw_motif(draw: ImageDraw.ImageDraw, size: int, motif_index: int, primary: tuple[int, int, int], secondary: tuple[int, int, int], dark: tuple[int, int, int], *, state: str) -> None:
    cx = cy = size // 2
    accent = rgba(secondary, 235 if state != "static" else 185)
    glow = rgba(primary, 95 if state != "static" else 55)
    variant = motif_index % 10
    if variant == 0:  # pétalos
        for angle in range(0, 360, 60):
            rad = math.radians(angle)
            x = cx + math.cos(rad) * size * 0.24
            y = cy + math.sin(rad) * size * 0.24
            draw.ellipse((x - size * 0.10, y - size * 0.10, x + size * 0.10, y + size * 0.10), fill=accent)
    elif variant == 1:  # fotograma
        for x in range(12, size - 12, 26):
            draw.rectangle((x, 8, x + 12, 20), fill=accent)
            draw.rectangle((x, size - 20, x + 12, size - 8), fill=accent)
    elif variant == 2:  # fractura
        draw.line((size * .23, size * .20, size * .45, size * .46, size * .35, size * .72, size * .72, size * .86), fill=accent, width=8)
    elif variant == 3:  # estrella
        pts = []
        for i in range(8):
            r = size * (.30 if i % 2 == 0 else .12)
            angle = -math.pi / 2 + i * math.pi / 4
            pts.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))
        draw.polygon(pts, fill=accent)
    elif variant == 4:  # eclipse
        draw.ellipse((size*.20, size*.20, size*.80, size*.80), outline=accent, width=10)
        draw.ellipse((size*.39, size*.19, size*.88, size*.68), fill=rgba(dark, 210))
    elif variant == 5:  # gota
        draw.ellipse((size*.34, size*.35, size*.66, size*.72), fill=accent)
        draw.polygon([(cx, size*.16), (size*.66, size*.51), (size*.34, size*.51)], fill=accent)
    elif variant == 6:  # prisma
        draw.polygon([(cx, size*.17), (size*.80, size*.76), (size*.20, size*.76)], outline=accent, width=9)
        draw.line((cx, size*.17, cx, size*.76), fill=glow, width=7)
    elif variant == 7:  # claqueta
        draw.rectangle((size*.22, size*.39, size*.78, size*.75), outline=accent, width=8)
        draw.polygon([(size*.20, size*.31), (size*.68, size*.21), (size*.80, size*.36), (size*.31, size*.47)], fill=accent)
    elif variant == 8:  # latido
        points = [(cx, size*.76), (size*.22, size*.50), (size*.32, size*.29), (cx, size*.40), (size*.68, size*.29), (size*.78, size*.50)]
        draw.polygon(points, fill=accent)
    else:  # patrón modular / orbitas / contraste
        for pos in ((.34,.34),(.66,.34),(.34,.66),(.66,.66)):
            x,y = size*pos[0], size*pos[1]
            draw.rectangle((x-size*.09,y-size*.09,x+size*.09,y+size*.09), fill=accent)
        draw.ellipse((size*.30,size*.30,size*.70,size*.70), outline=glow, width=5)


def arrow_frame(size: int, direction: str, primary: tuple[int, int, int], secondary: tuple[int, int, int], dark: tuple[int, int, int], motif_index: int, state: str) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    if state == "confirm":
        draw.ellipse((7, 7, size-7, size-7), fill=rgba(secondary, 68), outline=rgba(primary, 180), width=6)
    elif state == "press":
        draw.ellipse((17, 17, size-17, size-17), fill=rgba(primary, 43), outline=rgba(secondary, 145), width=5)
    poly = arrow_polygon(size, direction, 20 if state == "static" else 14)
    fill = rgba(blend(primary, dark, .25) if state == "static" else primary)
    draw.polygon(poly, fill=fill, outline=rgba(dark, 255))
    draw.line(poly + [poly[0]], fill=rgba(dark, 255), width=7, joint="curve")
    draw_motif(draw, size, motif_index, primary, secondary, dark, state=state)
    if state == "confirm":
        draw.line(poly + [poly[0]], fill=rgba(secondary, 255), width=4, joint="curve")
    return image


def save_sheet_with_xml(path: Path, frames: list[tuple[str, Image.Image]], frame_w: int, frame_h: int) -> None:
    cols = 4
    rows = math.ceil(len(frames) / cols)
    sheet = Image.new("RGBA", (cols * frame_w, rows * frame_h), (0, 0, 0, 0))
    root = ET.Element("TextureAtlas", {"imagePath": path.name})
    for index, (name, frame) in enumerate(frames):
        x = (index % cols) * frame_w
        y = (index // cols) * frame_h
        sheet.alpha_composite(frame, (x, y))
        ET.SubElement(root, "SubTexture", {"name": name, "x": str(x), "y": str(y), "width": str(frame_w), "height": str(frame_h), "frameX": "0", "frameY": "0", "frameWidth": str(frame_w), "frameHeight": str(frame_h)})
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, optimize=True)
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path.with_suffix(".xml"), encoding="utf-8", xml_declaration=True)


def font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def draw_badge(path: Path, label: str, primary: tuple[int, int, int], secondary: tuple[int, int, int], dark: tuple[int, int, int], motif_index: int) -> None:
    width, height = 420, 140
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    fill = primary if label in ("SICK!", "GOOD") else secondary
    draw.rounded_rectangle((8, 10, width-8, height-10), radius=30, fill=rgba(dark, 238), outline=rgba(fill, 255), width=7)
    draw_motif(draw, 116, motif_index, primary, secondary, dark, state="confirm")
    fnt = font(62 if label != "SICK!" else 58)
    bbox = draw.textbbox((0, 0), label, font=fnt, stroke_width=2)
    tx = 140 + ((width - 144) - (bbox[2] - bbox[0])) / 2
    ty = (height - (bbox[3] - bbox[1])) / 2 - bbox[1]
    draw.text((tx, ty), label, font=fnt, fill=rgba(fill), stroke_width=3, stroke_fill=rgba(dark))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)


def draw_combo(path: Path, digit: int, primary: tuple[int, int, int], secondary: tuple[int, int, int], dark: tuple[int, int, int], motif_index: int) -> None:
    width, height = 104, 132
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((5, 5, width-5, height-5), radius=18, fill=rgba(dark, 205), outline=rgba(secondary, 230), width=5)
    if motif_index % 2 == 0:
        draw.ellipse((14, 16, width-14, height-16), outline=rgba(primary, 120), width=4)
    else:
        draw.polygon([(width/2, 13),(width-15,height/2),(width/2,height-13),(15,height/2)], outline=rgba(primary, 150), width=4)
    fnt = font(88)
    label = str(digit)
    bbox = draw.textbbox((0, 0), label, font=fnt, stroke_width=2)
    x = (width - (bbox[2]-bbox[0])) / 2
    y = (height - (bbox[3]-bbox[1])) / 2 - bbox[1]
    draw.text((x, y), label, font=fnt, fill=rgba(primary), stroke_width=3, stroke_fill=rgba(dark))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)


def note_style_data(note_style_id: str, title: str) -> dict[str, Any]:
    note_path = f"shared:notes/{note_style_id}-notes"
    strum_path = f"shared:notes/{note_style_id}-strumline"
    assets: dict[str, Any] = {
        "note": {
            "assetPath": note_path,
            "scale": 1.0,
            "data": {direction: {"prefix": f"note{DIRECTION_PREFIX[direction]}"} for direction in DIRECTIONS},
        },
        "noteStrumline": {
            "assetPath": strum_path,
            "scale": 1.3,
            "offsets": [0, 0],
            "data": {},
        },
        "judgementSick": {"assetPath": f"shared:ui/{note_style_id}/sick", "scale": 0.62, "isPixel": False},
        "judgementGood": {"assetPath": f"shared:ui/{note_style_id}/good", "scale": 0.62, "isPixel": False},
        "judgementBad": {"assetPath": f"shared:ui/{note_style_id}/bad", "scale": 0.62, "isPixel": False},
        "judgementShit": {"assetPath": f"shared:ui/{note_style_id}/shit", "scale": 0.62, "isPixel": False},
    }
    strum_data = assets["noteStrumline"]["data"]
    for direction in DIRECTIONS:
        prefix = DIRECTION_PREFIX[direction]
        strum_data[f"{direction}Static"] = {"prefix": f"static{prefix}0"}
        strum_data[f"{direction}Press"] = {"prefix": f"press{prefix}0"}
        strum_data[f"{direction}Confirm"] = {"prefix": f"confirm{prefix}0"}
        strum_data[f"{direction}ConfirmHold"] = {"prefix": f"confirm{prefix}0"}
    for digit in range(10):
        assets[f"comboNumber{digit}"] = {"assetPath": f"shared:ui/{note_style_id}/num{digit}", "isPixel": False, "scale": 0.45}
    return {"version": "1.0.0", "name": f"Esperón — {title} Visual V2", "author": "Manus AI", "fallback": "funkin", "assets": assets}


def update_text(path: Path, old_prefix: str, new_line: str) -> None:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = [line for line in current.splitlines() if not line.startswith(old_prefix)]
    lines.append(new_line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def apply_to_mod(mod: Path) -> Path:
    slug = mod.name.removeprefix("esperon-dano-")
    if slug not in MOTIFS:
        raise ValueError(f"No hay motivo visual para {slug}")
    metadata_paths = sorted((mod / "data/songs").glob("*/*-metadata.json"))
    if len(metadata_paths) != 1:
        raise ValueError(f"Metadata no única en {mod.name}")
    metadata_path = metadata_paths[0]
    metadata = read_json(metadata_path)
    title = str(metadata.get("songName") or slug)
    style_id = f"esperon-{slug}-notes"
    brief_path = ROOT / "visual-briefs" / f"{slug}.json"
    brief = read_json(brief_path)
    palette = brief["palette"]
    primary, secondary, dark = rgb(palette["primary"]), rgb(palette["secondary"]), rgb(palette["dark"])
    motif, motif_index = MOTIFS[slug]

    chart_paths = sorted((mod / "data/songs").glob("*/*-chart.json"))
    if len(chart_paths) != 1:
        raise ValueError(f"Chart no único en {mod.name}")
    protected_before = {"chart_sha256": sha256(chart_paths[0]), "inst_sha256": sha256(next((mod / "songs").rglob("Inst.ogg")))}

    notes_dir = mod / "images/notes"
    ui_dir = mod / "images/ui" / style_id
    note_frames = [(f"note{DIRECTION_PREFIX[d]}", arrow_frame(160, d, primary, secondary, dark, motif_index, "press")) for d in DIRECTIONS]
    save_sheet_with_xml(notes_dir / f"{style_id}-notes.png", note_frames, 160, 160)
    strum_frames: list[tuple[str, Image.Image]] = []
    for state in STATE_ORDER:
        for direction in DIRECTIONS:
            strum_frames.append((f"{state}{DIRECTION_PREFIX[direction]}0", arrow_frame(176, direction, primary, secondary, dark, motif_index, state)))
    save_sheet_with_xml(notes_dir / f"{style_id}-strumline.png", strum_frames, 176, 176)

    for label, filename in (("SICK!", "sick"), ("GOOD", "good"), ("BAD", "bad"), ("MISS", "shit")):
        draw_badge(ui_dir / f"{filename}.png", label, primary, secondary, dark, motif_index)
    for digit in range(10):
        draw_combo(ui_dir / f"num{digit}.png", digit, primary, secondary, dark, motif_index)

    write_json(mod / "data/notestyles" / f"{style_id}.json", note_style_data(style_id, title))
    metadata["playData"]["noteStyle"] = style_id
    metadata["generatedBy"] = "Friday Night Funkin' - 0.8.6; visual V2 only, no musical data altered"
    write_json(metadata_path, metadata)

    manifest_path = mod / "_polymod_meta.json"
    manifest = read_json(manifest_path)
    manifest["mod_version"] = QUALITY_VERSION
    manifest["description"] = f"Mod V-Slice candidato para {title}; Visual V2 con note style y HUD temático. Requiere Audio Sync Test y playtest móvil."
    write_json(manifest_path, manifest)
    docs_dir = ROOT / "docs" / "mod-documentation-v220" / slug
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "visual-v2-notes.txt").write_text(f"VISUAL_V2: note style, receptores, juicios y combo geométricos originales para {title}.\nVISUAL_V2: comprobar carga y playtest móvil para {style_id}.\n", encoding="utf-8")

    brief["visual_system_v2"]["status"] = "INTEGRATED_PENDING_MOBILE_PLAYTEST"
    brief["visual_system_v2"]["note_style"]["files"] = [
        f"data/notestyles/{style_id}.json",
        f"images/notes/{style_id}-notes.png",
        f"images/notes/{style_id}-notes.xml",
        f"images/notes/{style_id}-strumline.png",
        f"images/notes/{style_id}-strumline.xml",
    ]
    brief["visual_system_v2"]["hud"]["files"] = [f"images/ui/{style_id}/{name}.png" for name in ("sick", "good", "bad", "shit", *[f"num{digit}" for digit in range(10)])]
    write_json(brief_path, brief)

    protected_after = {"chart_sha256": sha256(chart_paths[0]), "inst_sha256": sha256(next((mod / "songs").rglob("Inst.ogg")))}
    if protected_before != protected_after:
        raise RuntimeError(f"Integridad musical violada en {mod.name}")
    write_json(ROOT / "qa-lab" / "visual-evidence-v2" / slug / "visual-v2-integrity.json", {"scope": "VISUAL_ONLY", "protected_before": protected_before, "protected_after": protected_after, "status": "PASS_NO_MUSICAL_DATA_CHANGED"})

    archive = ROOT / "dist" / f"{mod.name}-v{QUALITY_VERSION}.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        archive.unlink()
    shutil.make_archive(str(archive.with_suffix("")), "zip", root_dir=mod.parent, base_dir=mod.name)
    return archive


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mod", required=True, help="ID del mod bajo mods/")
    args = parser.parse_args()
    mod = ROOT / "mods" / args.mod
    if not mod.is_dir():
        raise SystemExit(f"Mod no encontrado: {mod}")
    archive = apply_to_mod(mod)
    print(json.dumps({"mod": mod.name, "archive": str(archive.relative_to(ROOT)), "status": "VISUAL_V2_CREATED"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
