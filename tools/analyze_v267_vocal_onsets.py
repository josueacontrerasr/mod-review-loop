#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import librosa
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ALIGN_ROOT = ROOT / "qa-lab" / "rebuild-v266" / "playstate-fix" / "syllable-candidates-small"
OUT_ROOT = ROOT / "qa-lab" / "rebuild-v267" / "phase2-vocal-onsets"
SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "si-te-vas", "solare",
    "tristella", "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]


def rms_track(audio: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray]:
    hop = max(160, int(sr * 0.01))
    frame = max(hop * 2, int(sr * 0.02))
    rms = librosa.feature.rms(y=audio, frame_length=frame, hop_length=hop, center=False)[0]
    times = (np.arange(len(rms)) * hop + frame / 2.0) / sr * 1000.0
    kernel = np.ones(3, dtype=np.float32) / 3.0
    return times, np.convolve(rms, kernel, mode="same")


def voiced_mask(rms: np.ndarray) -> tuple[np.ndarray, float]:
    if len(rms) == 0:
        return np.zeros(0, dtype=bool), 0.0
    noise = float(np.percentile(rms, 10))
    upper = float(np.percentile(rms, 95))
    threshold = max(noise * 3.5, noise + 0.08 * max(0.0, upper - noise), 0.008)
    return rms >= threshold, threshold


def merge_segments(times: np.ndarray, mask: np.ndarray, min_ms: float = 45.0, merge_gap_ms: float = 80.0) -> list[tuple[float, float]]:
    if len(mask) == 0:
        return []
    step = float(np.median(np.diff(times))) if len(times) > 1 else 10.0
    segments: list[tuple[float, float]] = []
    active = np.flatnonzero(mask)
    if len(active) == 0:
        return []
    start = int(active[0])
    prev = int(active[0])
    for index in active[1:]:
        index = int(index)
        if (index - prev) * step > merge_gap_ms:
            lo = float(times[start] - step / 2.0)
            hi = float(times[prev] + step / 2.0)
            if hi - lo >= min_ms:
                segments.append((max(0.0, lo), hi))
            start = index
        prev = index
    lo = float(times[start] - step / 2.0)
    hi = float(times[prev] + step / 2.0)
    if hi - lo >= min_ms:
        segments.append((max(0.0, lo), hi))
    return segments


def local_onset(start_ms: float, word_start: float, word_end: float, previous_start: float, next_start: float, times: np.ndarray, rms: np.ndarray, mask: np.ndarray) -> tuple[float, str]:
    lo = max(word_start, start_ms - 100.0, previous_start + 18.0)
    hi = min(word_end, start_ms + 125.0, next_start - 18.0)
    if hi <= lo or len(times) == 0:
        return round(start_ms, 3), "timestamp-fallback"
    indices = np.flatnonzero((times >= lo) & (times <= hi))
    if len(indices) == 0:
        return round(start_ms, 3), "timestamp-fallback"
    # Prefer the first reliable energy crossing. This avoids using the RMS
    # maximum as the onset, which is the common source of perceived delay.
    active = [int(i) for i in indices if mask[i]]
    if active:
        return round(float(times[active[0]]), 3), "rms-first-active"
    derivative = np.diff(np.log(np.maximum(rms[indices], 1e-6)), prepend=np.log(max(float(rms[indices[0]]), 1e-6)))
    best = int(indices[int(np.argmax(derivative))])
    return round(float(times[best]), 3), "rms-rise-fallback"


def local_end(start_ms: float, hinted_end: float, next_start: float, word_end: float, times: np.ndarray, mask: np.ndarray) -> tuple[float, str]:
    soft_word_limit = max(word_end, hinted_end) + 300.0
    upper = min(next_start - 15.0, start_ms + 1800.0, soft_word_limit, hinted_end + 1200.0)
    lo = min(start_ms + 25.0, upper)
    if upper <= lo or len(times) == 0:
        return round(max(start_ms + 45.0, min(hinted_end, start_ms + 220.0)), 3), "bounded-fallback"
    indices = np.flatnonzero((times >= lo) & (times <= upper))
    active = [int(i) for i in indices if mask[i]]
    if not active:
        return round(max(start_ms + 45.0, min(hinted_end, start_ms + 220.0)), 3), "bounded-fallback"
    # The last active frame before the next attack is the best evidence for a
    # sustained vowel tail. A 20 ms frame margin preserves consonant endings.
    return round(min(upper, float(times[active[-1]]) + 20.0), 3), "rms-last-active"


def analyze_song(song: str) -> dict[str, Any]:
    mod = ROOT / "mods" / f"esperon-dano-{song}"
    voice = sorted((mod / "songs" / song).glob("Voices-*.ogg"))[0]
    alignment_path = ALIGN_ROOT / song / "syllable-alignment.json"
    alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
    audio, sr = librosa.load(voice, sr=16000, mono=True)
    times, rms = rms_track(audio, sr)
    mask, threshold = voiced_mask(rms)
    segments = merge_segments(times, mask)
    syllables = sorted(alignment.get("syllables", []), key=lambda item: float(item.get("start_ms", 0.0)))
    starts = [float(item.get("start_ms", 0.0)) for item in syllables]
    rows: list[dict[str, Any]] = []
    onset_deltas: list[float] = []
    end_deltas: list[float] = []
    for index, item in enumerate(syllables):
        start = float(item.get("start_ms", 0.0))
        previous_start = starts[index - 1] if index else -1e9
        next_start = starts[index + 1] if index + 1 < len(starts) else float(alignment.get("duration_ms", len(audio) * 1000.0 / sr))
        word_start = float(item.get("word_start_ms", start))
        word_end = float(item.get("word_end_ms", start + 45.0))
        hinted_end = float(item.get("vocal_end_ms", word_end))
        audio_onset, onset_source = local_onset(start, word_start, word_end, previous_start, next_start, times, rms, mask)
        audio_end, end_source = local_end(start, hinted_end, next_start, word_end, times, mask)
        onset_delta = round(start - audio_onset, 3)
        end_delta = round(hinted_end - audio_end, 3)
        onset_deltas.append(onset_delta)
        end_deltas.append(end_delta)
        rows.append({
            "index": index,
            "text": item.get("text"),
            "vowel": item.get("vowel"),
            "chart_start_ms": round(start, 3),
            "audio_onset_ms": audio_onset,
            "onset_delta_chart_minus_audio_ms": onset_delta,
            "current_vocal_end_ms": round(hinted_end, 3),
            "audio_end_ms": audio_end,
            "end_delta_current_minus_audio_ms": end_delta,
            "current_hold_ms": round(float(item.get("hold_ms", 0.0) or 0.0), 3),
            "onset_source": onset_source,
            "end_source": end_source,
            "review": "WARNING_REVIEW" if abs(onset_delta) > 45.0 or abs(end_delta) > 80.0 else "PASS_AUTO",
        })
    positive_onset = [value for value in onset_deltas if value > 0]
    negative_onset = [value for value in onset_deltas if value < 0]
    payload = {
        "song": song,
        "voice": str(voice.relative_to(ROOT)),
        "voice_sha256": __import__("hashlib").sha256(voice.read_bytes()).hexdigest(),
        "duration_ms": round(len(audio) * 1000.0 / sr, 3),
        "sample_rate": sr,
        "rms_threshold": round(threshold, 6),
        "voiced_segments": len(segments),
        "syllables": len(rows),
        "onset_delay_count_gt_45ms": sum(1 for value in positive_onset if value > 45.0),
        "onset_early_count_gt_45ms": sum(1 for value in negative_onset if value < -45.0),
        "onset_delta_median_ms": round(float(np.median(onset_deltas)), 3) if onset_deltas else 0.0,
        "onset_delta_p95_ms": round(float(np.percentile(onset_deltas, 95)), 3) if onset_deltas else 0.0,
        "end_delta_median_ms": round(float(np.median(end_deltas)), 3) if end_deltas else 0.0,
        "end_delta_p95_abs_ms": round(float(np.percentile(np.abs(end_deltas), 95)), 3) if end_deltas else 0.0,
        "warning_rows": sum(1 for row in rows if row["review"] == "WARNING_REVIEW"),
        "rows": rows,
    }
    return payload


def main() -> int:
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(analyze_song, SONGS))
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    for row in rows:
        (OUT_ROOT / f"{row['song']}.json").write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "scope": "WIDE_RESEARCH_V267_VOCAL_ONSET_AND_END_ANALYSIS",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "base_release": "esperon-vslice-086-v2.6.6",
        "songs": len(rows),
        "parallel_workers": 8,
        "total_warning_rows": sum(row["warning_rows"] for row in rows),
        "rows": sorted([{key: value for key, value in row.items() if key != "rows"} for row in rows], key=lambda row: row["song"]),
    }
    output = OUT_ROOT / "summary.json"
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"scope": summary["scope"], "songs": summary["songs"], "warnings": summary["total_warning_rows"], "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
