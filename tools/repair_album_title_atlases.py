#!/usr/bin/env python3
"""Add Sparrow XML atlases required by AlbumRoll for custom album titles.

FNF v0.8.6 AlbumRoll loads albumArtAsset with Paths.image but loads
albumTitleAsset with FunkinSprite.createSparrow and prefixes idle0/switch0.
This utility creates a valid XML atlas beside every existing title PNG.
It never changes audio, charts, metadata, or album IDs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree
from PIL import Image


def write_title_atlas(png: Path) -> Path:
    xml = png.with_suffix(".xml")
    with Image.open(png) as image:
        width, height = image.size
    atlas = Element("TextureAtlas", {"imagePath": png.name})
    # AlbumRoll adds animations using prefixes idle0 and switch0. A single
    # frame for each prefix is valid and avoids a missing-atlas null reference.
    for name in ("switch0000", "idle0000"):
        SubElement(atlas, "SubTexture", {
            "name": name,
            "x": "0",
            "y": "0",
            "width": str(width),
            "height": str(height),
            "frameX": "0",
            "frameY": "0",
            "frameWidth": str(width),
            "frameHeight": str(height),
        })
    tree = ElementTree(atlas)
    tree.write(xml, encoding="utf-8", xml_declaration=True)
    return xml


def find_title_pngs(root: Path, only_mod: str | None) -> list[Path]:
    mods = [root / "mods" / only_mod] if only_mod else sorted((root / "mods").glob("esperon-dano-*"))
    pngs: list[Path] = []
    for mod in mods:
        if not mod.is_dir():
            raise SystemExit(f"No existe el mod: {mod}")
        for album_json in sorted((mod / "data/ui/freeplay/albums").glob("*.json")):
            data = json.loads(album_json.read_text(encoding="utf-8"))
            asset = data.get("albumTitleAsset")
            if not isinstance(asset, str) or not asset:
                raise SystemExit(f"albumTitleAsset ausente en {album_json}")
            if asset.startswith("shared:"):
                png = mod / "shared/images" / (asset.removeprefix("shared:") + ".png")
            else:
                png = mod / "images" / (asset + ".png")
            if not png.is_file():
                raise SystemExit(f"No existe el PNG de título: {png}")
            pngs.append(png)
    return pngs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--mod", help="Solo modifica un directorio de mod, para prueba canaria")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    pngs = find_title_pngs(root, args.mod)
    results = []
    for png in pngs:
        xml = write_title_atlas(png)
        results.append({"png": str(png.relative_to(root)), "xml": str(xml.relative_to(root))})
    report = root / "reports" / "album-title-atlas-repair.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({"status": "PASS", "count": len(results), "files": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "count": len(results), "report": str(report)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
