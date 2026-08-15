#!/usr/bin/env python3
"""Create the Esperón Si Te Vas V-Slice 0.8.6 mod from the validated Fango template."""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

SONG = "si-te-vas"
OLD = "fango"
MOD_ID = "esperon-dano-si-te-vas"
MOD_VERSION = "2.6.2"


def font(size: int):
    for candidate in ("DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def replace_text(path: Path) -> None:
    if path.suffix.lower() not in {".json", ".xml", ".hxc"}:
        return
    text = path.read_text(encoding="utf-8")
    replacements = [
        ("EsperonFango", "EsperonSiTeVas"),
        ("esperon-fango", "esperon-si-te-vas"),
        ("Esperón Fango", "Esperón Si Te Vas"),
        ("ESPERÓN — Fango", "ESPERÓN — Si Te Vas"),
        ("Escenario Fango", "Escenario Si Te Vas"),
        ("rival-fango", "rival-si-te-vas"),
        ("escenario-fango", "escenario-si-te-vas"),
        ("esperon-fango-notes", "esperon-si-te-vas-notes"),
        ("Fango", "Si Te Vas"),
        ("fango", "si-te-vas"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


def make_title(path: Path) -> None:
    image = Image.new("RGBA", (512, 128), (12, 64, 70, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 511, 127), outline=(255, 190, 190, 255), width=4)
    label = "SI TE VAS"
    f = font(54)
    box = draw.textbbox((0, 0), label, font=f)
    draw.text(((512 - (box[2] - box[0])) // 2, 30), label, fill=(255, 218, 218, 255), font=f)
    image.save(path)


def make_cover(source: Path, output: Path) -> None:
    image = Image.open(source).convert("RGB")
    image = ImageOps.fit(image, (512, 512), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    image.save(output, format="PNG", optimize=True)


def make_title_xml(path: Path) -> None:
    root = ET.Element("TextureAtlas", imagePath="esperon-si-te-vas-title.png")
    for name in ("switch0000", "idle0000"):
        ET.SubElement(root, "SubTexture", name=name, x="0", y="0", width="512", height="128", frameX="0", frameY="0", frameWidth="512", frameHeight="128")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def draw_character_frame(draw: ImageDraw.ImageDraw, index: int, primary: tuple[int, int, int], accent: tuple[int, int, int], rival: bool = False) -> None:
    cx = 64 + ((index % 3) - 1) * 4
    bob = (index % 2) * 3
    draw.ellipse((cx - 31, 14 + bob, cx + 31, 76 + bob), fill=accent, outline=(245, 245, 245), width=3)
    draw.polygon([(cx - 44, 82 + bob), (cx + 44, 82 + bob), (cx + 31, 174), (cx - 31, 174)], fill=primary, outline=(245, 245, 245))
    draw.line((cx - 18, 105 + bob, cx - 44, 140), fill=accent, width=8)
    draw.line((cx + 18, 105 + bob, cx + 44, 140), fill=accent, width=8)
    draw.line((cx - 14, 174, cx - 28, 190), fill=(25, 25, 35), width=8)
    draw.line((cx + 14, 174, cx + 28, 190), fill=(25, 25, 35), width=8)
    eye = (15, 20, 35) if not rival else (240, 240, 250)
    draw.ellipse((cx - 16, 38 + bob, cx - 7, 49 + bob), fill=eye)
    draw.ellipse((cx + 7, 38 + bob, cx + 16, 49 + bob), fill=eye)
    if index % 4 in (1, 3):
        draw.arc((cx - 18, 48 + bob, cx + 18, 66 + bob), 10, 170, fill=eye, width=3)


def make_character_atlas(png: Path, xml: Path, primary: tuple[int, int, int], accent: tuple[int, int, int], rival: bool = False) -> None:
    names = ["Idle0", "Idle1", "Left0", "Left1", "Down0", "Down1", "Up0", "Up1", "Right0", "Right1", "LeftHold0", "LeftHold1", "DownHold0", "DownHold1", "UpHold0", "UpHold1", "RightHold0", "RightHold1"]
    image = Image.new("RGBA", (128 * len(names), 192), (0, 0, 0, 0))
    for index, _ in enumerate(names):
        frame = Image.new("RGBA", (128, 192), (0, 0, 0, 0))
        draw_character_frame(ImageDraw.Draw(frame), index, primary, accent, rival=rival)
        image.alpha_composite(frame, (index * 128, 0))
    image.save(png, format="PNG", optimize=True)
    root = ET.Element("TextureAtlas", imagePath=png.name)
    for index, name in enumerate(names):
        ET.SubElement(root, "SubTexture", name=name, x=str(index * 128), y="0", width="128", height="192", frameX="0", frameY="0", frameWidth="128", frameHeight="192")
    ET.ElementTree(root).write(xml, encoding="utf-8", xml_declaration=True)


def arrow_polygon(direction: int, cx: int, cy: int, r: int = 43):
    if direction == 0:
        return [(cx - r, cy), (cx - 10, cy - r), (cx - 10, cy - 18), (cx + r, cy - 18), (cx + r, cy + 18), (cx - 10, cy + 18), (cx - 10, cy + r)]
    if direction == 1:
        return [(cx, cy - r), (cx + r, cy - 10), (cx + 18, cy - 10), (cx + 18, cy + r), (cx - 18, cy + r), (cx - 18, cy - 10), (cx - r, cy - 10)]
    if direction == 2:
        return [(cx, cy + r), (cx + 10, cy + 18), (cx + 10, cy - r), (cx - 10, cy - r), (cx - 10, cy + 18), (cx - r, cy + 18)]
    return [(cx + r, cy), (cx + 10, cy - r), (cx + 10, cy - 18), (cx - r, cy - 18), (cx - r, cy + 18), (cx + 10, cy + 18), (cx + 10, cy + r)]


def make_notes(root: Path) -> None:
    note_dir = root / "shared/images/notes"
    note_dir.mkdir(parents=True, exist_ok=True)
    colors = [(245, 110, 165), (95, 215, 205), (255, 205, 115), (165, 125, 245)]
    image = Image.new("RGBA", (512, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for i, color in enumerate(colors):
        cx = i * 128 + 64
        draw.polygon(arrow_polygon(i, cx, 64), fill=color, outline=(255, 255, 255), width=4)
    image.save(note_dir / "esperon-si-te-vas-notes-notes.png", optimize=True)
    note_xml = ET.Element("TextureAtlas", imagePath="esperon-si-te-vas-notes-notes.png")
    for i, name in enumerate(("noteLeft", "noteDown", "noteUp", "noteRight")):
        ET.SubElement(note_xml, "SubTexture", name=name, x=str(i * 128), y="0", width="128", height="128", frameX="0", frameY="0", frameWidth="128", frameHeight="128")
    ET.ElementTree(note_xml).write(note_dir / "esperon-si-te-vas-notes-notes.xml", encoding="utf-8", xml_declaration=True)

    strum = Image.new("RGBA", (512, 384), (0, 0, 0, 0))
    draw = ImageDraw.Draw(strum)
    for row, alpha in ((0, 150), (1, 210), (2, 255)):
        for i, color in enumerate(colors):
            cx = i * 128 + 64
            cy = row * 128 + 64
            fill = (*color, alpha)
            draw.polygon(arrow_polygon(i, cx, cy), fill=fill, outline=(255, 255, 255, 255), width=4)
    strum.save(note_dir / "esperon-si-te-vas-notes-strumline.png", optimize=True)
    strum_xml = ET.Element("TextureAtlas", imagePath="esperon-si-te-vas-notes-strumline.png")
    prefixes = ("static", "press", "confirm")
    for row, prefix in enumerate(prefixes):
        for i, name in enumerate(("Left", "Down", "Up", "Right")):
            ET.SubElement(strum_xml, "SubTexture", name=f"{prefix}{name}0", x=str(i * 128), y=str(row * 128), width="128", height="128", frameX="0", frameY="0", frameWidth="128", frameHeight="128")
    ET.ElementTree(strum_xml).write(note_dir / "esperon-si-te-vas-notes-strumline.xml", encoding="utf-8", xml_declaration=True)


def make_stage(path: Path) -> None:
    image = Image.new("RGBA", (1600, 900), (14, 62, 70, 255))
    draw = ImageDraw.Draw(image)
    for y in range(900):
        t = y / 899
        draw.line((0, y, 1600, y), fill=(int(14 + 30 * t), int(62 + 25 * t), int(70 + 45 * t), 255))
    draw.ellipse((1140, 95, 1330, 285), fill=(255, 193, 155, 255), outline=(255, 230, 210, 255), width=6)
    for x in range(0, 1600, 120):
        h = 130 + ((x * 17) % 210)
        draw.rectangle((x, 760 - h, x + 72, 760), fill=(12, 35, 45, 230))
        for wy in range(770 - h, 752, 34):
            draw.rectangle((x + 16, wy, x + 24, wy + 10), fill=(255, 210, 125, 220))
            draw.rectangle((x + 44, wy + 8, x + 52, wy + 18), fill=(140, 240, 225, 180))
    draw.rectangle((0, 760, 1600, 900), fill=(22, 25, 38, 255))
    draw.text((64, 70), "SI TE VAS", fill=(255, 220, 220, 255), font=font(52))
    image.save(path, optimize=True)


def make_story_and_icons(root: Path) -> None:
    cover = Image.open(root / "images/freeplay/albumRoll/esperon-si-te-vas-art.png").convert("RGBA")
    images = root / "images"
    (images / "storymenu/props").mkdir(parents=True, exist_ok=True)
    (images / "icons").mkdir(parents=True, exist_ok=True)
    story = Image.new("RGBA", (512, 256), (10, 35, 42, 255))
    story_draw = ImageDraw.Draw(story)
    story_draw.rectangle((16, 16, 495, 239), outline=(255, 190, 190, 255), width=5)
    story_draw.text((42, 92), "SI TE VAS", fill=(255, 220, 220, 255), font=font(50))
    story.save(images / "storymenu/esperon-si-te-vas.png", optimize=True)
    for kind, color in (("opponent", (255, 130, 185, 255)), ("player", (100, 220, 210, 255))):
        prop = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        d = ImageDraw.Draw(prop)
        d.ellipse((50, 30, 206, 186), fill=color, outline=(255, 255, 255, 255), width=5)
        d.polygon([(40, 190), (216, 190), (180, 245), (76, 245)], fill=(35, 42, 55, 255))
        d.text((62, 106), kind.upper(), fill=(20, 35, 45, 255), font=font(18))
        prop.save(images / f"storymenu/props/esperon-si-te-vas-{kind}.png", optimize=True)
    for name, tint in (("esperon-si-te-vas", (255, 150, 190, 255)), ("rival-si-te-vas", (100, 220, 210, 255))):
        icon = Image.new("RGBA", (300, 150), (0, 0, 0, 0))
        d = ImageDraw.Draw(icon)
        d.ellipse((50, 15, 135, 100), fill=tint, outline=(255, 255, 255, 255), width=4)
        d.polygon([(150, 105), (270, 105), (240, 145), (180, 145)], fill=tint)
        icon.save(images / "icons" / f"{name}.png", optimize=True)


def make_ui(root: Path) -> None:
    ui = root / "shared/images/ui/esperon-si-te-vas-notes"
    old_ui = root / "shared/images/ui/esperon-fango-notes"
    ui.mkdir(parents=True, exist_ok=True)
    for source in old_ui.glob("*.png"):
        image = Image.open(source).convert("RGBA")
        image = ImageOps.colorize(image.convert("L"), black=(10, 40, 48), white=(255, 190, 205)).convert("RGBA")
        image.save(ui / source.name, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--vocals-wav", type=Path, required=True)
    parser.add_argument("--inst-wav", type=Path, required=True)
    parser.add_argument("--cover-source", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    template = root / "mods/esperon-dano-fango"
    destination = root / f"mods/{MOD_ID}"
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(template, destination)

    # Rename nested files/directories before replacing textual references.
    for path in sorted(destination.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.name == "fango":
            path.rename(path.with_name(SONG))
        elif "fango" in path.name.lower():
            new_name = path.name.replace("Fango", "SiTeVas").replace("fango", SONG)
            path.rename(path.with_name(new_name))
    for path in destination.rglob("*"):
        if path.is_file():
            replace_text(path)

    # Update known structured contracts after broad replacement.
    meta_path = destination / "_polymod_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.update({"title": "Esperón — Si Te Vas", "description": "Esperón FNF Mobile V-Slice 0.8.6 — V2.6.2 vocal-only chart; stem separado con Demucs", "mod_version": MOD_VERSION})
    write_json(meta_path, meta)

    song_dir = destination / "data/songs" / SONG
    manifest = json.loads((song_dir / "manifest.json").read_text(encoding="utf-8")); manifest["songId"] = SONG; write_json(song_dir / "manifest.json", manifest)
    metadata_path = song_dir / f"{SONG}-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["songName"] = "Si Te Vas"
    metadata["charter"] = "Manus AI — vocal-only chart from separated Voices stem; Audio Sync Test móvil pendiente"
    metadata["playData"]["characters"] = {"player": "esperon-si-te-vas", "opponent": "rival-si-te-vas", "playerVocals": ["esperon-si-te-vas"], "opponentVocals": []}
    metadata["playData"]["stage"] = "escenario-si-te-vas"
    metadata["playData"]["noteStyle"] = "esperon-si-te-vas-notes"
    metadata["playData"]["album"] = "esperon-si-te-vas"
    metadata["generatedBy"] = "Friday Night Funkin' - 0.8.6; V2.6.2 Si Te Vas stem-separated vocal-only pipeline"
    write_json(metadata_path, metadata)

    level_path = destination / "data/levels" / f"esperon-{SONG}.json"
    level = json.loads(level_path.read_text(encoding="utf-8"))
    level.update({"name": "ESPERÓN — Si Te Vas", "titleAsset": "storymenu/esperon-si-te-vas", "songs": [SONG], "background": "#0E3E46"})
    level["capsule"]["name"] = "Si Te Vas"
    for prop in level.get("props", []):
        prop["assetPath"] = prop["assetPath"].replace("esperon-si-te-vas", "esperon-si-te-vas")
    write_json(level_path, level)

    stage_path = destination / "data/stages" / f"escenario-{SONG}.json"
    stage = json.loads(stage_path.read_text(encoding="utf-8")); stage["name"] = "Escenario Si Te Vas"; stage["props"][0]["assetPath"] = "stages/escenario-si-te-vas"; write_json(stage_path, stage)

    # Replace chart with a safe placeholder until the vocal generator promotes final timestamps.
    chart_path = song_dir / f"{SONG}-chart.json"
    chart = json.loads(chart_path.read_text(encoding="utf-8")); chart["version"] = "2.0.0"; chart["events"] = []; chart["notes"] = {"easy": [], "normal": [], "hard": []}; chart["generatedBy"] = "Friday Night Funkin' - 0.8.6"; write_json(chart_path, chart)

    # Convert separated stems to final runtime OGGs.
    audio_dir = destination / "songs" / SONG; audio_dir.mkdir(parents=True, exist_ok=True)
    for output, source in ((audio_dir / "Voices-esperon-si-te-vas.ogg", args.vocals_wav), (audio_dir / "Inst.ogg", args.inst_wav)):
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(source), "-c:a", "libvorbis", "-q:a", "6", "-ar", "44100", "-ac", "2", "-y", str(output)], check=True)

    # Use the embedded GitHub-provided cover from the Si Te Vas source M4A.
    art = destination / "images/freeplay/albumRoll/esperon-si-te-vas-art.png"
    make_cover(args.cover_source, art)
    make_title(destination / "images/freeplay/albumRoll/esperon-si-te-vas-title.png")
    make_title_xml(destination / "images/freeplay/albumRoll/esperon-si-te-vas-title.xml")
    album_path = destination / "data/ui/freeplay/albums/esperon-si-te-vas.json"
    album = json.loads(album_path.read_text(encoding="utf-8")); album.update({"name": "Si Te Vas", "albumArtAsset": "freeplay/albumRoll/esperon-si-te-vas-art", "albumTitleAsset": "freeplay/albumRoll/esperon-si-te-vas-title"}); write_json(album_path, album)

    make_character_atlas(destination / "shared/images/characters/esperon-si-te-vas.png", destination / "shared/images/characters/esperon-si-te-vas.xml", (255, 105, 160), (255, 218, 170), rival=False)
    make_character_atlas(destination / "shared/images/characters/rival-si-te-vas.png", destination / "shared/images/characters/rival-si-te-vas.xml", (70, 180, 185), (255, 190, 205), rival=True)
    make_notes(destination)
    make_stage(destination / "shared/images/stages/escenario-si-te-vas.png")
    make_story_and_icons(destination)
    make_ui(destination)

    hud = destination / "scripts/EsperonSiTeVasHudV2.hxc"
    hud.write_text('''import funkin.play.PlayState;\nimport funkin.modding.module.Module;\nclass EsperonSiTeVasHudV2 extends Module\n{\n  function new() { super("Esperón HUD — Si Te Vas", 1, {state: PlayState}); }\n  override function onCountdownStart(event)\n  {\n    super.onCountdownStart(event);\n    if (PlayState.instance == null || PlayState.instance.healthBar == null) return;\n    if (PlayState.instance.iconP1 == null) return;\n    if (PlayState.instance.iconP1.characterId != "esperon-si-te-vas") return;\n    PlayState.instance.healthBar.createFilledBar(0xFFFF9DBB, 0xFF46B8B6);\n    PlayState.instance.healthBar.updateBar();\n  }\n}\n''', encoding="utf-8")

    # Ensure JSON/XML replacements are valid after generated assets.
    for path in destination.rglob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
    for path in destination.rglob("*.xml"):
        ET.parse(path)
    print(json.dumps({"status": "PASS", "mod": str(destination), "song": SONG, "mod_version": MOD_VERSION, "cover": str(art.relative_to(root)), "audio": [str(p.relative_to(root)) for p in sorted(audio_dir.glob("*.ogg"))]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
