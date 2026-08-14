#!/usr/bin/env python3
"""Consolida la auditoría Wide Research de estructura y sincronía de los 20 mods."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    baseline_path = ROOT / "qa-lab/session-zip-structure/asset-layout-repair.json"
    baseline = read_json(baseline_path) if baseline_path.is_file() else read_json(ROOT / "qa-lab/wide-research-v212/baseline-musical-hashes.json")
    baseline_entries = baseline.get("entries", [])
    current = []
    for item in baseline_entries:
        mod = ROOT / "mods" / item["mod"]
        song = item["song"]
        song_dir = mod / "data/songs" / song
        chart = next(song_dir.glob("*-chart.json"))
        metadata = next(song_dir.glob("*-metadata.json"))
        current.append({
            "mod": item["mod"],
            "song": song,
            "inst_sha256": sha256(mod / "songs" / song / "Inst.ogg"),
            "chart_sha256": sha256(chart),
            "metadata_sha256": sha256(metadata),
            "musical_hashes_unchanged": item.get("protected_hashes", {}).get("inst_sha256", item.get("inst_sha256")) == sha256(mod / "songs" / song / "Inst.ogg") and item.get("protected_hashes", {}).get("chart_sha256", item.get("chart_sha256")) == sha256(chart) and item.get("protected_hashes", {}).get("metadata_sha256", item.get("metadata_sha256")) == sha256(metadata),
        })
    musical_ok = len(current) == 20 and all(item["musical_hashes_unchanged"] for item in current)

    structure = read_json(ROOT / "qa-lab/session-zip-structure/official-reference-comparison.json")
    install = read_json(ROOT / "qa-lab/session-zip-structure/v2.1.2-install-layout.json")
    final_static = read_json(ROOT / "qa-lab/session-30min/final-vslice-086-static.json")
    hscript = read_json(ROOT / "qa-lab/session-hscript/hscript-zip-inventory-v2.1.2.json")
    sync = read_json(ROOT / "qa-lab/wide-research-v212/vocal-chart-sync-consolidated.json")
    qa = read_json(ROOT / "qa-lab/final/consolidated-20-rounds.json")
    visual_files = sorted((ROOT / "qa-lab/session-30min/visual-animation").glob("esperon-dano-*-review.json"))
    visual = [read_json(path) for path in visual_files]
    visual_ok = len(visual) == 20 and all(item.get("status") == "PASS" and not item.get("issues") for item in visual)

    payload = {
        "scope": "WIDE_RESEARCH_FINAL_AUDIT_20_MODS",
        "target": "FNF Mobile V-Slice 0.8.6",
        "sources": {
            "official_installation": "https://github.com/FunkinCrew/Funkin/blob/v0.8.6/docs/INSTALLING_MODS.md",
            "official_release": "https://github.com/FunkinCrew/Funkin/releases/tag/v0.8.6",
            "official_modding_docs": "https://funkincrew.github.io/funkin-modding-docs/",
            "official_mod_menu_blog": "https://funkin.me/blog/2026-08-03/",
            "official_assets": "https://github.com/FunkinCrew/Funkin.assets",
            "community_template": "https://github.com/crowplexus/Funkin-VSlice-Template",
        },
        "coverage": {"mods": 20, "source_mods": len(baseline_entries), "individual_zips": install.get("packages"), "collection": install.get("collection")},
        "structure": {"status": "PASS" if structure.get("status") == "PASS" and install.get("status") == "PASS" else "ERRORS_FOUND", "official_reference_comparison": structure.get("coverage"), "install_layout": install.get("status"), "errors": install.get("collection_errors", [])},
        "v_slice_contracts": {"status": "PASS" if final_static.get("status") == "PASS" and hscript.get("status") == "PASS" else "ERRORS_FOUND", "static": {"mods": final_static.get("mods"), "passed": final_static.get("passed")}, "hscript": {"packages": hscript.get("packages"), "hscript_files": hscript.get("hscript_files"), "module_superclass_files": hscript.get("module_superclass_files")}},
        "visual": {"status": "PASS" if visual_ok else "REVIEW_REQUIRED", "reports": len(visual), "errors": sum(1 for item in visual if item.get("status") == "ERROR"), "warnings": sum(1 for item in visual if item.get("status") == "WARNING")},
        "musical_hash_integrity": {"status": "PASS" if musical_ok else "ERRORS_FOUND", "entries": current},
        "sync": {"structural_status": sync.get("structural_status"), "evidence_status": sync.get("evidence_status"), "promotion_status": sync.get("promotion_status"), "engine_confirmation": sync.get("engine_confirmation"), "songs": sync.get("songs"), "passed_structural": sync.get("passed_structural")},
        "qa": {"status": qa.get("status"), "rounds": qa.get("rounds"), "mods_per_round": qa.get("mods_per_round"), "records": qa.get("records"), "totals": qa.get("totals")},
        "overall_static_status": "PASS" if all([structure.get("status") == "PASS", install.get("status") == "PASS", final_static.get("status") == "PASS", hscript.get("status") == "PASS", visual_ok, musical_ok, sync.get("structural_status") == "PASS", qa.get("status") == "STABLE_PLATEAU_REACHED"]) else "REVIEW_REQUIRED",
        "limitations": ["La auditoría estática no sustituye Audio Sync Test dentro del Chart Editor ni el playtest en FNF Mobile.", "La evidencia vocal es PASS_EVIDENCE_ONLY y permanece MANUAL_REVIEW_REQUIRED para promoción musical."],
    }
    output = ROOT / "qa-lab/wide-research-v212/final-wide-research-report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mods": 20, "overall_static_status": payload["overall_static_status"], "sync_evidence": payload["sync"]["evidence_status"]}, ensure_ascii=False))
    return 0 if payload["overall_static_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
