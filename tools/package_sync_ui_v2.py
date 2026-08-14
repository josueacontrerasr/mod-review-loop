#!/usr/bin/env python3
"""Versiona y empaqueta los mods sync-ui v2 sin ocultar validaciones manuales pendientes."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

VERSION = "2.1.0"


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    final_static_path = root / "qa-lab" / "session-30min" / "final-vslice-086-static.json"
    if not final_static_path.is_file():
        raise RuntimeError("Falta la verificación final V-Slice 0.8.6; ejecútala antes de empaquetar")
    final_static = json.loads(final_static_path.read_text(encoding="utf-8"))
    if final_static.get("status") != "PASS" or final_static.get("mods") != 20 or final_static.get("passed") != 20:
        raise RuntimeError("La verificación final V-Slice 0.8.6 no aprobó los 20 mods")
    legacy_validation_path = root / "artifacts" / "sync-ui-v2-validation.json"
    validation = json.loads(legacy_validation_path.read_text(encoding="utf-8")) if legacy_validation_path.is_file() else {"reports": []}
    by_mod = {item["mod"]: item for item in validation["reports"]}
    packages = []
    for mod in sorted((root / "mods").glob("esperon-dano-*")):
        if not mod.is_dir():
            continue
        report = by_mod.get(mod.name, {})
        if report and report.get("status") != "PASS":
            raise RuntimeError(f"No se empaqueta {mod.name}: validación estática histórica no aprobada")
        manifest_path = mod / "_polymod_meta.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["mod_version"] = VERSION
        manifest["description"] = "Mod V-Slice 0.8.6 con HUD, flechas, animaciones vocales y carátula Freeplay personalizada; requiere Audio Sync Test y playtest móvil para confirmar sincronía."
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
            "vocal_animation": "Atlas Sparrow de 18 cuadros por personaje: idle, cuatro direcciones de canto y cuatro poses hold en secuencia multi-frame.",
            "freeplay_album": "Carátula 512×512 y rótulo 512×128 declarados en el registro Album 1.0.3 y enlazados desde playData.album."
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
            "Los 20 candidatos se basan en stems vocales Demucs; la separación no asigna automáticamente personaje/strumline.",
            "El playtest en FNF Mobile V-Slice 0.8.6 permanece pendiente."
        ]
    })
    print(json.dumps({"version": VERSION, "packages": len(packages)}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
