#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SPECS = {
    "tools/resolve_playstate_v260.py": "tools/resolve_playstate_v262.py",
    "tools/validate_production_vocal_v261.py": "tools/validate_production_v262.py",
    "tools/validate_v261_contracts_assets.py": "tools/validate_v262_contracts_assets.py",
    "tools/validate_esperon_complete_v261.py": "tools/validate_esperon_complete_v262.py",
    "tools/mobile_headless_loader_v260.py": "tools/mobile_headless_loader_v262.py",
    "tools/run_qa_v261_20x20.py": "tools/run_qa_v262_20x21.py",
    "tools/package_esperon_complete_v261.py": "tools/package_esperon_complete_v262.py",
}


def update_song_list(text: str) -> str:
    marker = '"tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",'
    if marker not in text:
        raise RuntimeError("song_list_marker_missing")
    if '"si-te-vas"' not in text:
        text = text.replace(marker, marker + ' "si-te-vas",', 1)
    return text


def transform(source: Path, target: Path) -> None:
    text = source.read_text(encoding="utf-8")
    text = update_song_list(text)
    text = text.replace("V2.6.1", "V2.6.2")
    text = text.replace("V261", "V262")
    text = text.replace("v261", "v262")
    text = text.replace("2.6.1", "2.6.2")
    text = text.replace("V260", "V262")
    text = text.replace("v260", "v262")
    text = text.replace("20X20", "20X21")
    text = text.replace('"mods_per_round": 20', '"mods_per_round": 21')
    text = text.replace('"total_reviews": 400', '"total_reviews": 420')
    text = text.replace('len(individual) == 20', 'len(individual) == 21')
    text = text.replace('inspect(delivery / "Esperon-Completo.zip", 20)', 'inspect(delivery / "Esperon-Completo.zip", 21)')
    text = text.replace('len(rows) == 20', 'len(rows) == 21')
    # Resolver evidence had a historical before-fix filename; isolate the new gate output.
    if target.name == "resolve_playstate_v262.py":
        text = text.replace('playstate-resolver-before-fix.json', 'playstate-resolver-production-v262.json')
    target.write_text(text, encoding="utf-8")


def main() -> None:
    for source_name, target_name in SPECS.items():
        transform(ROOT / source_name, ROOT / target_name)
    print(f"created={len(SPECS)}")


if __name__ == "__main__":
    main()
