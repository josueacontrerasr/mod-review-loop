#!/usr/bin/env python3
"""Generación y auditoría reproducible de mods FNF Mobile V-Slice 0.8.6.

La herramienta crea arte original geométrico y un chart de referencia. No declara
sincronización musical aprobada ni modifica offsets/notas durante la revisión.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
AUDIO_EXTENSIONS = {".m4a", ".mp3", ".ogg", ".wav", ".flac"}
POSES = ("Idle", "Left", "Down", "Up", "Right")
API_VERSION = "0.8.6"
METADATA_VERSION = "2.2.4"
CHART_VERSION = "2.0.0"

THEMES = {
    "solare": ("solar nocturno", (244, 152, 42), (40, 76, 128), (20, 24, 50)),
    "arcoloria": ("jardín cromático", (233, 96, 169), (75, 207, 186), (40, 32, 72)),
    "cortamos": ("cine fragmentado", (221, 88, 73), (82, 154, 194), (36, 32, 48)),
    "dano": ("neón melancólico", (210, 69, 105), (85, 138, 194), (28, 24, 42)),
    "dias-magicos": ("amanecer mágico", (255, 205, 89), (123, 180, 255), (52, 74, 128)),
    "eclipsis": ("eclipse violeta", (144, 96, 209), (247, 169, 79), (22, 21, 45)),
    "fango": ("pantano luminoso", (111, 151, 72), (205, 168, 76), (40, 61, 47)),
    "luma": ("luz prismática", (108, 235, 231), (249, 152, 222), (42, 58, 112)),
    "maraton-de-peliculas": ("maratón cinematográfico", (229, 72, 76), (245, 199, 85), (47, 40, 76)),
    "meteora": ("lluvia de meteoros", (255, 117, 70), (92, 101, 228), (21, 27, 67)),
    "mi-hogar": ("hogar cálido", (238, 143, 77), (127, 190, 162), (83, 60, 55)),
    "nubia": ("nubes azuladas", (112, 175, 232), (198, 183, 245), (42, 65, 112)),
    "peligrosa": ("peligro carmesí", (230, 68, 74), (255, 176, 65), (51, 23, 41)),
    "rompecabezas": ("rompecabezas eléctrico", (68, 193, 221), (249, 178, 61), (55, 44, 112)),
    "tristella": ("triple estrella", (255, 205, 72), (126, 94, 214), (35, 30, 72)),
    "dealer-de-nostalgia": ("nostalgia analógica", (213, 116, 109), (98, 167, 171), (65, 49, 73)),
    "volver-a-vernos": ("reencuentro crepuscular", (239, 124, 176), (111, 161, 229), (54, 48, 93)),
}


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=check)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    normalized = re.sub(r"\b(esperon|letra|audio)\b", " ", normalized)
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized or "cancion"


def visible_title(path: Path) -> str:
    title = path.stem.replace("_", " ")
    title = re.sub(r"^Esper[oó]n\s+", "", title, flags=re.I)
    title = re.sub(r"\s*\(?\s*(LETRA|Letra|Audio)\s*\)?\s*", " ", title, flags=re.I)
    title = re.sub(r"\s+", " ", title).strip(" -_")
    return title or path.stem


def discover_audios(root: Path) -> list[Path]:
    return sorted(path for path in root.iterdir() if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS)


def theme_for(slug: str) -> tuple[str, tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    for token, theme in THEMES.items():
        if token in slug:
            return theme
    seed = int(hashlib.sha256(slug.encode("utf-8")).hexdigest()[:8], 16)
    hue = seed % 360
    def hsl(h: float, s: float, l: float) -> tuple[int, int, int]:
        import colorsys
        r, g, b = colorsys.hls_to_rgb(h / 360, l, s)
        return round(r * 255), round(g * 255), round(b * 255)
    return "abstracción geométrica", hsl(hue, 0.72, 0.57), hsl((hue + 128) % 360, 0.65, 0.62), hsl((hue + 225) % 360, 0.45, 0.18)


def mix(a: tuple[int, int, int], b: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
    return tuple(round(a[i] * (1 - ratio) + b[i] * ratio) for i in range(3))


def draw_character_sheet(path: Path, primary: tuple[int, int, int], secondary: tuple[int, int, int], *, rival: bool) -> None:
    frame_w, frame_h = 256, 384
    sheet = Image.new("RGBA", (frame_w * len(POSES), frame_h), (0, 0, 0, 0))
    for index, pose in enumerate(POSES):
        image = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        cx, cy = 128, 135
        lean = {"Idle": 0, "Left": -18, "Down": 0, "Up": 0, "Right": 18}[pose]
        lift = {"Idle": 0, "Left": 6, "Down": 24, "Up": -28, "Right": 6}[pose]
        cx += lean; cy += lift
        outline = (24, 24, 38, 255)
        draw.ellipse((cx - 55, cy - 55, cx + 55, cy + 55), fill=primary + (255,), outline=outline, width=8)
        draw.rectangle((cx - 40, cy + 50, cx + 40, cy + 170), fill=secondary + (255,), outline=outline, width=8)
        draw.polygon([(cx - 40, cy + 70), (cx - 92, cy + 128), (cx - 40, cy + 150)], fill=primary + (255,), outline=outline)
        draw.polygon([(cx + 40, cy + 70), (cx + 92, cy + 128), (cx + 40, cy + 150)], fill=primary + (255,), outline=outline)
        if pose == "Left":
            draw.polygon([(cx - 40, cy + 85), (cx - 120, cy + 45), (cx - 80, cy + 130)], fill=primary + (255,), outline=outline)
        elif pose == "Right":
            draw.polygon([(cx + 40, cy + 85), (cx + 120, cy + 45), (cx + 80, cy + 130)], fill=primary + (255,), outline=outline)
        elif pose == "Up":
            draw.polygon([(cx, cy + 70), (cx + 8, cy - 98), (cx + 60, cy + 70)], fill=primary + (255,), outline=outline)
        elif pose == "Down":
            draw.polygon([(cx - 60, cy + 130), (cx, cy + 220), (cx + 60, cy + 130)], fill=primary + (255,), outline=outline)
        eye = secondary if not rival else primary
        draw.ellipse((cx - 27, cy - 12, cx - 10, cy + 5), fill=eye + (255,))
        draw.ellipse((cx + 10, cy - 12, cx + 27, cy + 5), fill=eye + (255,))
        draw.rectangle((cx - 10, cy + 20, cx + 10, cy + 27), fill=outline)
        sheet.alpha_composite(image, (index * frame_w, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, optimize=True)


def write_sparrow_xml(path: Path, png_name: str) -> None:
    root = ET.Element("TextureAtlas", {"imagePath": png_name})
    for index, pose in enumerate(POSES):
        ET.SubElement(root, "SubTexture", {"name": pose, "x": str(index * 256), "y": "0", "width": "256", "height": "384", "frameX": "0", "frameY": "0", "frameWidth": "256", "frameHeight": "384"})
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def draw_stage(path: Path, primary: tuple[int, int, int], secondary: tuple[int, int, int], dark: tuple[int, int, int]) -> None:
    width, height = 1280, 720
    image = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        ratio = y / max(height - 1, 1)
        color = mix(primary, dark, ratio)
        draw.line((0, y, width, y), fill=color + (255,))
    for index in range(14):
        x = (index * 97 + primary[0] * 3) % width
        radius = 18 + (index % 5) * 10
        y = 80 + (index * 47) % 330
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=secondary + (70,), outline=primary + (160,), width=3)
    draw.rectangle((0, 560, width, height), fill=dark + (220,))
    for x in range(-20, width + 50, 120):
        draw.polygon([(x, 560), (x + 100, 560), (x + 50, 420)], fill=secondary + (150,), outline=primary + (200,))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)


def draw_icon(path: Path, primary: tuple[int, int, int], secondary: tuple[int, int, int]) -> None:
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((24, 24, 232, 232), fill=primary + (255,), outline=(24, 24, 38, 255), width=12)
    draw.polygon([(128, 48), (198, 198), (58, 198)], fill=secondary + (255,), outline=(24, 24, 38, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)


def probe_duration(audio: Path) -> float:
    result = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nokey=1:noprint_wrappers=1", str(audio)], check=False)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def estimate_bpm(audio: Path) -> float:
    try:
        import librosa  # type: ignore
        signal, rate = librosa.load(audio, sr=22050, mono=True, duration=120)
        tempo, _ = librosa.beat.beat_track(y=signal, sr=rate)
        value = float(tempo[0] if hasattr(tempo, "__len__") else tempo)
        return round(max(60.0, min(value, 220.0)), 3)
    except Exception:
        return 120.0


def build_chart(duration_ms: float, bpm: float) -> dict[str, Any]:
    beat = 60000.0 / bpm
    start = beat * 16
    end = max(start, duration_ms - beat * 2)
    notes: dict[str, list[dict[str, Any]]] = {"easy": [], "normal": [], "hard": []}
    current = start
    counter = 0
    while current < end:
        owner = 4 if (counter // 16) % 2 == 0 else 0
        lane = counter % 4
        if counter % 4 == 0:
            notes["easy"].append({"t": round(current, 3), "d": owner + lane})
        notes["normal"].append({"t": round(current, 3), "d": owner + lane})
        notes["hard"].append({"t": round(current, 3), "d": owner + lane})
        if counter % 2 == 0 and current + beat / 2 < end:
            notes["hard"].append({"t": round(current + beat / 2, 3), "d": owner + ((lane + 2) % 4)})
        if counter % 32 == 31 and current + beat * 2 < end:
            notes["normal"][-1]["l"] = round(beat, 3)
            notes["hard"][-1]["l"] = round(beat, 3)
        current += beat
        counter += 1
    for items in notes.values():
        items.sort(key=lambda item: (item["t"], item["d"]))
    events = []
    for section in range(0, max(1, counter // 16), 1):
        time = start + section * 16 * beat
        if time < end:
            events.append({"t": round(time, 3), "e": "FocusCamera", "v": {"char": 1 if section % 2 == 0 else 0}})
    return {"version": CHART_VERSION, "scrollSpeed": {"easy": 0.9, "normal": 1.0, "hard": 1.12}, "events": events, "notes": notes, "generatedBy": "Geometric V-Slice pipeline; requires Audio Sync Test"}


def character_data(name: str, asset: str, flip: bool) -> dict[str, Any]:
    return {"version": "1.0.2", "name": name, "renderType": "sparrow", "assetPath": asset, "flipX": flip, "offsets": [0, 0], "cameraOffsets": [0, 0], "animations": [{"name": "idle", "prefix": "Idle"}, {"name": "singLEFT", "prefix": "Left"}, {"name": "singDOWN", "prefix": "Down"}, {"name": "singUP", "prefix": "Up"}, {"name": "singRIGHT", "prefix": "Right"}]}


def build_mod(audio: Path, output_root: Path) -> Path:
    title = visible_title(audio)
    song_slug = slugify(title)
    mod_id = f"esperon-dano-{song_slug}"
    player_id = f"esperon-{song_slug}"
    rival_id = f"rival-{song_slug}"
    stage_id = f"escenario-{song_slug}"
    theme, primary, secondary, dark = theme_for(song_slug)
    mod = output_root / mod_id
    if mod.exists():
        shutil.rmtree(mod)
    (mod / "data/songs" / song_slug).mkdir(parents=True)
    (mod / "data/characters").mkdir(parents=True)
    (mod / "data/stages").mkdir(parents=True)
    (mod / "images/characters").mkdir(parents=True)
    (mod / "images/stages").mkdir(parents=True)
    (mod / "images/icons").mkdir(parents=True)
    (mod / "songs" / song_slug).mkdir(parents=True)

    duration = probe_duration(audio)
    bpm = estimate_bpm(audio)
    inst = mod / "songs" / song_slug / "Inst.ogg"
    converted = run(["ffmpeg", "-y", "-v", "error", "-i", str(audio), "-vn", "-c:a", "libvorbis", "-q:a", "4", str(inst)], check=False)
    if converted.returncode != 0:
        raise RuntimeError(f"No se pudo convertir {audio.name}: {converted.stderr}")
    final_duration = probe_duration(inst)

    write_json(mod / "_polymod_meta.json", {"title": f"Esperón — {title}", "description": f"Mod V-Slice candidato para {title}; requiere Audio Sync Test y playtest móvil.", "contributors": [{"name": "Manus AI", "role": "Producción técnica y assets geométricos"}], "api_version": API_VERSION, "mod_version": "1.0.0", "license": "Custom — see LICENSE.txt"})
    metadata = {"version": METADATA_VERSION, "songName": title, "artist": "Esperón", "charter": "Manus AI — chart de referencia", "offsets": {}, "playData": {"difficulties": ["easy", "normal", "hard"], "characters": {"player": player_id, "opponent": rival_id, "playerVocals": [], "opponentVocals": []}, "stage": stage_id, "noteStyle": "funkin", "ratings": {"easy": 0, "normal": 1, "hard": 2}}, "timeChanges": [{"t": 0, "b": 0, "bpm": bpm, "bt": [4, 4, 4, 4]}], "generatedBy": "Friday Night Funkin' - 0.8.6"}
    write_json(mod / "data/songs" / song_slug / f"{song_slug}-metadata.json", metadata)
    write_json(mod / "data/songs" / song_slug / f"{song_slug}-chart.json", build_chart(final_duration * 1000, bpm))
    write_json(mod / "data/characters" / f"{player_id}.json", character_data(f"Esperón {title}", f"shared:characters/{player_id}", True))
    write_json(mod / "data/characters" / f"{rival_id}.json", character_data(f"Rival {title}", f"shared:characters/{rival_id}", False))
    write_json(mod / "data/stages" / f"{stage_id}.json", {"version": "1.0.1", "name": f"Escenario {title}", "cameraZoom": 0.92, "props": [{"assetPath": f"shared:stages/{stage_id}", "position": [-140, -75], "scale": [1.15, 1.15], "scroll": [0.85, 0.85], "zIndex": -10, "alpha": 1.0}]})

    player_png = mod / "images/characters" / f"{player_id}.png"
    rival_png = mod / "images/characters" / f"{rival_id}.png"
    draw_character_sheet(player_png, primary, secondary, rival=False)
    draw_character_sheet(rival_png, secondary, primary, rival=True)
    write_sparrow_xml(player_png.with_suffix(".xml"), player_png.name)
    write_sparrow_xml(rival_png.with_suffix(".xml"), rival_png.name)
    draw_stage(mod / "images/stages" / f"{stage_id}.png", primary, secondary, dark)
    draw_icon(mod / "images/icons" / f"{player_id}.png", primary, secondary)
    draw_icon(mod / "images/icons" / f"{rival_id}.png", secondary, primary)

    brief = {"song": title, "song_slug": song_slug, "theme": theme, "palette": {"primary": "#%02X%02X%02X" % primary, "secondary": "#%02X%02X%02X" % secondary, "dark": "#%02X%02X%02X" % dark}, "characters": {"player": player_id, "rival": rival_id, "style": "Formas geométricas originales: cabeza circular, torso rectangular y extremidades triangulares."}, "stage": {"id": stage_id, "style": "Fondo degradado y estructuras geométricas estáticas, sin shaders ni partículas."}, "status": "CANDIDATE_REQUIRES_AUDIO_SYNC_TEST"}
    write_json(ROOT / "visual-briefs" / f"{song_slug}.json", brief)
    evidence = {"source": str(audio.relative_to(ROOT)), "source_sha256": sha256(audio), "instrumental": str(inst.relative_to(mod)), "instrumental_sha256": sha256(inst), "source_duration_seconds": duration, "instrumental_duration_seconds": final_duration, "bpm_candidate": bpm, "status": "CANDIDATE_REQUIRES_AUDIO_SYNC_TEST"}
    write_json(mod / "audio-evidence.json", evidence)
    write_json(mod / "sync-report.json", {"scope": "STATIC_GRID_COHERENCE_ONLY", "review_basis": "AUTO_GENERATED_REFERENCE_CHART", "status": "REQUIRES_MANUAL_REVIEW", "limitations": ["El BPM y las notas son candidatos automatizados.", "Audio Sync Test y playtest móvil son obligatorios antes de declarar sincronización."]})
    (mod / "CREDITS.txt").write_text(f"MOD: Esperón — {title}\nVERSION: 1.0.0\nASSETS: personajes y escenario geométricos originales generados para {title}.\nAUDIO: archivo fuente del repositorio; confirmar derechos antes de distribución pública.\n", encoding="utf-8")
    (mod / "LICENSE.txt").write_text("Los assets geométricos y scripts de este mod pueden reutilizarse con atribución a Manus AI. El audio permanece sujeto a los derechos de sus titulares; no redistribuir sin autorización.\n", encoding="utf-8")
    (mod / "INSTALACION_MOVIL.txt").write_text(f"Extraer la carpeta {mod_id} directamente en la carpeta mods de FNF Mobile V-Slice. Antes de jugar, abrir {title} en Chart Editor y ejecutar Audio Sync Test.\n", encoding="utf-8")
    return mod


def validate_mod(mod: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    def read_json(path: Path) -> dict[str, Any] | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"JSON inválido: {path.relative_to(mod)} ({exc})")
            return None
    manifest = read_json(mod / "_polymod_meta.json")
    if not manifest or manifest.get("api_version") != API_VERSION:
        errors.append("Manifiesto ausente o api_version incorrecta")
    song_dirs = list((mod / "data/songs").glob("*")) if (mod / "data/songs").exists() else []
    if len(song_dirs) != 1:
        errors.append("El mod debe contener exactamente una carpeta de canción")
    else:
        song = song_dirs[0].name
        metadata = read_json(song_dirs[0] / f"{song}-metadata.json")
        chart = read_json(song_dirs[0] / f"{song}-chart.json")
        if not metadata or metadata.get("version") != METADATA_VERSION:
            errors.append("Metadata V-Slice inválida")
        if not chart or chart.get("version") != CHART_VERSION:
            errors.append("Chart V-Slice inválido")
        if metadata:
            chars = metadata.get("playData", {}).get("characters", {})
            stage = metadata.get("playData", {}).get("stage")
            for char in (chars.get("player"), chars.get("opponent")):
                if not isinstance(char, str) or not (mod / "data/characters" / f"{char}.json").is_file():
                    errors.append(f"Personaje no resuelto: {char!r}")
            if not isinstance(stage, str) or not (mod / "data/stages" / f"{stage}.json").is_file():
                errors.append(f"Escenario no resuelto: {stage!r}")
        if chart:
            for difficulty, notes in chart.get("notes", {}).items():
                previous = -1.0
                for index, note in enumerate(notes):
                    if not isinstance(note, dict) or not isinstance(note.get("t"), (int, float)) or not isinstance(note.get("d"), int):
                        errors.append(f"Nota inválida {difficulty}[{index}]")
                        continue
                    if note["t"] < previous or not 0 <= note["d"] <= 7:
                        errors.append(f"Nota inválida u desordenada {difficulty}[{index}]")
                    previous = note["t"]
                    if "l" in note and (not isinstance(note["l"], (int, float)) or note["l"] <= 0):
                        errors.append(f"Hold inválido {difficulty}[{index}]")
        if not (mod / "songs" / song / "Inst.ogg").is_file():
            errors.append("Inst.ogg ausente")
    for xml_path in mod.rglob("*.xml"):
        try:
            root = ET.parse(xml_path).getroot()
            names = {node.attrib.get("name") for node in root.findall("SubTexture")}
            is_character_atlas = xml_path.parent == mod / "images" / "characters"
            valid_names = set(POSES).issubset(names) if is_character_atlas else bool(names)
            if root.tag != "TextureAtlas" or not valid_names or not xml_path.with_suffix(".png").is_file():
                errors.append(f"Atlas inválido: {xml_path.relative_to(mod)}")
        except Exception as exc:
            errors.append(f"XML inválido: {xml_path.relative_to(mod)} ({exc})")
    for required in ("CREDITS.txt", "LICENSE.txt", "INSTALACION_MOVIL.txt", "audio-evidence.json", "sync-report.json"):
        if not (mod / required).is_file():
            errors.append(f"Documento requerido ausente: {required}")
    sync = read_json(mod / "sync-report.json")
    if sync and sync.get("status") != "PASS":
        warnings.append("REQUIERE_VALIDACION_MANUAL: Audio Sync Test y playtest móvil pendientes")
    return {"mod": mod.name, "status": "PASS" if not errors else "ERROR_ESTRUCTURAL", "errors": errors, "warnings": warnings}


def package_mod(mod: Path, dist: Path) -> Path:
    dist.mkdir(parents=True, exist_ok=True)
    archive = dist / f"{mod.name}-v1.0.0.zip"
    if archive.exists():
        archive.unlink()
    shutil.make_archive(str(archive.with_suffix("")), "zip", root_dir=mod.parent, base_dir=mod.name)
    return archive


def command_build(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    output = root / "mods"
    audio_files = [root / args.audio] if args.audio else discover_audios(root)
    if not audio_files:
        print("No se encontraron audios en la raíz.", file=sys.stderr)
        return 2
    manifests = []
    for audio in audio_files:
        mod = build_mod(audio, output)
        report = validate_mod(mod)
        if report["status"] != "PASS":
            raise RuntimeError(json.dumps(report, ensure_ascii=False))
        archive = package_mod(mod, root / "dist")
        manifests.append({"audio": audio.name, "mod": mod.name, "zip": archive.relative_to(root).as_posix(), "report": report})
        print(json.dumps(manifests[-1], ensure_ascii=False))
    if not args.no_manifest:
        write_json(root / "reports" / "build-manifest.json", {"generated_at": datetime.utcnow().isoformat() + "Z", "mods": manifests})
    return 0


def command_review(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    reports = []
    for mod in sorted((root / "mods").glob("esperon-dano-*")):
        if mod.is_dir():
            reports.append(validate_mod(mod))
    output = root / (args.output or "artifacts/reports")
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "review-report.json", {"generated_at": datetime.utcnow().isoformat() + "Z", "reports": reports, "changes_applied": []})
    print(json.dumps({"mods": len(reports), "errors": sum(len(item["errors"]) for item in reports), "changes_applied": 0}, ensure_ascii=False))
    return 0 if all(item["status"] == "PASS" for item in reports) else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--root", default=str(ROOT))
    build.add_argument("--audio", help="Ruta relativa de un único audio para procesamiento paralelo.")
    build.add_argument("--no-manifest", action="store_true", help="No escribir el manifiesto global; usar en trabajadores paralelos.")
    build.set_defaults(handler=command_build)
    review = sub.add_parser("review")
    review.add_argument("--root", default=str(ROOT))
    review.add_argument("--output")
    review.set_defaults(handler=command_review)
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
