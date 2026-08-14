#!/usr/bin/env python3
"""Genera atlas geométricos multi-frame para animaciones vocales V-Slice."""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw

FRAME_W, FRAME_H = 128, 192
ANIMATION_FRAMES = [
    ("Idle", 2), ("Left", 2), ("Down", 2), ("Up", 2), ("Right", 2),
    ("LeftHold", 2), ("DownHold", 2), ("UpHold", 2), ("RightHold", 2),
]


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"#([0-9A-Fa-f]{6})", value)
    if not match:
        raise ValueError(f"Color inválido: {value}")
    raw = match.group(1)
    return tuple(int(raw[index:index + 2], 16) for index in (0, 2, 4))


def draw_frame(primary: tuple[int, int, int], secondary: tuple[int, int, int], pose: str, phase: int, rival: bool) -> Image.Image:
    img = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    base = pose.replace("Hold", "")
    movement = 4 if phase else -2
    lean = {"Idle": 0, "Left": -10, "Down": 0, "Up": 0, "Right": 10}[base]
    lift = {"Idle": movement, "Left": 4 + movement, "Down": 14 + movement, "Up": -13 + movement, "Right": 4 + movement}[base]
    if "Hold" in pose:
        lift = {"LeftHold": 5, "DownHold": 15, "UpHold": -14, "RightHold": 5}[pose] + (1 if phase else -1)
    cx, cy = 64 + lean, 68 + lift
    outline = (20, 21, 35, 255)
    glow = primary + (42,)
    draw.ellipse((cx - 37, cy - 37, cx + 37, cy + 37), fill=glow)
    draw.ellipse((cx - 26, cy - 26, cx + 26, cy + 26), fill=primary + (255,), outline=outline, width=4)
    body_top, body_bottom = cy + 24, cy + 78
    draw.rounded_rectangle((cx - 20, body_top, cx + 20, body_bottom), radius=5, fill=secondary + (255,), outline=outline, width=4)
    arm_shift = 5 if phase else -3
    if base == "Left":
        points = [(cx - 18, body_top + 8), (cx - 53, body_top - 5 + arm_shift), (cx - 29, body_top + 29)]
    elif base == "Right":
        points = [(cx + 18, body_top + 8), (cx + 53, body_top - 5 + arm_shift), (cx + 29, body_top + 29)]
    elif base == "Up":
        points = [(cx, body_top + 4), (cx + (4 if phase else -4), cy - 50), (cx + 19, body_top + 22)]
    elif base == "Down":
        points = [(cx - 25, body_top + 27), (cx + (5 if phase else -5), body_bottom + 30), (cx + 25, body_top + 27)]
    else:
        points = [(cx - 20, body_top + 19), (cx, body_bottom + 13 + arm_shift), (cx + 20, body_top + 19)]
    draw.polygon(points, fill=primary + (255,), outline=outline)
    eye = primary if rival else secondary
    draw.ellipse((cx - 14, cy - 5, cx - 6, cy + 3), fill=eye + (255,))
    draw.ellipse((cx + 6, cy - 5, cx + 14, cy + 3), fill=eye + (255,))
    mouth_y = cy + 11 + (2 if phase else 0)
    draw.rounded_rectangle((cx - 6, mouth_y, cx + 6, mouth_y + 3), radius=1, fill=outline)
    return img


def write_atlas(path: Path, frames: list[tuple[str, Image.Image]]) -> None:
    sheet = Image.new("RGBA", (FRAME_W * len(frames), FRAME_H), (0, 0, 0, 0))
    root = ET.Element("TextureAtlas", {"imagePath": path.name})
    for index, (name, frame) in enumerate(frames):
        sheet.alpha_composite(frame, (index * FRAME_W, 0))
        ET.SubElement(root, "SubTexture", {"name": name, "x": str(index * FRAME_W), "y": "0", "width": str(FRAME_W), "height": str(FRAME_H), "frameX": "0", "frameY": "0", "frameWidth": str(FRAME_W), "frameHeight": str(FRAME_H)})
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, optimize=True)
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path.with_suffix(".xml"), encoding="utf-8", xml_declaration=True)


def update_character_json(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    base = [
        {"name": "idle", "prefix": "Idle"},
        {"name": "singLEFT", "prefix": "Left"},
        {"name": "singDOWN", "prefix": "Down"},
        {"name": "singUP", "prefix": "Up"},
        {"name": "singRIGHT", "prefix": "Right"},
        {"name": "singLEFT-hold", "prefix": "LeftHold"},
        {"name": "singDOWN-hold", "prefix": "DownHold"},
        {"name": "singUP-hold", "prefix": "UpHold"},
        {"name": "singRIGHT-hold", "prefix": "RightHold"},
    ]
    data["animations"] = base
    data["generatedBy"] = "Geometric multi-frame vocal atlas for FNF Mobile V-Slice 0.8.6"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    report = []
    for mod in sorted((root / "mods").glob("esperon-dano-*")):
        song_dirs = list((mod / "data" / "songs").glob("*"))
        if len(song_dirs) != 1:
            continue
        song = song_dirs[0].name
        brief_path = root / "visual-briefs" / f"{song}.json"
        brief = json.loads(brief_path.read_text(encoding="utf-8"))
        primary = hex_to_rgb(brief["palette"]["primary"])
        secondary = hex_to_rgb(brief["palette"]["secondary"])
        metadata = json.loads((song_dirs[0] / f"{song}-metadata.json").read_text(encoding="utf-8"))
        ids = metadata["playData"]["characters"]
        for role, char_id in (("player", ids["player"]), ("rival", ids["opponent"])):
            frames: list[tuple[str, Image.Image]] = []
            for pose, count in ANIMATION_FRAMES:
                for phase in range(count):
                    frames.append((f"{pose}{phase}", draw_frame(primary if role == "player" else secondary, secondary if role == "player" else primary, pose, phase, role == "rival")))
            write_atlas(mod / "images" / "characters" / f"{char_id}.png", frames)
            update_character_json(mod / "data" / "characters" / f"{char_id}.json")
        report.append({"mod": mod.name, "song": song, "character_frames_per_atlas": len(ANIMATION_FRAMES) * 2})
    output = root / "artifacts" / "vocal-animation-report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"mods": len(report), "frames_per_atlas": len(ANIMATION_FRAMES) * 2, "report": report}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mods": len(report), "frames_per_atlas": len(ANIMATION_FRAMES) * 2}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
