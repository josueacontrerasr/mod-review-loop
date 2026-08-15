#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import math
import wave
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]


def load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"__error__": str(exc)}


def sha256(p: Path):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_image(mod: Path, asset: str):
    if not isinstance(asset, str):
        return None
    if asset.startswith("shared:"):
        base = mod / "shared" / "images" / asset.removeprefix("shared:")
    elif asset.startswith(("characters/", "stages/", "notes/", "ui/")):
        base = mod / "shared" / "images" / asset
    else:
        base = mod / "images" / asset
    return base


def atlas_info(mod: Path, asset: str):
    base = resolve_image(mod, asset)
    if base is None:
        return {"asset": asset, "resolved": None, "png": False, "xml": False, "frames": [], "png_size": None, "xml_error": None}
    png, xml = base.with_suffix(".png"), base.with_suffix(".xml")
    frames = []
    xml_error = None
    if xml.is_file():
        try:
            frames = [n.attrib.get("name", "") for n in ET.parse(xml).getroot().findall(".//SubTexture")]
        except Exception as exc:
            xml_error = str(exc)
    png_size = None
    if png.is_file():
        try:
            with Image.open(png) as im:
                png_size = list(im.size)
        except Exception as exc:
            png_size = ["error", str(exc)]
    return {"asset": asset, "resolved": str(base.relative_to(mod)), "png": png.is_file(), "xml": xml.is_file(), "frames": frames, "frame_count": len(frames), "png_size": png_size, "xml_error": xml_error}


def note_style_summary(mod: Path, style_id: str):
    p = mod / "data" / "notestyles" / f"{style_id}.json"
    style = load(p)
    if "__error__" in style:
        return {"path": str(p.relative_to(mod)), "error": style["__error__"]}
    assets = style.get("assets", {})
    out = {"path": str(p.relative_to(mod)), "version": style.get("version"), "assets": {}}
    for group in ("note", "noteStrumline"):
        data = assets.get(group, {})
        atlas = atlas_info(mod, data.get("assetPath"))
        prefixes = {}
        for key, spec in (data.get("data") or {}).items():
            if isinstance(spec, dict):
                prefix = spec.get("prefix")
                prefixes[key] = {"prefix": prefix, "matches": [f for f in atlas["frames"] if f == prefix or f.startswith(str(prefix) + "0")]}
        out["assets"][group] = {"assetPath": data.get("assetPath"), "atlas": atlas, "prefixes": prefixes}
    return out


def one(song: str):
    mod = ROOT / "mods" / f"esperon-dano-{song}"
    result = {"song": song, "mod": str(mod), "issues": [], "status": "ERROR"}
    try:
        manifest = load(mod / "_polymod_meta.json")
        song_dir = next((mod / "data" / "songs").iterdir())
        meta = load(song_dir / f"{song}-metadata.json")
        chart = load(song_dir / f"{song}-chart.json")
        play = meta.get("playData", {})
        style_id = play.get("noteStyle")
        style = note_style_summary(mod, style_id)
        notes = chart.get("notes", {})
        note_summary = {}
        for diff in ("easy", "normal", "hard"):
            ns = notes.get(diff, [])
            times = [float(n.get("t", -1)) for n in ns]
            dirs = sorted(set(int(n.get("d", -1)) for n in ns))
            first_by_lane = {str(d): min((float(n.get("t", -1)) for n in ns if int(n.get("d", -1)) == d), default=None) for d in range(4, 8)}
            note_summary[diff] = {"count": len(ns), "first": min(times) if times else None, "first_10s": sum(t <= 10000 for t in times), "lanes": dirs, "first_by_lane": first_by_lane, "last": max(times) if times else None, "scrollSpeed": chart.get("scrollSpeed", {}).get(diff)}
            if not ns: result["issues"].append(f"empty_{diff}")
            if not all(4 <= d <= 7 for d in dirs): result["issues"].append(f"lane_domain_{diff}")
        inst = mod / "songs" / song / "Inst.ogg"
        voices = sorted((mod / "songs" / song).glob("Voices-*.ogg"))
        audio = {"inst": str(inst.relative_to(mod)), "inst_bytes": inst.stat().st_size if inst.is_file() else 0, "inst_sha256": sha256(inst) if inst.is_file() else None, "voices": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)} for p in voices]}
        style_issues = []
        for group in ("note", "noteStrumline"):
            g = style.get("assets", {}).get(group, {})
            a = g.get("atlas", {})
            if not a.get("png") or not a.get("xml") or a.get("xml_error"): style_issues.append(f"{group}_atlas")
            for key, spec in g.get("prefixes", {}).items():
                if not spec.get("matches"): style_issues.append(f"{group}_{key}_prefix")
        result.update({"status": "PASS" if not style_issues and not result["issues"] else "ERROR", "issues": result["issues"] + style_issues, "manifest": {"api_version": manifest.get("api_version"), "mod_version": manifest.get("mod_version")}, "metadata": {"version": meta.get("version"), "stage": play.get("stage"), "characters": play.get("characters"), "noteStyle": style_id, "album": play.get("album")}, "chart": {"version": chart.get("version"), "timeChanges": chart.get("timeChanges"), "notes": note_summary}, "note_style": style, "audio": audio})
    except Exception as exc:
        result["issues"].append(f"exception:{type(exc).__name__}:{exc}")
    return result


def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        rows = sorted(ex.map(one, SONGS), key=lambda r: r["song"])
    payload = {"version": "2.5.0-baseline", "status": "PASS" if all(r["status"] == "PASS" for r in rows) else "ERRORS_FOUND", "songs": len(rows), "parallel_workers": 20, "rows": rows}
    out = ROOT / "qa-lab" / "rebuild-v250" / "parallel-runtime-baseline-v250.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "songs": payload["songs"], "errors": sum(r["status"] != "PASS" for r in rows), "output": str(out)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
