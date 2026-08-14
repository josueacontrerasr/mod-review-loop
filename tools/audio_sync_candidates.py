#!/usr/bin/env python3
"""Genera evidencia y charts candidatos V-Slice sin modificar charts de producción.

Los onsets de una mezcla completa son candidatos rítmicos, no prueba de actividad vocal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import librosa
import numpy as np

SAMPLE_RATE = 22050
HOP_LENGTH = 256
MIN_NOTE_SPACING_MS = 150.0


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def robust_bpm_from_beats(beat_ms: list[float]) -> float | None:
    if len(beat_ms) < 3:
        return None
    intervals = np.diff(np.asarray(beat_ms))
    intervals = intervals[(intervals > 200.0) & (intervals < 2000.0)]
    if not len(intervals):
        return None
    return float(60000.0 / np.median(intervals))


def select_candidates(onsets: list[float], duration_ms: float) -> list[float]:
    selected: list[float] = []
    for timestamp in onsets:
        if timestamp < 1500.0 or timestamp >= duration_ms - 50.0:
            continue
        if not selected or timestamp - selected[-1] >= MIN_NOTE_SPACING_MS:
            selected.append(round(timestamp, 3))
    return selected


def difficulty_notes(times: list[float], difficulty: str) -> list[dict[str, float | int]]:
    if difficulty == "easy":
        selected = times[::2]
    elif difficulty == "normal":
        selected = [time for index, time in enumerate(times) if index % 4 != 3]
    else:
        selected = times
    notes: list[dict[str, float | int]] = []
    for index, timestamp in enumerate(selected):
        notes.append({"t": timestamp, "d": 4 + (index % 4)})
    return notes


def nearest_distances(points: list[float], references: list[float]) -> list[float]:
    if not references:
        return []
    result = []
    cursor = 0
    for point in points:
        while cursor + 1 < len(references) and abs(references[cursor + 1] - point) <= abs(references[cursor] - point):
            cursor += 1
        result.append(abs(references[cursor] - point))
    return result


def analyze(mod: Path, root: Path, output_root: Path, vocal_stem: Path | None = None) -> dict:
    song_dirs = [path for path in (mod / "data" / "songs").iterdir() if path.is_dir()]
    if len(song_dirs) != 1:
        raise ValueError(f"{mod.name}: se esperaba exactamente una canción")
    song_dir = song_dirs[0]
    song = song_dir.name
    audio = mod / "songs" / song / "Inst.ogg"
    manifest_path = root / "sync-candidates" / "input-manifests" / f"{song}.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if hash_file(audio) != manifest["final_audio"]["sha256"]:
        raise ValueError(f"{song}: el hash del audio cambió respecto al manifiesto")
    analysis_audio = vocal_stem if vocal_stem and vocal_stem.is_file() else audio
    analysis_mode = "VOCAL_STEM" if analysis_audio != audio else "FULL_MIX_PROXY"
    y, sr = librosa.load(analysis_audio, sr=SAMPLE_RATE, mono=True)
    duration_ms = len(y) * 1000.0 / sr
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP_LENGTH)
    onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, hop_length=HOP_LENGTH, backtrack=True, units="frames")
    onset_ms = [round(float(frame) * HOP_LENGTH * 1000.0 / sr, 3) for frame in onset_frames]
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=HOP_LENGTH)
    beat_ms = [round(float(frame) * HOP_LENGTH * 1000.0 / sr, 3) for frame in beat_frames]
    bpm_tracker = float(np.asarray(tempo).reshape(-1)[0])
    bpm_median = robust_bpm_from_beats(beat_ms)
    bpm_delta_pct = None if bpm_median is None else round(abs(bpm_tracker - bpm_median) / max(abs(bpm_tracker), 0.001) * 100.0, 3)
    candidates = select_candidates(onset_ms, duration_ms)
    chart = {
        "version": "2.0.0",
        "scrollSpeed": {"easy": 0.9, "normal": 1.0, "hard": 1.12},
        "events": [],
        "notes": {difficulty: difficulty_notes(candidates, difficulty) for difficulty in ("easy", "normal", "hard")},
        "candidateOnly": True,
        "generatedBy": "audio_sync_candidates.py — full-mix onset candidates; not approved for production"
    }
    normal_times = [float(note["t"]) for note in chart["notes"]["normal"]]
    distances = nearest_distances(normal_times, onset_ms)
    output = output_root / song
    anchors = [{"section": f"candidate-{index // 8 + 1}", "label": f"full-mix-onset-{index + 1}", "expected_ms": timestamp, "direction": 4 + (index % 4), "evidence": "AUTO_FULL_MIX_CANDIDATE"} for index, timestamp in enumerate(candidates[::8])]
    report = {
        "scope": "AUDIO_SYNC_CANDIDATE_ONLY",
        "status": "MANUAL_REVIEW_REQUIRED",
        "song": song,
        "mod": mod.name,
        "analysis_mode": analysis_mode,
        "audio": {"path": audio.relative_to(root).as_posix(), "sha256": hash_file(audio), "duration_ms": round(duration_ms, 3), "sample_rate": sr},
        "analysis_audio": {"path": analysis_audio.relative_to(root).as_posix(), "sha256": hash_file(analysis_audio)},
        "parameters": {"hop_length": HOP_LENGTH, "sample_rate": SAMPLE_RATE, "minimum_note_spacing_ms": MIN_NOTE_SPACING_MS},
        "tempo": {"librosa_beat_bpm": round(bpm_tracker, 3), "median_beat_interval_bpm": None if bpm_median is None else round(bpm_median, 3), "agreement_delta_percent": bpm_delta_pct},
        "counts": {"onsets": len(onset_ms), "beats": len(beat_ms), "candidate_base_notes": len(candidates), "easy_notes": len(chart["notes"]["easy"]), "normal_notes": len(chart["notes"]["normal"]), "hard_notes": len(chart["notes"]["hard"])},
        "candidate_self_coherence": {"mean_distance_to_detected_onset_ms": None if not distances else round(float(np.mean(distances)), 3), "max_distance_to_detected_onset_ms": None if not distances else round(float(np.max(distances)), 3)},
        "promotion_blockers": ([
            "El stem separado puede contener sangrado instrumental, coros o artefactos y no identifica por sí solo personaje/strumline.",
            "Falta Audio Sync Test documentado en Chart Editor.",
            "Falta playtest documentado en FNF Mobile V-Slice 0.8.6."
        ] if analysis_mode == "VOCAL_STEM" else [
            "La mezcla completa no identifica de forma fiable qué picos pertenecen a voces.",
            "No hay stems vocales distribuidos y verificados por strumline.",
            "Falta Audio Sync Test documentado en Chart Editor.",
            "Falta playtest documentado en FNF Mobile V-Slice 0.8.6."
        ]),
        "proposed_metadata_patch": {"timeChanges": [{"t": 0, "b": 0, "bpm": round(bpm_tracker, 3), "bt": [4, 4, 4, 4]}], "status": "CANDIDATE_DO_NOT_APPLY_AUTOMATICALLY"}
    }
    write_json(output / "candidate-chart.json", chart)
    write_json(output / "candidate-anchors.json", {"anchors": anchors})
    write_json(output / "sync-candidate-report.json", report)
    return {"song": song, "status": report["status"], "candidate_notes": len(candidates), "audio_sha256": report["audio"]["sha256"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--mod", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("sync-candidates/results"))
    parser.add_argument("--vocal-stem", type=Path, help="Stem vocal aislado; se usa solo para candidatos.")
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    vocal_stem = args.vocal_stem.resolve() if args.vocal_stem else None
    result = analyze(args.mod.resolve(), root, output, vocal_stem)
    print(json.dumps(result, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
