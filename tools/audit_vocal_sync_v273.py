#!/usr/bin/env python3
"""Parallel, evidence-first audit of vocal charts for the 21 Esperon mods."""
from __future__ import annotations

import concurrent.futures
import json
import math
import os
import subprocess
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np
import soundfile as sf
from scipy.signal import find_peaks

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "si-te-vas", "solare",
    "tristella", "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]
DIFFS = ("easy", "normal", "hard")
PLAYER_LANES = {0, 1, 2, 3}
ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "qa-lab/rebuild-v273/playstate-fix/vocal-sync-candidates-canonical"
V271 = ROOT / "qa-lab/rebuild-v271/playstate-fix/density-candidates"
OUT = ROOT / "qa-lab/rebuild-v273/playstate-fix/vocal-sync-candidates-canonical"
CHART_ROOT = ROOT / "mods"
CANDIDATE_ROOT: Path | None = None


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_chart(base: Path, song: str) -> Path | None:
    candidates = [
        base / song / "candidate-chart.json",
        base / song / f"{song}-chart.json",
        base / song / "density-candidate-chart.json",
    ]
    for path in candidates:
        if path.is_file():
            return path
    found = sorted((base / song).glob("*.json")) if (base / song).is_dir() else []
    for path in found:
        try:
            data = read_json(path)
        except Exception:
            continue
        if isinstance(data.get("notes"), dict):
            return path
    return None


def voice_path(song: str, alignment: dict[str, Any]) -> Path:
    raw = str(alignment.get("voice", ""))
    if raw.startswith("mods/"):
        return ROOT / raw
    candidates = [
        ROOT / f"mods/esperon-dano-{song}/songs/{song}/Voices-esperon-{song}.ogg",
        ROOT / raw,
    ]
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


def independent_energy_onsets(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"status": "MISSING", "onsets_ms": []}
    try:
        audio, sr = sf.read(path, always_2d=True, dtype="float32")
        mono = audio.mean(axis=1)
        frame = max(1, int(sr * 0.020))
        hop = max(1, int(sr * 0.010))
        if len(mono) < frame:
            return {"status": "TOO_SHORT", "onsets_ms": [], "sample_rate": sr}
        count = 1 + (len(mono) - frame) // hop
        rms = np.empty(count, dtype=np.float32)
        for i in range(count):
            block = mono[i * hop:i * hop + frame]
            rms[i] = float(np.sqrt(np.mean(block * block) + 1e-10))
        smooth = np.convolve(rms, np.ones(5, dtype=np.float32) / 5, mode="same")
        delta = np.maximum(0.0, np.diff(smooth, prepend=smooth[0]))
        noise = float(np.median(delta))
        mad = float(np.median(np.abs(delta - noise)) + 1e-7)
        prominence = max(0.002, noise + 3.0 * mad)
        peaks, _ = find_peaks(delta, distance=max(1, int(0.060 / 0.010)), prominence=prominence)
        onsets = [round(float(index * hop / sr * 1000.0), 3) for index in peaks]
        return {"status": "PASS", "sample_rate": int(sr), "duration_ms": round(len(mono) / sr * 1000.0, 3), "onsets_ms": onsets, "threshold": prominence}
    except Exception as exc:
        return {"status": "ERROR", "onsets_ms": [], "error": repr(exc)}


def local_rms_refinement(path: Path, target_times: list[float], window_ms: float = 80.0) -> dict[str, Any]:
    if not path.is_file() or not target_times:
        return {"status": "MISSING", "targets": len(target_times), "matched": 0, "deltas_ms": []}
    try:
        audio, sr = sf.read(path, always_2d=True, dtype="float32")
        mono = audio.mean(axis=1)
        frame = max(1, int(sr * 0.020))
        hop = max(1, int(sr * 0.010))
        if len(mono) < frame:
            return {"status": "TOO_SHORT", "targets": len(target_times), "matched": 0, "deltas_ms": []}
        count = 1 + (len(mono) - frame) // hop
        rms = np.empty(count, dtype=np.float32)
        for index in range(count):
            block = mono[index * hop:index * hop + frame]
            rms[index] = float(np.sqrt(np.mean(block * block) + 1e-10))
        smooth = np.convolve(rms, np.ones(5, dtype=np.float32) / 5, mode="same")
        delta = np.maximum(0.0, np.diff(smooth, prepend=smooth[0]))
        noise = float(np.median(delta))
        mad = float(np.median(np.abs(delta - noise)) + 1e-7)
        threshold = max(0.002, noise + 2.0 * mad)
        centers = np.arange(count, dtype=np.float32) * (hop / sr * 1000.0)
        deltas: list[float] = []
        confidences: list[float] = []
        for target in target_times:
            mask = np.abs(centers - float(target)) <= window_ms
            candidates = np.where(mask & (delta >= threshold))[0]
            if len(candidates) == 0:
                continue
            best = int(candidates[np.argmax(delta[candidates])])
            deltas.append(float(centers[best] - float(target)))
            confidences.append(float(delta[best] / max(threshold, 1e-7)))
        abs_deltas = np.abs(deltas)
        return {
            "status": "PASS",
            "targets": len(target_times),
            "matched": len(deltas),
            "coverage": round(len(deltas) / len(target_times), 4),
            "median_delta_ms": round(median(deltas), 3) if deltas else None,
            "mean_abs_error_ms": round(float(np.mean(abs_deltas)), 3) if deltas else None,
            "p95_abs_error_ms": round(float(np.percentile(abs_deltas, 95)), 3) if deltas else None,
            "low_confidence_matches": sum(value < 1.25 for value in confidences),
            "deltas_ms": [round(value, 3) for value in deltas[:500]],
        }
    except Exception as exc:
        return {"status": "ERROR", "targets": len(target_times), "matched": 0, "deltas_ms": [], "error": repr(exc)}


def spectral_flux_onsets(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"status": "MISSING", "onsets_ms": []}
    try:
        audio, sr = sf.read(path, always_2d=True, dtype="float32")
        mono = audio.mean(axis=1)
        frame = 2048
        hop = max(1, int(sr * 0.010))
        if len(mono) < frame:
            return {"status": "TOO_SHORT", "onsets_ms": [], "sample_rate": sr}
        count = 1 + (len(mono) - frame) // hop
        window = np.hanning(frame).astype(np.float32)
        previous = None
        flux = np.zeros(count, dtype=np.float32)
        for index in range(count):
            block = mono[index * hop:index * hop + frame] * window
            magnitude = np.abs(np.fft.rfft(block))
            if previous is not None:
                flux[index] = float(np.sum(np.maximum(magnitude - previous, 0.0)))
            previous = magnitude
        smooth = np.convolve(flux, np.ones(5, dtype=np.float32) / 5, mode="same")
        noise = float(np.median(smooth))
        mad = float(np.median(np.abs(smooth - noise)) + 1e-7)
        prominence = max(noise * 0.10, noise + 2.5 * mad)
        peaks, _ = find_peaks(smooth, distance=max(1, int(0.060 / 0.010)), prominence=prominence)
        onsets = [round(float(index * hop / sr * 1000.0), 3) for index in peaks]
        return {"status": "PASS", "sample_rate": int(sr), "duration_ms": round(len(mono) / sr * 1000.0, 3), "onsets_ms": onsets, "threshold": prominence}
    except Exception as exc:
        return {"status": "ERROR", "onsets_ms": [], "error": repr(exc)}


def nearest_match(expected: list[float], observed: list[float], tolerance: float = 135.0) -> dict[str, Any]:
    observed_sorted = sorted(observed)
    used: set[int] = set()
    errors: list[float] = []
    matched: list[dict[str, Any]] = []
    unmatched: list[float] = []
    for target in sorted(expected):
        candidates = [(abs(value - target), index, value) for index, value in enumerate(observed_sorted) if index not in used]
        if not candidates:
            unmatched.append(target)
            continue
        distance, index, value = min(candidates)
        if distance > tolerance:
            unmatched.append(target)
            continue
        used.add(index)
        errors.append(value - target)
        matched.append({"expected_ms": target, "observed_ms": value, "delta_ms": value - target, "abs_error_ms": distance})
    extra = [value for index, value in enumerate(observed_sorted) if index not in used]
    return {
        "expected": len(expected), "observed": len(observed), "matched": len(matched),
        "coverage": round(len(matched) / len(expected), 4) if expected else 1.0,
        "unmatched_expected_ms": unmatched[:80], "extra_observed_ms": extra[:80],
        "median_delta_ms": round(median(errors), 3) if errors else None,
        "mean_abs_error_ms": round(float(np.mean(np.abs(errors))), 3) if errors else None,
        "p95_abs_error_ms": round(float(np.percentile(np.abs(errors), 95)), 3) if errors else None,
        "matches": matched[:120],
    }


def chart_notes(chart: dict[str, Any], difficulty: str) -> list[dict[str, Any]]:
    notes = chart.get("notes", {}).get(difficulty, [])
    return sorted([note for note in notes if isinstance(note, dict) and int(note.get("d", -1)) in PLAYER_LANES], key=lambda n: float(n.get("t", 0)))


def duplicate_collisions(notes: list[dict[str, Any]], spacing_ms: float = 12.0) -> list[dict[str, Any]]:
    collisions = []
    by_lane: dict[int, list[dict[str, Any]]] = {}
    for note in notes:
        by_lane.setdefault(int(note["d"]), []).append(note)
    for lane, items in by_lane.items():
        for left, right in zip(items, items[1:]):
            gap = float(right["t"]) - float(left["t"])
            if 0 <= gap < spacing_ms:
                collisions.append({"lane": lane, "left_t": left["t"], "right_t": right["t"], "gap_ms": gap})
    return collisions


def close_pair_metrics(expected: list[float], notes: list[dict[str, Any]]) -> dict[str, Any]:
    chart_times = [float(n["t"]) for n in notes]
    pairs = []
    preserved = 0
    collapsed = 0
    for left, right in zip(sorted(expected), sorted(expected)[1:]):
        gap = right - left
        if 80.0 <= gap <= 500.0:
            pairs.append({"left_ms": left, "right_ms": right, "gap_ms": gap})
            left_hits = [t for t in chart_times if abs(t - left) <= 135.0]
            right_hits = [t for t in chart_times if abs(t - right) <= 135.0]
            if left_hits and right_hits and min(abs(a - b) for a in left_hits for b in right_hits) > 12.0:
                preserved += 1
            else:
                collapsed += 1
    return {"pairs": len(pairs), "preserved_separate": preserved, "collapsed_or_missing": collapsed, "examples": pairs[:20]}


def hold_metrics(syllables: list[dict[str, Any]], notes: list[dict[str, Any]]) -> dict[str, Any]:
    expected = [s for s in syllables if float(s.get("hold_ms", 0.0)) >= 180.0 and s.get("kind") == "sustained_syllable"]
    errors = []
    missing = 0
    for syllable in expected:
        start = float(syllable.get("audio_onset_ms", syllable.get("start_ms", 0.0)))
        wanted = float(syllable.get("hold_ms", 0.0))
        candidates = [n for n in notes if abs(float(n.get("t", 0.0)) - start) <= 135.0]
        if not candidates:
            missing += 1
            continue
        note = min(candidates, key=lambda n: abs(float(n["t"]) - start))
        actual = float(note.get("l", 0.0))
        errors.append(actual - wanted)
    return {
        "expected_sustained": len(expected), "missing": missing,
        "median_hold_delta_ms": round(median(errors), 3) if errors else None,
        "mean_abs_hold_error_ms": round(float(np.mean(np.abs(errors))), 3) if errors else None,
        "long_holds_over_1800_ms": sum(float(n.get("l", 0.0)) > 1800.0 for n in notes),
    }


def audio_hash(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False}
    try:
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], capture_output=True, text=True, timeout=60, check=False)
        return {"exists": True, "duration_seconds": float(probe.stdout.strip()) if probe.stdout.strip() else None, "ffprobe_returncode": probe.returncode}
    except Exception as exc:
        return {"exists": True, "error": repr(exc)}


def audit_song(song: str) -> dict[str, Any]:
    alignment_path = CANONICAL / song / "syllable-alignment.json"
    alignment = read_json(alignment_path)
    syllables = alignment.get("syllables", [])
    expected = [float(s.get("audio_onset_ms", s.get("start_ms", 0.0))) for s in syllables if s.get("audio_onset_ms") is not None]
    voice = voice_path(song, alignment)
    independent = independent_energy_onsets(voice)
    flux = spectral_flux_onsets(voice)
    voice_check = audio_hash(voice)
    diffs: dict[str, Any] = {}
    for difficulty in DIFFS:
        prod_chart_path = (CANDIDATE_ROOT / song / "candidate-chart.json") if CANDIDATE_ROOT is not None else (CHART_ROOT / f"esperon-dano-{song}/data/songs/{song}/{song}-chart.json")
        chart = read_json(prod_chart_path)
        notes = chart_notes(chart, difficulty)
        times = [float(n.get("t", 0.0)) for n in notes]
        coverage = {str(tol): nearest_match(expected, times, tol) for tol in (45.0, 90.0, 135.0)}
        local_refinement = local_rms_refinement(voice, times) if difficulty == "normal" else None
        diffs[difficulty] = {
            "chart": str(prod_chart_path.relative_to(ROOT)),
            "notes": len(notes), "holds": sum(float(n.get("l", 0.0)) >= 180.0 for n in notes),
            "coverage": coverage,
            "independent_rms_vs_chart": nearest_match(times, independent.get("onsets_ms", []), 90.0),
            "independent_flux_vs_chart": nearest_match(times, flux.get("onsets_ms", []), 90.0),
            "local_rms_refinement": local_refinement,
            "collisions_sub12ms": duplicate_collisions(notes),
            "close_pairs": close_pair_metrics(expected, notes),
            "holds": hold_metrics(syllables, notes),
            "lane_counts": {str(lane): sum(int(n.get("d", -1)) == lane for n in notes) for lane in sorted(PLAYER_LANES)},
            "duration_ms": max((float(n.get("t", 0.0)) + float(n.get("l", 0.0)) for n in notes), default=0.0),
        }
    previous_path = find_chart(V271, song)
    previous = None
    if previous_path:
        previous_chart = read_json(previous_path)
        previous = {difficulty: len(chart_notes(previous_chart, difficulty)) for difficulty in DIFFS}
    report = {
        "song": song,
        "alignment": str(alignment_path.relative_to(ROOT)),
        "syllables": len(syllables),
        "voice": str(voice.relative_to(ROOT)) if voice.is_relative_to(ROOT) else str(voice),
        "voice_probe": voice_check,
        "independent_energy_onsets": independent,
        "independent_spectral_flux_onsets": flux,
        "alignment_vs_independent_rms": nearest_match(expected, independent.get("onsets_ms", []), 90.0),
        "alignment_vs_independent_flux": nearest_match(expected, flux.get("onsets_ms", []), 90.0),
        "alignment_onset_span_ms": [min(expected), max(expected)] if expected else None,
        "difficulties": diffs,
        "v271_candidate_note_counts": previous,
        "status": "PASS" if all(diffs[d]["coverage"]["90.0"]["coverage"] >= 0.90 for d in ("normal", "hard")) and all(not diffs[d]["collisions_sub12ms"] for d in DIFFS) else "REVIEW",
    }
    out = OUT / song / "vocal-sync-audit-v273.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    global CHART_ROOT, CANDIDATE_ROOT, OUT
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--chart-root", type=Path, default=CHART_ROOT)
    parser.add_argument("--output-root", type=Path, default=OUT)
    parser.add_argument("--candidate-root", type=Path, default=None, help="Folder containing <song>/candidate-chart.json")
    args = parser.parse_args()
    CHART_ROOT = args.chart_root.resolve()
    CANDIDATE_ROOT = args.candidate_root.resolve() if args.candidate_root else None
    OUT = args.output_root.resolve()
    workers = min(8, max(1, os.cpu_count() or 1))
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        reports = list(pool.map(audit_song, SONGS))
    reports.sort(key=lambda r: r["song"])
    summary = {
        "scope": "VOCAL_SYNC_AUDIT_V273",
        "songs": len(reports),
        "workers": workers,
        "status_counts": {status: sum(r["status"] == status for r in reports) for status in ("PASS", "REVIEW")},
        "coverage_90_or_better": {d: sum(r["difficulties"][d]["coverage"]["90.0"]["coverage"] >= 0.90 for r in reports) for d in DIFFS},
        "coverage_135_or_better": {d: sum(r["difficulties"][d]["coverage"]["135.0"]["coverage"] >= 0.90 for r in reports) for d in DIFFS},
        "total_sub12_collisions": sum(len(r["difficulties"][d]["collisions_sub12ms"]) for r in reports for d in DIFFS),
        "total_close_pairs": sum(r["difficulties"]["normal"]["close_pairs"]["pairs"] for r in reports),
        "total_close_pairs_preserved": sum(r["difficulties"]["normal"]["close_pairs"]["preserved_separate"] for r in reports),
        "rms_alignment_median_deltas_ms": [r["alignment_vs_independent_rms"]["median_delta_ms"] for r in reports],
        "flux_alignment_median_deltas_ms": [r["alignment_vs_independent_flux"]["median_delta_ms"] for r in reports],
        "rms_chart_90_coverage": {d: round(float(np.mean([r["difficulties"][d]["independent_rms_vs_chart"]["coverage"] for r in reports])), 4) for d in DIFFS},
        "flux_chart_90_coverage": {d: round(float(np.mean([r["difficulties"][d]["independent_flux_vs_chart"]["coverage"] for r in reports])), 4) for d in DIFFS},
        "local_rms_median_deltas_ms": [r["difficulties"]["normal"]["local_rms_refinement"]["median_delta_ms"] for r in reports],
        "local_rms_p95_abs_errors_ms": [r["difficulties"]["normal"]["local_rms_refinement"]["p95_abs_error_ms"] for r in reports],
        "reports": reports,
    }
    out = OUT / "audit-vocal-sync-v273.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("songs", "workers", "status_counts", "coverage_90_or_better", "coverage_135_or_better", "total_sub12_collisions", "total_close_pairs", "total_close_pairs_preserved")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
