#!/usr/bin/env python3
from __future__ import annotations

import colorsys
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path('/home/ubuntu/mod-review-loop-production')
SOURCE_ROOT = ROOT / 'mods'
FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT_REGULAR = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def palette(song: str) -> tuple[str, str, str, str]:
    digest = hashlib.sha256(song.encode('utf-8')).digest()
    hue = int.from_bytes(digest[:2], 'big') / 65535.0
    colors = []
    for sat, light in ((0.70, 0.48), (0.78, 0.62), (0.55, 0.27), (0.35, 0.90)):
        r, g, b = colorsys.hls_to_rgb(hue, light, sat)
        colors.append('#%02X%02X%02X' % (round(r * 255), round(g * 255), round(b * 255)))
        hue = (hue + 0.09) % 1.0
    return tuple(colors)  # type: ignore[return-value]


def rgb(hex_color: str) -> tuple[int, int, int, int]:
    value = hex_color.lstrip('#')
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), 255


def make_title(path: Path, title: str, colors: tuple[str, str, str, str]) -> None:
    image = Image.new('RGBA', (900, 220), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font_size = 76 if len(title) <= 14 else 58 if len(title) <= 22 else 42
    font = ImageFont.truetype(FONT_BOLD, font_size)
    text = title.upper()
    box = draw.textbbox((0, 0), text, font=font, stroke_width=0)
    x = max(20, (900 - (box[2] - box[0])) // 2)
    y = max(25, (220 - (box[3] - box[1])) // 2 - 8)
    draw.text((x + 6, y + 8), text, font=font, fill=(0, 0, 0, 170), stroke_width=7, stroke_fill=(0, 0, 0, 150))
    draw.text((x, y), text, font=font, fill=rgb(colors[1]), stroke_width=3, stroke_fill=rgb(colors[2]))
    image.save(path)


def make_prop(path: Path, song: str, colors: tuple[str, str, str, str], player: bool) -> None:
    image = Image.new('RGBA', (320, 360), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    primary = rgb(colors[0] if player else colors[1])
    secondary = rgb(colors[1] if player else colors[0])
    dark = rgb(colors[2])
    accent = rgb(colors[3])
    cx = 160
    # Static geometric prop: LevelProp loads it with Paths.image when animations=[] .
    draw.ellipse((54, 34, 266, 246), fill=dark, outline=accent, width=8)
    if player:
        draw.polygon([(72, 70), (112, 12), (142, 76)], fill=primary, outline=accent)
        draw.polygon([(248, 70), (208, 12), (178, 76)], fill=primary, outline=accent)
    else:
        draw.polygon([(66, 78), (78, 6), (132, 60)], fill=primary, outline=accent)
        draw.polygon([(254, 78), (242, 6), (188, 60)], fill=primary, outline=accent)
    eye_y = 118
    draw.ellipse((94, eye_y, 132, eye_y + 44), fill=accent)
    draw.ellipse((188, eye_y, 226, eye_y + 44), fill=accent)
    draw.ellipse((107, eye_y + 14, 119, eye_y + 26), fill=dark)
    draw.ellipse((201, eye_y + 14, 213, eye_y + 26), fill=dark)
    if player:
        draw.arc((105, 148, 215, 218), start=10, end=170, fill=secondary, width=10)
    else:
        draw.line((105, 188, 215, 188), fill=secondary, width=10)
    draw.polygon([(95, 232), (225, 232), (278, 350), (42, 350)], fill=primary, outline=accent)
    draw.line((160, 244, 160, 342), fill=secondary, width=8)
    label = 'P' if player else 'R'
    font = ImageFont.truetype(FONT_BOLD, 42)
    label_box = draw.textbbox((0, 0), label, font=font)
    draw.text(((320 - (label_box[2] - label_box[0])) // 2, 270), label, font=font, fill=accent)
    image.save(path)


def update_mod(mod: Path) -> dict:
    songs = sorted(path for path in (mod / 'data' / 'songs').glob('*') if path.is_dir())
    if len(songs) != 1:
        raise RuntimeError(f'{mod.name}: song directories={len(songs)}')
    song_dir = songs[0]
    song = song_dir.name
    metadata_path = song_dir / f'{song}-metadata.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    play = metadata.setdefault('playData', {})
    top_album = metadata.pop('album', None)
    if top_album and not play.get('album'):
        play['album'] = top_album
    play.setdefault('songVariations', [])
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    level_id = f'esperon-{song}'
    colors = palette(song)
    story_root = mod / 'images' / 'storymenu'
    props_root = story_root / 'props'
    props_root.mkdir(parents=True, exist_ok=True)
    make_title(story_root / f'{level_id}.png', metadata.get('songName', song), colors)
    make_prop(props_root / f'{level_id}-player.png', song, colors, True)
    make_prop(props_root / f'{level_id}-opponent.png', song, colors, False)

    display_name = metadata.get('songName', song.replace('-', ' ').title())
    level = {
        'version': '1.0.2',
        'name': f'ESPERÓN — {display_name}',
        'capsule': {'name': display_name, 'offsets': [0, 0]},
        'titleAsset': f'storymenu/{level_id}',
        'props': [
            {
                'assetPath': f'storymenu/props/{level_id}-opponent',
                'scale': 0.72,
                'danceEvery': 2,
                'offsets': [40, 70],
                'animations': [],
            },
            {
                'assetPath': f'storymenu/props/{level_id}-player',
                'scale': 0.72,
                'danceEvery': 2,
                'offsets': [190, 70],
                'animations': [],
            },
        ],
        'visible': True,
        'songs': [song],
        'background': colors[2],
    }
    level_path = mod / 'data' / 'levels' / f'{level_id}.json'
    level_path.parent.mkdir(parents=True, exist_ok=True)
    level_path.write_text(json.dumps(level, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {'mod': mod.name, 'song': song, 'level': level_id, 'album': play.get('album'), 'status': 'UPDATED'}


def main() -> int:
    reports = [update_mod(mod) for mod in sorted(SOURCE_ROOT.glob('esperon-dano-*')) if mod.is_dir()]
    output = ROOT / 'qa-lab/wide-research-v212/discovery-repair-report.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'status': 'PASS' if len(reports) == 20 else 'ERROR', 'updated': len(reports), 'reports': reports}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'PASS' if len(reports) == 20 else 'ERROR', 'updated': len(reports)}, ensure_ascii=False))
    return 0 if len(reports) == 20 else 1


if __name__ == '__main__':
    raise SystemExit(main())
