#!/usr/bin/env python3
"""Crea datos y carátulas Freeplay V-Slice desde assets geométricos ya validados.

Se usa como alternativa determinista después de que la generación visual no está disponible.
No reemplaza personajes, stage ni HUD existentes; añade assets de álbum y metadata album.
"""
from __future__ import annotations

import json
import re
import sys
from hashlib import sha256
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

FONT = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')


def color_from_token(token: str, shift: int = 0) -> tuple[int, int, int]:
    digest = sha256((token + str(shift)).encode()).digest()
    palette = [(246, 163, 26), (64, 184, 232), (171, 90, 231), (239, 93, 110), (53, 199, 147)]
    return palette[digest[0] % len(palette)]


def song_title(slug: str) -> str:
    return ' '.join(word.capitalize() for word in slug.split('-'))


def image_path_for_stage(mod: Path) -> Path:
    stages = sorted((mod / 'images' / 'stages').glob('*.png'))
    if not stages:
        raise RuntimeError(f'No stage PNG in {mod}')
    return stages[0]


def build_art(mod: Path, slug: str, destination: Path) -> None:
    base = Image.new('RGBA', (512, 512), (24, 33, 58, 255))
    stage = Image.open(image_path_for_stage(mod)).convert('RGBA')
    backdrop = ImageOps.fit(stage, (512, 512), method=Image.Resampling.LANCZOS)
    base.alpha_composite(backdrop)
    overlay = Image.new('RGBA', (512, 512), (12, 20, 40, 145))
    base.alpha_composite(overlay)
    draw = ImageDraw.Draw(base)
    c1, c2, c3 = color_from_token(slug), color_from_token(slug, 1), color_from_token(slug, 2)
    draw.polygon([(0, 380), (245, 120), (512, 350), (512, 512), (0, 512)], fill=(*c1, 210))
    draw.ellipse((70, 62, 268, 260), fill=(*c2, 225), outline=(245, 248, 255, 220), width=8)
    draw.polygon([(295, 70), (445, 265), (255, 265)], fill=(*c3, 240), outline=(245, 248, 255, 215), width=8)
    draw.rounded_rectangle((24, 24, 488, 488), radius=24, outline=(245, 248, 255, 170), width=7)
    destination.parent.mkdir(parents=True, exist_ok=True)
    base.save(destination)


def build_title(slug: str, destination: Path) -> None:
    title = song_title(slug)
    canvas = Image.new('RGBA', (512, 128), (24, 33, 58, 255))
    draw = ImageDraw.Draw(canvas)
    c1, c2 = color_from_token(slug), color_from_token(slug, 1)
    draw.rectangle((0, 0, 512, 128), fill=(*c1, 245))
    draw.polygon([(0, 0), (190, 0), (90, 128), (0, 128)], fill=(*c2, 230))
    font_size = 32 if len(title) <= 22 else 23
    font = ImageFont.truetype(str(FONT), font_size)
    bbox = draw.textbbox((0, 0), title, font=font)
    text_w = bbox[2] - bbox[0]
    draw.text(((512 - text_w) / 2, 47), title, font=font, fill=(248, 250, 255, 255), stroke_width=2, stroke_fill=(18, 26, 48, 255))
    draw.rectangle((7, 7, 505, 121), outline=(248, 250, 255, 180), width=4)
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination)


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
    reports = []
    for mod in sorted((root / 'mods').glob('esperon-dano-*')):
        if not mod.is_dir():
            continue
        song_dirs = list((mod / 'data' / 'songs').glob('*'))
        if len(song_dirs) != 1:
            raise RuntimeError(f'Song directory ambiguous in {mod}')
        song = song_dirs[0].name
        album_id = f'esperon-{song}'
        art_asset = f'freeplay/albums/{album_id}-art'
        title_asset = f'freeplay/albums/{album_id}-title'
        art = mod / 'images' / f'{art_asset}.png'
        title = mod / 'images' / f'{title_asset}.png'
        build_art(mod, song, art)
        build_title(song, title)
        album_json = mod / 'data' / 'ui' / 'freeplay' / 'albums' / f'{album_id}.json'
        album_json.parent.mkdir(parents=True, exist_ok=True)
        album_json.write_text(json.dumps({
            'version': '1.0.3', 'name': song_title(song), 'artists': ['Esperón'],
            'albumArtAsset': art_asset, 'albumTitleAsset': title_asset,
            'albumTitleOffsets': [0, 0], 'albumTitleAnimations': [], 'albumOSTName': 'ESPERÓN'
        }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        metadata_path = song_dirs[0] / f'{song}-metadata.json'
        metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
        metadata['album'] = album_id
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        reports.append({'mod': mod.name, 'song': song, 'album': album_id, 'art': art.relative_to(mod).as_posix(), 'title': title.relative_to(mod).as_posix()})
    output = root / 'qa-lab' / 'session-30min' / 'freeplay-album-additions.json'
    output.write_text(json.dumps({'scope': 'FREEPLAY_ALBUM_ASSETS', 'count': len(reports), 'entries': reports}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'albums': len(reports), 'status': 'CREATED'}, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
