#!/usr/bin/env python3
"""Genera evidencia candidata de actividad vocal; no edita charts ni declara sincronía."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import librosa
import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def intervals_from_mask(mask: np.ndarray, hop_ms: float, min_ms: float, merge_gap_ms: float) -> list[dict[str, float]]:
    raw: list[tuple[int, int]] = []
    start: int | None = None
    for idx, active in enumerate(mask):
        if active and start is None:
            start = idx
        elif not active and start is not None:
            raw.append((start, idx))
            start = None
    if start is not None:
        raw.append((start, len(mask)))
    merged: list[tuple[int, int]] = []
    for begin, end in raw:
        if merged and (begin - merged[-1][1]) * hop_ms <= merge_gap_ms:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((begin, end))
    report: list[dict[str, float]] = []
    for begin, end in merged:
        start_ms, end_ms = begin * hop_ms, end * hop_ms
        if end_ms - start_ms >= min_ms:
            report.append({"start_ms": round(start_ms, 3), "end_ms": round(end_ms, 3), "duration_ms": round(end_ms - start_ms, 3)})
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vocal_stem", type=Path)
    parser.add_argument("reference_audio", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    vocal, sr = librosa.load(args.vocal_stem, sr=22050, mono=True)
    reference, ref_sr = librosa.load(args.reference_audio, sr=22050, mono=True)
    frame_length, hop_length = 2048, 256
    rms = librosa.feature.rms(y=vocal, frame_length=frame_length, hop_length=hop_length)[0]
    db = librosa.amplitude_to_db(np.maximum(rms, 1e-10), ref=np.max)
    threshold_db = float(np.percentile(db, 62))
    mask = db >= threshold_db
    hop_ms = hop_length * 1000.0 / sr
    segments = intervals_from_mask(mask, hop_ms, min_ms=140.0, merge_gap_ms=180.0)

    onset_frames = librosa.onset.onset_detect(y=vocal, sr=sr, hop_length=hop_length, backtrack=True, units="frames")
    onset_ms = [round(float(frame) * hop_ms, 3) for frame in onset_frames]
    tempo, beat_frames = librosa.beat.beat_track(y=reference, sr=ref_sr, hop_length=hop_length)
    bpm = float(np.asarray(tempo).reshape(-1)[0])
    beat_ms = [round(float(frame) * hop_ms, 3) for frame in beat_frames]

    payload = {
        "scope": "AUTO_VOCAL_ACTIVITY_CANDIDATES_ONLY",
        "status": "REQUIRES_HUMAN_MUSICAL_REVIEW",
        "vocal_stem": str(args.vocal_stem),
        "vocal_stem_sha256": sha256(args.vocal_stem),
        "reference_audio": str(args.reference_audio),
        "reference_audio_sha256": sha256(args.reference_audio),
        "sample_rate": sr,
        "duration_ms": round(len(vocal) * 1000.0 / sr, 3),
        "activity_threshold_db_relative_to_peak": round(threshold_db, 3),
        "candidate_vocal_segments": segments,
        "candidate_vocal_onsets_ms": onset_ms,
        "beat_tracker_bpm_candidate": round(bpm, 3),
        "beat_candidates_ms": beat_ms,
        "limitations": [
            "Los segmentos y onsets detectados no prueban cantante, sílaba, dirección ni strumline.",
            "Todo anclaje debe revisarse contra el OGG final y el Chart Editor antes de editar timeChanges, offsets o notas.",
            "Audio Sync Test y playtest móvil siguen siendo obligatorios para declarar sincronización."
        ]
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"segments": len(segments), "onsets": len(onset_ms), "bpm": round(bpm, 3)}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
