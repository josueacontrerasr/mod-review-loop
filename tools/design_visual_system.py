#!/usr/bin/env python3
"""Genera un brief visual V2 individual sin tocar audio, charts ni offsets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONCEPTS = {
    "arcoloria": ("pétalos cromáticos", "rombo floral", "aro de pétalos", "barra con pétalos alternos"),
    "cortamos-y-volvemos": ("corte de película", "chevrón de fotograma", "marco perforado", "barra con cortes de celuloide"),
    "dano": ("neón herido", "punta quebrada", "receptor de pulso", "barra de pulso carmesí"),
    "dias-magicos": ("destello de amanecer", "estrella de cuatro puntas", "halo de amanecer", "barra de destellos"),
    "eclipsis": ("corona eclipsada", "media luna direccional", "anillo umbral", "barra de corona dual"),
    "fango": ("gota luminosa", "flecha de lodo cristalino", "receptor de charco", "barra de burbujas"),
    "luma": ("prisma luminoso", "triángulo refractado", "anillo prismático", "barra de refracción"),
    "maraton-de-peliculas": ("sala de proyección", "flecha de claqueta", "receptor de película", "barra de tira cinematográfica"),
    "me-voy-a-morir-si-no-me-besas-ahora-mismo": ("latido urgente", "corazón geométrico", "halo cardiaco", "barra de pulso afectivo"),
    "meteora": ("trazo meteórico", "cometa direccional", "receptor orbital", "barra de estela"),
    "mi-hogar": ("refugio cálido", "techo direccional", "receptor ventana", "barra de mosaico hogareño"),
    "nubia": ("nube estelar", "punta de nube", "receptor nebuloso", "barra de constelación"),
    "nuestro-amor-no-es-normal": ("amor asimétrico", "corazón poligonal", "receptor irregular", "barra de vínculo anómalo"),
    "peligrosa": ("señal de peligro", "triángulo de alerta", "receptor de advertencia", "barra de riesgo"),
    "rompecabezas": ("pieza encajable", "flecha modular", "receptor de puzzle", "barra de piezas"),
    "solare": ("rayo solar", "flecha radiante", "receptor heliocéntrico", "barra de amanecer solar"),
    "tristella": ("triple estrella", "punta estelar", "receptor de tres estrellas", "barra de constelación triple"),
    "tu-dealer-de-nostalgia": ("cinta analógica", "flecha de casete", "receptor retro", "barra de señal nostálgica"),
    "un-poco-bien-un-poco-mal": ("dualidad equilibrada", "flecha bicolor", "receptor partido", "barra de contraste"),
    "volver-a-vernos": ("reencuentro crepuscular", "flecha entrelazada", "receptor espejo", "barra de horizonte"),
}

DIRECTIONS = {
    "left": "La silueta apunta a la izquierda y conserva un borde oscuro de alto contraste.",
    "down": "La silueta apunta abajo y usa el segundo tono de la paleta como cara interior.",
    "up": "La silueta apunta arriba y destaca el motivo temático en el vértice superior.",
    "right": "La silueta apunta a la derecha y refleja la composición izquierda sin invertir el motivo central.",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def design_for(mod: Path) -> None:
    slug = mod.name.removeprefix("esperon-dano-")
    if slug not in CONCEPTS:
        raise ValueError(f"No existe un concepto V2 para {slug}")
    brief_path = ROOT / "visual-briefs" / f"{slug}.json"
    brief = read_json(brief_path)
    motif, arrow_shape, strum_shape, bar_shape = CONCEPTS[slug]
    note_style_id = f"esperon-{slug}-notes"
    brief["visual_system_v2"] = {
        "status": "DESIGNED_PENDING_ASSET_GENERATION",
        "rule": "No modifica audio, BPM, offsets, timeChanges ni datos de notas.",
        "note_style": {
            "id": note_style_id,
            "fallback": "funkin",
            "motif": motif,
            "arrow_shape": arrow_shape,
            "receptor_shape": strum_shape,
            "asset_paths": {
                "notes": f"shared:notes/{note_style_id}-notes",
                "strumline": f"shared:notes/{note_style_id}-strumline",
            },
            "directions": DIRECTIONS,
            "states": ["static", "press", "confirm", "confirm_hold"],
        },
        "hud": {
            "scope": "tema visual de gameplay mediante iconos existentes y assets de judgement/combo propios del note style; no inyecta scripts de HUD sin API pública probada",
            "health_bar_theme": bar_shape,
            "judgement_style": f"placa geométrica {motif}",
            "combo_style": f"numerales con acento {motif}",
            "mobile_readability": "contraste alto, borde oscuro de 6 px y zonas transparentes fuera del sprite",
        },
    }
    write_json(brief_path, brief)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mod", required=True, help="ID de carpeta bajo mods/")
    args = parser.parse_args()
    mod = ROOT / "mods" / args.mod
    if not mod.is_dir():
        raise SystemExit(f"Mod no encontrado: {mod}")
    design_for(mod)
    print(args.mod)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
