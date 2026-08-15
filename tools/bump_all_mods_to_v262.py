#!/usr/bin/env python3
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos", "si-te-vas",
]

def bump(root: Path, song: str) -> dict:
    path = root / "mods" / f"esperon-dano-{song}" / "_polymod_meta.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["mod_version"] = "2.6.2"
    if song != "si-te-vas":
        data["description"] = data.get("description", "").replace("V2.6.1", "V2.6.2")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"song": song, "path": str(path.relative_to(root)), "mod_version": data["mod_version"]}

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument("root", type=Path, nargs="?", default=Path(".")); parser.add_argument("--workers", type=int, default=8); args = parser.parse_args()
    root = args.root.resolve()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(lambda song: bump(root, song), SONGS))
    print(json.dumps({"songs": len(rows), "version": "2.6.2", "status": "PASS"}, ensure_ascii=False))

if __name__ == "__main__": main()
