#!/usr/bin/env python3
"""Compare production chart note times against an identified vocal stem.

This is evidence only. It never edits metadata, charts, audio, BPM, or offsets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import librosa
import numpy as np

SAMPLE_RATE = 22050
HOP_LENGTH = 256
MATCH_WINDOW_MS = 120.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def nearest_distances(points: list[float], refs: np.ndarray) -> list[float]:
    if not points or not len(refs):
        return []
    values = np.asarray(points, dtype=float)
    indexes = np.searchsorted(refs, values, side="left")
    indexes = np.clip(indexes, 0, len(refs) - 1)
    prev = np.clip(indexes - 1, 0, len(refs) - 1)
    return np.minimum(np.abs(values - refs[indexes]), np.abs(values - refs[prev])).tolist()


def quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"mean_ms": None, "median_ms": None, "p90_ms": None, "max_ms": None}
    arr = np.asarray(values, dtype=float)
    return {
        "mean_ms": round(float(np.mean(arr)), 3),
        "median_ms": round(float(np.median(arr)), 3),
        "p90_ms": round(float(np.percentile(arr, 90)), 3),
        "max_ms": round(float(np.max(arr)), 3),
    }


def active_segments(y: np.ndarray, sr: int) -> list[tuple[float, float]]:
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=HOP_LENGTH)[0]
    db = librosa.amplitude_to_db(np.maximum(rms, 1e-10), ref=np.max)
    mask = db >= np.percentile(db, 62)
    raw: list[tuple[int, int]] = []
    start: int | None = None
    for idx, value in enumerate(mask):
        if bool(value) and start is None:
            start = idx
        elif not bool(value) and start is not None:
            raw.append((start, idx))
            start = None
    if start is not None:
        raw.append((start, len(mask)))
    result: list[tuple[float, float]] = []
    for begin, end in raw:
        start_ms = begin * HOP_LENGTH * 1000.0 / sr
        end_ms = end * HOP_LENGTH * 1000.0 / sr
        if end_ms - start_ms >= 140.0:
            if result and start_ms - result[-1][1] <= 180.0:
                result[-1] = (result[-1][0], end_ms)
            else:
                result.append((start_ms, end_ms))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--mod", type=Path, required=True)
    parser.add_argument("--vocal-stem", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chart", type=Path, help="Chart alternativo aislado; por defecto usa el chart de producción")
    args = parser.parse_args()
    root = args.root.resolve()
    mod = args.mod.resolve()
    stem = args.vocal_stem.resolve()
    song_dirs = [p for p in (mod / "data/songs").iterdir() if p.is_dir()]
    if len(song_dirs) != 1:
        raise SystemExit(f"Se esperaba una canción en {mod}")
    song_dir = song_dirs[0]
    song = song_dir.name
    chart_path = args.chart.resolve() if args.chart else song_dir / f"{song}-chart.json"
    audio = mod / "songs" / song / "Inst.ogg"
    if not stem.is_file():
        raise SystemExit(f"No existe el stem vocal: {stem}")
    y, sr = librosa.load(stem, sr=SAMPLE_RATE, mono=True)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP_LENGTH)
    onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, hop_length=HOP_LENGTH, backtrack=True, units="frames")
    onset_ms = np.asarray(sorted({round(float(f) * HOP_LENGTH * 1000.0 / sr, 3) for f in onset_frames}), dtype=float)
    segments = active_segments(y, sr)
    chart = json.loads(chart_path.read_text(encoding="utf-8"))
    per_diff: dict[str, object] = {}
    for difficulty, entries in chart.get("notes", {}).items():
        times = sorted(float(note["t"]) for note in entries if isinstance(note, dict) and "t" in note)
        distances = nearest_distances(times, onset_ms)
        in_activity = sum(1 for t in times if any(start <= t <= end for start, end in segments))
        matched = sum(1 for d in distances if d <= MATCH_WINDOW_MS)
        per_diff[difficulty] = {
            "notes": len(times),
            "notes_in_vocal_activity_segments": in_activity,
            "activity_coverage_percent": round(100.0 * in_activity / len(times), 3) if times else None,
            "notes_with_nearest_vocal_onset_within_120ms": matched,
            "nearest_onset_match_percent": round(100.0 * matched / len(times), 3) if times else None,
            "nearest_onset_distance": quantiles(distances),
            "first_note_ms": round(times[0], 3) if times else None,
            "last_note_ms": round(times[-1], 3) if times else None,
        }
    payload = {
        "scope": "CHART_VOCAL_ALIGNMENT_EVIDENCE_ONLY",
        "status": "REQUIRES_AUDIO_SYNC_TEST_AND_MOBILE_PLAYTEST",
        "song": song,
        "mod": mod.name,
        "production_audio": {"path": str(audio.relative_to(root)), "sha256": sha256(audio)},
        "chart_under_test": {"path": str(chart_path.relative_to(root)) if chart_path.is_relative_to(root) else str(chart_path), "kind": "isolated_candidate" if args.chart else "production"},
        "vocal_stem": {"path": str(stem.relative_to(root)), "sha256": sha256(stem), "sample_rate": sr, "duration_ms": round(len(y) * 1000.0 / sr, 3)},
        "parameters": {"sample_rate": SAMPLE_RATE, "hop_length": HOP_LENGTH, "match_window_ms": MATCH_WINDOW_MS, "onset_detector": "librosa.onset_detect(backtrack=true)"},
        "vocal_onsets": {"count": int(len(onset_ms)), "times_ms": [float(x) for x in onset_ms], "activity_segments": [{"start_ms": round(a, 3), "end_ms": round(b, 3)} for a, b in segments]},
        "difficulties": per_diff,
        "limitations": [
            "Un onset no demuestra que sea una sílaba ni asigna personaje o dirección.",
            "La separación Demucs puede contener sangrado, coros y artefactos.",
            "Las métricas no sustituyen Audio Sync Test del Chart Editor ni playtest en FNF Mobile V-Slice 0.8.6.",
            "No se modificó ningún chart, BPM, offset ni audio.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"song": song, "onsets": int(len(onset_ms)), "difficulties": list(per_diff), "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
