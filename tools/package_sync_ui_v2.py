#!/usr/bin/env python3
"""Versiona y empaqueta los mods sync-ui v2 sin ocultar validaciones manuales pendientes."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

VERSION = "2.0.0"


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    validation = json.loads((root / "artifacts" / "sync-ui-v2-validation.json").read_text(encoding="utf-8"))
    by_mod = {item["mod"]: item for item in validation["reports"]}
    packages = []
    for mod in sorted((root / "mods").glob("esperon-dano-*")):
        if not mod.is_dir():
            continue
        report = by_mod.get(mod.name, {})
        if report.get("status") != "PASS":
            raise RuntimeError(f"No se empaqueta {mod.name}: validación estática no aprobada")
        manifest_path = mod / "_polymod_meta.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["mod_version"] = VERSION
        manifest["description"] = "Mod V-Slice con flechas, HUD y animaciones vocales personalizadas; requiere Audio Sync Test y playtest móvil para confirmar sincronía."
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        song_dirs = list((mod / "data" / "songs").glob("*"))
        song = song_dirs[0].name
        brief_path = root / "visual-briefs" / f"{song}.json"
        brief = json.loads(brief_path.read_text(encoding="utf-8"))
        style = json.loads((song_dirs[0] / f"{song}-metadata.json").read_text(encoding="utf-8"))["playData"]["noteStyle"]
        brief["gameplay_visuals"] = {
            "note_style": style,
            "notes": "Cuatro direcciones, receptores y sostenidos geométricos transparentes derivados de la paleta de la canción.",
            "hud": "Juicios, combo, iconos y barra de vida temática vinculados al mod.",
            "vocal_animation": "Atlas Sparrow de 18 cuadros por personaje: idle, cuatro direcciones de canto y cuatro poses hold en secuencia multi-frame."
        }
        brief["sync_status"] = {
            "status": "REQUIRES_HUMAN_REVIEW",
            "basis": "Chart candidato generado desde actividad/onsets de audio y validación estática; no equivale a Audio Sync Test.",
            "warnings": report.get("warnings", [])
        }
        write_json(brief_path, brief)
        destination = root / "dist" / f"{mod.name}-v{VERSION}.zip"
        if destination.exists():
            destination.unlink()
        shutil.make_archive(str(destination.with_suffix("")), "zip", root_dir=mod.parent, base_dir=mod.name)
        packages.append({"mod": mod.name, "song": song, "zip": destination.relative_to(root).as_posix(), "version": VERSION, "static_validation": "PASS", "sync_status": "REQUIRES_HUMAN_REVIEW"})
    output = root / "reports" / "sync-ui-v2-manifest.json"
    write_json(output, {
        "version": VERSION,
        "packages": packages,
        "validation": "STATIC_PASS",
        "limitations": [
            "Los charts son candidatos y requieren Audio Sync Test del Chart Editor.",
            "19 canciones se analizaron por mezcla completa; su asignación vocal necesita revisión humana prioritaria.",
            "El playtest en FNF Mobile V-Slice 0.8.6 permanece pendiente."
        ]
    })
    print(json.dumps({"version": VERSION, "packages": len(packages)}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
