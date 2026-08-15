#!/usr/bin/env python3
"""Genera charts candidatos estrictamente vocal-only sin modificar producción.

La única fuente de tiempos es Voices-*.ogg. Inst.ogg nunca se carga ni se usa
para crear notas. Los outputs se escriben bajo qa-lab/rebuild-v260/vocal-only.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import librosa
import numpy as np

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]
SR = 22050
HOP = 256
FRAME = 2048
MIN_SEGMENT_MS = 120.0
SEGMENT_GAP_MS = 180.0
MIN_STRONG_SPACING_MS = 150.0
MIN_HARD_SPACING_MS = 85.0


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def merge_mask(mask: np.ndarray, hop_ms: float) -> list[tuple[float, float]]:
    raw: list[tuple[int, int]] = []
    start: int | None = None
    for index, active in enumerate(mask):
        if bool(active) and start is None:
            start = index
        elif not bool(active) and start is not None:
            raw.append((start, index))
            start = None
    if start is not None:
        raw.append((start, len(mask)))
    merged: list[tuple[float, float]] = []
    for start_frame, end_frame in raw:
        start_ms = start_frame * hop_ms
        end_ms = end_frame * hop_ms
        if end_ms - start_ms < MIN_SEGMENT_MS:
            continue
        if merged and start_ms - merged[-1][1] <= SEGMENT_GAP_MS:
            merged[-1] = (merged[-1][0], end_ms)
        else:
            merged.append((start_ms, end_ms))
    return merged


def inside_segments(value: float, segments: list[tuple[float, float]], margin_ms: float = 45.0) -> bool:
    return any(start_ms - margin_ms <= value <= end_ms + margin_ms for start_ms, end_ms in segments)


def dedupe(times: list[float], min_spacing_ms: float, segments: list[tuple[float, float]]) -> list[float]:
    selected: list[float] = []
    for time_ms in sorted(times):
        if not inside_segments(time_ms, segments):
            continue
        if selected and time_ms - selected[-1] < min_spacing_ms:
            continue
        selected.append(round(float(time_ms), 3))
    return selected


def analyze_voice(path: Path) -> dict[str, Any]:
    y, sr = librosa.load(path, sr=SR, mono=True)
    hop_ms = HOP * 1000.0 / sr
    rms = librosa.feature.rms(y=y, frame_length=FRAME, hop_length=HOP, center=True)[0]
    db = librosa.amplitude_to_db(np.maximum(rms, 1e-10), ref=np.max)
    noise_floor_db = float(np.percentile(db, 20.0))
    robust_floor_db = float(np.percentile(db, 35.0))
    active_threshold_db = max(noise_floor_db + 8.0, robust_floor_db + 2.0)
    active_mask = db >= active_threshold_db
    segments = merge_mask(active_mask, hop_ms)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP, aggregate=np.median)
    onset_db = librosa.amplitude_to_db(np.maximum(onset_env, 1e-10), ref=np.max)
    frame_times = librosa.frames_to_time(np.arange(len(onset_env)), sr=sr, hop_length=HOP) * 1000.0
    vocal_onset_mask = np.array([inside_segments(float(time), segments, margin_ms=35.0) for time in frame_times])
    strong_threshold = float(np.percentile(onset_db[vocal_onset_mask], 70.0)) if vocal_onset_mask.any() else 0.0
    normal_threshold = float(np.percentile(onset_db[vocal_onset_mask], 45.0)) if vocal_onset_mask.any() else 0.0
    strong_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, hop_length=HOP, units="frames", backtrack=False, pre_max=4, post_max=4, pre_avg=8, post_avg=8, delta=max(0.05, strong_threshold / 20.0), wait=max(1, int(MIN_STRONG_SPACING_MS / hop_ms)))
    broad_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, hop_length=HOP, units="frames", backtrack=False, pre_max=3, post_max=3, pre_avg=6, post_avg=6, delta=max(0.02, normal_threshold / 25.0), wait=max(1, int(MIN_HARD_SPACING_MS / hop_ms)))
    strong_raw = [float(frame) * hop_ms for frame in strong_frames if frame < len(onset_db) and onset_db[frame] >= strong_threshold]
    broad_raw = [float(frame) * hop_ms for frame in broad_frames if frame < len(onset_db) and onset_db[frame] >= normal_threshold]
    strong = dedupe(strong_raw, MIN_STRONG_SPACING_MS, segments)
    normal = dedupe(sorted(set(strong + broad_raw)), MIN_STRONG_SPACING_MS, segments)
    hard = dedupe(sorted(set(strong + broad_raw)), MIN_HARD_SPACING_MS, segments)
    return {
        "duration_ms": round(float(len(y) / sr * 1000.0), 3),
        "sample_rate": sr,
        "frame_ms": round(FRAME * 1000.0 / sr, 3),
        "hop_ms": round(hop_ms, 3),
        "noise_floor_db": round(noise_floor_db, 3),
        "active_threshold_db": round(active_threshold_db, 3),
        "segments": [{"start_ms": round(start, 3), "end_ms": round(end, 3)} for start, end in segments],
        "onsets": {"easy": strong[::2], "normal": normal, "hard": hard},
        "onset_counts": {"easy": len(strong[::2]), "normal": len(normal), "hard": len(hard)},
        "source_policy": "VOICE_ONLY; all timestamps derive from Voices-*.ogg",
    }


def note(t: float, index: int) -> dict[str, Any]:
    return {"t": round(t, 3), "d": index % 4, "_source": "voice", "_voice_event_id": f"voice-{index + 1:05d}"}


def chart_from_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    notes = {}
    for difficulty in ("easy", "normal", "hard"):
        notes[difficulty] = [note(float(time_ms), index) for index, time_ms in enumerate(analysis["onsets"][difficulty])]
    return {
        "version": "2.0.0",
        "scrollSpeed": {"easy": 0.9, "normal": 1.0, "hard": 1.12},
        "events": [],
        "notes": notes,
        "candidateOnly": True,
        "generatedBy": "Vocal-only distributed Voices-*.ogg onset generator V260",
        "sourcePolicy": "NO_INSTRUMENTAL_NOTES",
    }


def analyze_one(root: Path, song: str) -> dict[str, Any]:
    song_dir = root / "mods" / f"esperon-dano-{song}" / "songs" / song
    voice_files = sorted(song_dir.glob("Voices-*.ogg"))
    if len(voice_files) != 1:
        return {"song": song, "status": "ERROR", "errors": [f"vocal_sources={len(voice_files)}"]}
    voice = voice_files[0]
    try:
        analysis = analyze_voice(voice)
        chart = chart_from_analysis(analysis)
        output = root / "qa-lab" / "rebuild-v260" / "vocal-only" / song
        output.mkdir(parents=True, exist_ok=True)
        (output / "voice-activity.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (output / "chart-vocal-only.json").write_text(json.dumps(chart, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report = {
            "song": song,
            "status": "PASS",
            "source_type": "DISTRIBUTED_VOCAL_OGG",
            "source_vocal": str(voice.relative_to(root)),
            "source_vocal_sha256": file_sha256(voice),
            "analysis": analysis,
            "instrumental_used_for_generation": False,
            "manual_review_required": True,
            "limitations": ["Vocal stem may contain residual bleed; verify ambiguous segments manually.", "Audio Sync Test and mobile playtest remain required."],
        }
        (output / "candidate-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"song": song, "status": "PASS", "onsets": analysis["onset_counts"], "source_sha256": report["source_vocal_sha256"], "output": str(output.relative_to(root))}
    except Exception as exc:
        return {"song": song, "status": "ERROR", "errors": [f"{type(exc).__name__}: {exc}"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    root = args.root.resolve()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = sorted(pool.map(lambda song: analyze_one(root, song), SONGS), key=lambda row: row["song"])
    payload = {
        "scope": "VOCAL_ONLY_CANDIDATES_V260",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "target_version": "0.8.6",
        "songs": len(rows),
        "passed": sum(row["status"] == "PASS" for row in rows),
        "status": "PASS_CANDIDATES_ISOLATED" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND",
        "rows": rows,
        "instrumental_used_for_generation": False,
        "promotion": "BLOCKED_UNTIL_PROVENANCE_AND_AUDIO_SYNC_GATES_PASS",
    }
    output = root / "qa-lab" / "rebuild-v260" / "vocal-only" / "candidate-summary-v260.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "passed": payload["passed"], "status": payload["status"], "instrumental_used_for_generation": payload["instrumental_used_for_generation"], "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS_CANDIDATES_ISOLATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
