#!/usr/bin/env python3
"""Genera candidatos vocal-only refinados V2.6.2 a partir de Voices-*.ogg."""
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
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos", "si-te-vas",
]
SR = 22050
HOP = 256
FRAME = 1024
MIN_SEGMENT_MS = 120.0
SEGMENT_GAP_MS = 180.0


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def merge_mask(mask: np.ndarray, hop_ms: float) -> list[tuple[float, float]]:
    raw: list[tuple[int, int]] = []
    start: int | None = None
    for index, flag in enumerate(mask):
        if bool(flag) and start is None:
            start = index
        elif not bool(flag) and start is not None:
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


def in_segments(time_ms: float, segments: list[tuple[float, float]], margin_ms: float = 45.0) -> bool:
    return any(start - margin_ms <= time_ms <= end + margin_ms for start, end in segments)


def dedupe_scored(items: list[tuple[float, float]], spacing_ms: float, segments: list[tuple[float, float]]) -> list[tuple[float, float]]:
    selected: list[tuple[float, float]] = []
    for time_ms, score in sorted(items):
        if not in_segments(time_ms, segments):
            continue
        if selected and time_ms - selected[-1][0] < spacing_ms:
            if score > selected[-1][1]:
                selected[-1] = (time_ms, score)
            continue
        selected.append((round(float(time_ms), 3), float(score)))
    return selected


def refine_to_energy(time_ms: float, frame_times: np.ndarray, rms: np.ndarray, window_ms: float = 55.0) -> float:
    mask = (frame_times >= time_ms - window_ms) & (frame_times <= time_ms + window_ms)
    if not mask.any():
        return round(float(time_ms), 3)
    indices = np.flatnonzero(mask)
    return round(float(frame_times[indices[int(np.argmax(rms[indices]))]]), 3)


def analyze_voice(path: Path) -> dict[str, Any]:
    y, sr = librosa.load(path, sr=SR, mono=True)
    hop_ms = HOP * 1000.0 / sr
    rms = librosa.feature.rms(y=y, frame_length=FRAME, hop_length=HOP, center=True)[0]
    frame_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=HOP) * 1000.0
    sorted_rms = np.sort(rms)
    noise_floor = float(np.median(sorted_rms[: max(1, len(sorted_rms) // 3)]))
    threshold = max(noise_floor * 4.0, float(np.percentile(rms, 35.0)))
    segments = merge_mask(rms >= threshold, hop_ms)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP, aggregate=np.median, detrend=True)
    onset_times = librosa.frames_to_time(np.arange(len(onset_env)), sr=sr, hop_length=HOP) * 1000.0
    active_onsets = np.array([in_segments(float(value), segments, margin_ms=35.0) for value in onset_times])
    active_scores = onset_env[active_onsets]
    strong_cut = float(np.percentile(active_scores, 62.0)) if active_scores.size else 0.0
    normal_cut = float(np.percentile(active_scores, 35.0)) if active_scores.size else 0.0
    hard_cut = float(np.percentile(active_scores, 18.0)) if active_scores.size else 0.0
    def detect(delta: float, wait_ms: float) -> list[tuple[float, float]]:
        frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, hop_length=HOP, units="frames", backtrack=True, pre_max=4, post_max=4, pre_avg=8, post_avg=8, delta=max(delta, 0.02), wait=max(1, int(wait_ms / hop_ms)))
        raw: list[tuple[float, float]] = []
        for frame in frames:
            if frame >= len(onset_env):
                continue
            score = float(onset_env[frame])
            if score >= hard_cut:
                initial = float(onset_times[frame])
                refined = refine_to_energy(initial, frame_times, rms)
                raw.append((refined, score))
        return raw
    raw = detect(0.02, 55.0)
    strong = dedupe_scored([(time, score) for time, score in raw if score >= strong_cut], 165.0, segments)
    normal = dedupe_scored([(time, score) for time, score in raw if score >= normal_cut], 110.0, segments)
    hard = dedupe_scored([(time, score) for time, score in raw if score >= hard_cut], 70.0, segments)
    # Guarantee readable progression without inventing non-vocal notes.
    if len(strong) == 0 and raw:
        strong = dedupe_scored(raw, 220.0, segments)
    if len(normal) <= len(strong):
        normal = dedupe_scored(raw, 95.0, segments)
    if len(hard) <= len(normal):
        hard = dedupe_scored(raw, 60.0, segments)
    onsets = {"easy": [time for time, _ in strong], "normal": [time for time, _ in normal], "hard": [time for time, _ in hard]}
    return {
        "duration_ms": round(float(len(y) / sr * 1000.0), 3),
        "sample_rate": sr,
        "frame_ms": round(FRAME * 1000.0 / sr, 3),
        "hop_ms": round(hop_ms, 3),
        "noise_floor_rms": round(noise_floor, 8),
        "active_threshold_rms": round(threshold, 8),
        "segments": [{"start_ms": round(start, 3), "end_ms": round(end, 3)} for start, end in segments],
        "onsets": onsets,
        "onset_counts": {key: len(value) for key, value in onsets.items()},
        "refinement": "backtracked onset -> local vocal RMS peak within 55ms",
        "source_policy": "VOICE_ONLY; all timestamps derive from Voices-*.ogg",
    }


def make_chart(analysis: dict[str, Any]) -> dict[str, Any]:
    notes = {}
    for difficulty in ("easy", "normal", "hard"):
        notes[difficulty] = [{"t": round(float(time_ms), 3), "d": index % 4, "_source": "voice", "_voice_event_id": f"v262-{difficulty}-{index + 1:05d}"} for index, time_ms in enumerate(analysis["onsets"][difficulty])]
    return {"version": "2.0.0", "scrollSpeed": {"easy": 0.9, "normal": 1.0, "hard": 1.12}, "events": [], "notes": notes, "candidateOnly": True, "generatedBy": "Vocal-only V2.6.2 backtracked RMS refinement", "sourcePolicy": "NO_INSTRUMENTAL_NOTES"}


def analyze_one(root: Path, song: str) -> dict[str, Any]:
    song_dir = root / "mods" / f"esperon-dano-{song}" / "songs" / song
    voices = sorted(song_dir.glob("Voices-*.ogg"))
    if len(voices) != 1:
        return {"song": song, "status": "ERROR", "errors": [f"vocal_sources={len(voices)}"]}
    try:
        analysis = analyze_voice(voices[0])
        output = root / "qa-lab" / "rebuild-v262" / "playstate-fix" / "vocal-only-v262" / song
        output.mkdir(parents=True, exist_ok=True)
        (output / "voice-activity.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (output / "chart-vocal-only.json").write_text(json.dumps(make_chart(analysis), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report = {"song": song, "status": "PASS", "source_vocal": str(voices[0].relative_to(root)), "source_vocal_sha256": sha(voices[0]), "analysis": analysis, "instrumental_used_for_generation": False, "manual_review_required": True}
        (output / "candidate-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"song": song, "status": "PASS", "onsets": analysis["onset_counts"], "output": str(output.relative_to(root))}
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
    payload = {"scope": "VOCAL_ONLY_REFINED_CANDIDATES_V262", "executed_at": datetime.now(timezone.utc).isoformat(), "target_version": "0.8.6", "mod_version": "2.6.2", "songs": len(rows), "passed": sum(row["status"] == "PASS" for row in rows), "status": "PASS_CANDIDATES_ISOLATED" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND", "rows": rows, "instrumental_used_for_generation": False, "promotion": "BLOCKED_UNTIL_ALL_GATES_PASS"}
    output = root / "qa-lab" / "rebuild-v262" / "playstate-fix" / "vocal-only-v262" / "candidate-summary-v262.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "passed": payload["passed"], "status": payload["status"], "instrumental_used_for_generation": payload["instrumental_used_for_generation"], "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS_CANDIDATES_ISOLATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
