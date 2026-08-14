#!/usr/bin/env python3
"""Añade una recolorización de barra de vida por canción sin modificar música ni chart."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.2.0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def hex_color(value: str) -> str:
    value = value.removeprefix("#").upper()
    if not re.fullmatch(r"[0-9A-F]{6}", value):
        raise ValueError(f"Color inválido: {value}")
    return f"0xFF{value}"


def class_name(slug: str) -> str:
    return "Esperon" + "".join(piece.capitalize() for piece in slug.split("-")) + "HudV2"


def healthbar_script(class_id: str, visible_name: str, player_id: str, opponent_color: str, player_color: str) -> str:
    return f'''import funkin.modding.module.Module;
import funkin.play.PlayState;

/**
 * HUD visual V2 para {visible_name}.
 * Solo recoloriza la barra de vida al inicio del conteo.
 * No modifica audio, BPM, offsets, chart, notas ni eventos musicales.
 */
class {class_id} extends Module
{{
  function new()
  {{
    super("Esperón HUD — {visible_name}", 1, {{state: PlayState}});
  }}

  override function onCountdownStart(event)
  {{
    super.onCountdownStart(event);
    if (PlayState.instance == null || PlayState.instance.healthBar == null) return;
    if (PlayState.instance.iconP1 == null) return;
    if (PlayState.instance.iconP1.characterId != "{player_id}") return;
    PlayState.instance.healthBar.createFilledBar({opponent_color}, {player_color});
    PlayState.instance.healthBar.updateBar();
  }}
}}
'''


def draw_healthbar_preview(path: Path, primary: str, secondary: str, dark: str) -> None:
    p = tuple(int(primary.removeprefix("#")[i:i+2], 16) for i in (0, 2, 4))
    s = tuple(int(secondary.removeprefix("#")[i:i+2], 16) for i in (0, 2, 4))
    d = tuple(int(dark.removeprefix("#")[i:i+2], 16) for i in (0, 2, 4))
    width, height = 640, 110
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, width - 8, height - 8), radius=36, fill=d + (245,), outline=(18, 20, 32, 255), width=7)
    draw.rounded_rectangle((18, 18, width // 2, height - 18), radius=26, fill=s + (255,))
    draw.rounded_rectangle((width // 2, 18, width - 18, height - 18), radius=26, fill=p + (255,))
    draw.line((width // 2, 22, width // 2, height - 22), fill=(18, 20, 32, 255), width=5)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)


def apply(mod: Path) -> Path:
    slug = mod.name.removeprefix("esperon-dano-")
    metadata_path = next((mod / "data/songs").glob("*/*-metadata.json"))
    chart_path = next((mod / "data/songs").glob("*/*-chart.json"))
    inst_path = next((mod / "songs").rglob("Inst.ogg"))
    before = {"chart_sha256": sha256(chart_path), "inst_sha256": sha256(inst_path)}
    metadata = read_json(metadata_path)
    title = str(metadata["songName"])
    player_id = str(metadata["playData"]["characters"]["player"])
    brief_path = ROOT / "visual-briefs" / f"{slug}.json"
    brief = read_json(brief_path)
    palette = brief["palette"]
    primary = hex_color(palette["primary"])
    secondary = hex_color(palette["secondary"])
    class_id = class_name(slug)
    script_path = mod / "scripts" / f"{class_id}.hxc"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(healthbar_script(class_id, title, player_id, secondary, primary), encoding="utf-8")
    style_id = f"esperon-{slug}-notes"
    preview = mod / "shared/images/ui" / style_id / "healthbar-theme.png"
    draw_healthbar_preview(preview, palette["primary"], palette["secondary"], palette["dark"])
    manifest_path = mod / "_polymod_meta.json"
    manifest = read_json(manifest_path)
    manifest["mod_version"] = VERSION
    manifest["description"] = f"Mod V-Slice candidato para {title}; HUD, note style y flechas geométricas V2. Requiere Audio Sync Test y playtest móvil."
    write_json(manifest_path, manifest)
    song_id = chart_path.parent.name
    integrity_path = ROOT / "qa-lab" / "rebuild-v220" / "evidence" / song_id / "visual-v2-integrity.json"
    if not integrity_path.is_file():
        integrity_path = mod / "visual-v2-integrity.json"
    integrity = read_json(integrity_path)
    after = {"chart_sha256": sha256(chart_path), "inst_sha256": sha256(inst_path)}
    if before != after:
        raise RuntimeError(f"Integridad musical violada: {mod.name}")
    integrity["healthbar_v2"] = {
        "script": script_path.relative_to(mod).as_posix(),
        "class": class_id,
        "player_character_id": player_id,
        "opponent_color": secondary,
        "player_color": primary,
        "preview": preview.relative_to(mod).as_posix(),
        "status": "PASS_VISUAL_ONLY",
    }
    integrity["protected_after"] = after
    write_json(integrity_path, integrity)
    hud = brief.setdefault("visual_system_v2", {}).setdefault("hud", {})
    hud["health_bar"] = {
        "implementation": "Módulo HScript de inicialización única: createFilledBar(opponentColor, playerColor) y updateBar().",
        "script": script_path.relative_to(mod).as_posix(),
        "preview": preview.relative_to(mod).as_posix(),
        "opponent_color": secondary,
        "player_color": primary,
        "no_per_frame_updates": True,
        "status": "INTEGRATED_PENDING_MOBILE_PLAYTEST",
    }
    write_json(brief_path, brief)
    archive = ROOT / "dist" / f"{mod.name}-v{VERSION}.zip"
    if archive.exists():
        archive.unlink()
    shutil.make_archive(str(archive.with_suffix("")), "zip", root_dir=mod.parent, base_dir=mod.name)
    return archive


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mod", required=True)
    args = parser.parse_args()
    mod = ROOT / "mods" / args.mod
    if not mod.is_dir():
        raise SystemExit(f"Mod no encontrado: {mod}")
    archive = apply(mod)
    print(json.dumps({"mod": mod.name, "archive": archive.relative_to(ROOT).as_posix(), "status": "HEALTHBAR_V2_CREATED"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
