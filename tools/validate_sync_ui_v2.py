#!/usr/bin/env python3
"""Validador estático para charts candidatos, animaciones y UI de V-Slice 0.8.6."""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REQUIRED_ANIMS = {
    "idle": "Idle",
    "singLEFT": "Left",
    "singDOWN": "Down",
    "singUP": "Up",
    "singRIGHT": "Right",
    "singLEFT-hold": "LeftHold",
    "singDOWN-hold": "DownHold",
    "singUP-hold": "UpHold",
    "singRIGHT-hold": "RightHold",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_mod(mod: Path, root: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    song_dirs = [item for item in (mod / "data" / "songs").iterdir() if item.is_dir()]
    if len(song_dirs) != 1:
        return {"mod": mod.name, "status": "ERROR", "errors": ["Debe existir exactamente una canción"], "warnings": []}
    song_dir = song_dirs[0]
    song = song_dir.name
    metadata = load(song_dir / f"{song}-metadata.json")
    chart = load(song_dir / f"{song}-chart.json")
    style = metadata.get("playData", {}).get("noteStyle")
    if not isinstance(style, str) or not (mod / "data" / "notestyles" / f"{style}.json").is_file():
        errors.append("Note style no resuelto")
    chars = metadata.get("playData", {}).get("characters", {})
    player = chars.get("player")
    opponent = chars.get("opponent")
    players = set()
    opponents = set()
    for character_id, role in ((player, "player"), (opponent, "opponent")):
        path = mod / "data" / "characters" / f"{character_id}.json"
        if not isinstance(character_id, str) or not path.is_file():
            errors.append(f"Personaje {role} no resuelto")
            continue
        data = load(path)
        found = {item.get("name"): item.get("prefix") for item in data.get("animations", []) if isinstance(item, dict)}
        for name, prefix in REQUIRED_ANIMS.items():
            if found.get(name) != prefix:
                errors.append(f"{role}: animación {name} no declarada")
        atlas = mod / "images" / "characters" / f"{character_id}.xml"
        if not atlas.is_file():
            errors.append(f"{role}: atlas XML ausente")
            continue
        xml = ET.parse(atlas).getroot()
        tags = [node.attrib.get("name", "") for node in xml.findall("SubTexture")]
        for prefix in REQUIRED_ANIMS.values():
            if not any(tag.startswith(prefix) for tag in tags):
                errors.append(f"{role}: atlas sin cuadros para {prefix}")
        if role == "player":
            players = {4, 5, 6, 7}
        else:
            opponents = {0, 1, 2, 3}
    total_notes = 0
    vocal_side_notes = 0
    for difficulty in ("easy", "normal", "hard"):
        notes = chart.get("notes", {}).get(difficulty)
        if not isinstance(notes, list) or not notes:
            errors.append(f"{difficulty}: notas ausentes")
            continue
        previous = -1.0
        for index, note in enumerate(notes):
            if not isinstance(note, dict) or not isinstance(note.get("t"), (int, float)) or not isinstance(note.get("d"), int):
                errors.append(f"{difficulty}[{index}]: nota inválida")
                continue
            if note["t"] < previous or not 0 <= note["d"] <= 7:
                errors.append(f"{difficulty}[{index}]: orden/dirección inválidos")
            previous = note["t"]
            total_notes += 1
            if note["d"] in players | opponents:
                vocal_side_notes += 1
    if total_notes == 0 or vocal_side_notes != total_notes:
        errors.append("El chart no vincula todas las notas a una strumline de personaje")
    evidence_candidates = list((root / "evidence" / "analysis" / "all-candidates" / song).glob("*-alignment-evidence.json"))
    if song == "solare":
        evidence_candidates = list((root / "evidence" / "analysis" / "solare").glob("*-alignment-evidence.json"))
    if len(evidence_candidates) != 1:
        errors.append("Evidencia de alineación ausente")
    else:
        evidence = load(evidence_candidates[0])
        if evidence.get("status") != "REQUIRES_HUMAN_REVIEW":
            warnings.append("Estado de evidencia inesperado")
        if evidence.get("analysis_mode") != "VOCAL_STEM":
            warnings.append("La actividad vocal proviene de mezcla completa: necesita revisión humana prioritaria")
    if not (mod / "images" / "ui" / style / "healthbar-theme.png").is_file():
        errors.append("Asset de barra de vida temática ausente")
    if not list((mod / "scripts").glob("*.hxc")):
        errors.append("Script de HUD ausente")
    return {"mod": mod.name, "song": song, "status": "PASS" if not errors else "ERROR", "errors": errors, "warnings": warnings, "total_notes": total_notes}


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    reports = [check_mod(mod, root) for mod in sorted((root / "mods").glob("esperon-dano-*")) if mod.is_dir()]
    payload = {
        "scope": "STATIC_VSLICE_SYNC_UI_V2_VALIDATION",
        "status": "PASS" if all(report["status"] == "PASS" for report in reports) else "ERRORS_FOUND",
        "mods": len(reports),
        "passed": sum(report["status"] == "PASS" for report in reports),
        "warnings": sum(len(report["warnings"]) for report in reports),
        "reports": reports,
        "limitations": [
            "La validación confirma rutas, enlaces y coherencia estática; no reemplaza Audio Sync Test.",
            "Los 19 análisis sobre mezcla completa no prueban entradas vocales individuales.",
            "El playtest móvil oficial sigue pendiente."
        ]
    }
    out = root / "artifacts" / "sync-ui-v2-validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("status", "mods", "passed", "warnings")}, ensure_ascii=False))
    raise SystemExit(0 if payload["status"] == "PASS" else 1)

if __name__ == "__main__":
    main()
