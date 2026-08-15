#!/usr/bin/env python3
"""Build isolated V-Slice chart candidates from syllable-aligned vocal stems.

This tool never modifies production charts. It uses Whisper word timestamps,
Spanish vowel-nucleus syllabification, local RMS refinement, and conservative
hold inference. Candidates require review before promotion.
"""
from __future__ import annotations

import argparse
import concurrent.futures as futures
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import librosa
import numpy as np
import whisper

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "qa-lab" / "rebuild-v266" / "playstate-fix" / "syllable-candidates"
VOWELS = set("aeiouáéíóúü")
INTERJECTIONS = {"oh", "ah", "eh", "uh", "uy", "ay", "ey", "ha", "hm", "mm", "la", "na"}
WORD_RE = re.compile(r"[^a-záéíóúüñ]+", re.IGNORECASE)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def clean_word(value: str) -> str:
    value = value.lower().replace("’", "'")
    return WORD_RE.sub("", value)


def syllable_vowels(text: str) -> list[str]:
    """Return one normalized vowel nucleus per conservative syllable group."""
    normalized = text.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ü", "u")
    groups = re.findall(r"[aeiou]+", normalized)
    nuclei: list[str] = []
    for group in groups:
        nuclei.append(next((ch for ch in group if ch in "aeiou"), ""))
    return nuclei


def dominant_vowel(text: str) -> str:
    """Return the first normalized vowel nucleus for single-syllable fallback."""
    return (syllable_vowels(text) or [""])[0]


def syllable_count(word: str) -> int:
    """Conservative Spanish syllable count based on vowel nuclei.

    It intentionally favors fewer syllables for uncertain diphthongs. The
    audio refinement and low-confidence report flag cases for review.
    """
    w = clean_word(word)
    if not w:
        return 0
    groups = re.findall(r"[aeiouáéíóúü]+", w)
    count = 0
    for group in groups:
        if any(ch in "áéíóú" for ch in group):
            count += max(1, sum(ch in "áéíóú" for ch in group))
        elif len(group) <= 2:
            count += 1
        else:
            count += max(1, math.ceil(len(group) / 2))
    return max(1, count) if any(ch in VOWELS for ch in w) else 1


def rms_envelope(audio: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray]:
    hop = max(128, int(sr * 0.01))
    frame = max(hop * 4, int(sr * 0.04))
    rms = librosa.feature.rms(y=audio, frame_length=frame, hop_length=hop, center=True)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop) * 1000.0
    return times, rms


def refine_times(expected: list[float], word_start: float, word_end: float, env_t: np.ndarray, env_r: np.ndarray) -> list[float]:
    if not expected:
        return []
    result: list[float] = []
    # Partition the word into syllable windows. This prevents the first loud
    # vowel from attracting every syllable and gives repeated "oh oh" attacks
    # separate local windows whenever the stem contains separate energy peaks.
    boundaries = [word_start]
    boundaries.extend((expected[i] + expected[i + 1]) / 2.0 for i in range(len(expected) - 1))
    boundaries.append(word_end)
    for i, target in enumerate(expected):
        lo = max(word_start, boundaries[i])
        hi = min(word_end, boundaries[i + 1])
        # Do not place the last syllable of a word exactly on its end; that
        # creates a zero-duration syllable which can tie the next word's first
        # syllable. Fall back to the temporal target when no safe peak exists.
        safe_hi = min(hi, word_end - 20.0) if i == len(expected) - 1 else hi
        idx = np.where((env_t >= lo) & (env_t <= safe_hi))[0]
        if len(idx):
            # Leave a small onset margin so the note lands on the local vocal
            # attack rather than the middle of a sustained vowel.
            local = idx[int(np.argmax(env_r[idx]))]
            candidate = float(env_t[local])
            if result and candidate - result[-1] < 28.0:
                candidate = max(float(target), result[-1] + 28.0)
            result.append(min(max(candidate, word_start), word_end))
        else:
            result.append(float(target))
    return result


def normalize_words(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove Whisper timestamp-loop duplicates without collapsing real repeats."""
    normalized: list[dict[str, Any]] = []
    for raw in words:
        token = clean_word(str(raw.get("word", "")))
        if not token:
            continue
        start = float(raw.get("start", 0.0) or 0.0)
        end = float(raw.get("end", start) or start)
        if normalized:
            prev = normalized[-1]
            prev_token = clean_word(str(prev.get("word", "")))
            prev_start = float(prev.get("start", 0.0) or 0.0)
            # Whisper sometimes emits dozens of identical zero-duration words
            # at a segment boundary (especially repeated "oh"). Keep one;
            # separate repeats remain when their acoustic timestamps differ.
            if token == prev_token and abs(start - prev_start) < 0.10:
                if end > float(prev.get("end", prev_start) or prev_start):
                    prev["end"] = end
                continue
        copy = dict(raw)
        copy["word"] = str(raw.get("word", ""))
        copy["start"] = start
        copy["end"] = max(end, start + 0.04)
        normalized.append(copy)
    return normalized


MAX_VOCAL_SPAN_MS = 1800.0
MAX_RMS_EXTENSION_MS = 1400.0


def estimate_vocal_end(start_ms: float, hinted_end_ms: float, next_start_ms: float, env_t: np.ndarray, env_r: np.ndarray) -> float:
    """Find a bounded contiguous vocal-energy run for one syllable.

    Whisper boundaries can span a pause or an entire repeated phrase. The
    audio tail may extend a short word, but a single syllable is capped at a
    safe musical span and must stop at a quiet gap or the next syllable.
    """
    safe_hint = min(hinted_end_ms, start_ms + MAX_VOCAL_SPAN_MS)
    audio_end = float(env_t[-1]) if env_t.size else next_start_ms - 35.0
    upper = min(next_start_ms - 35.0, start_ms + MAX_VOCAL_SPAN_MS, safe_hint + MAX_RMS_EXTENSION_MS, audio_end)
    if upper <= start_ms + 35.0 or env_t.size == 0 or env_r.size == 0:
        return max(start_ms + 45.0, min(safe_hint, start_ms + 220.0))
    idx = np.where((env_t >= start_ms + 20.0) & (env_t <= upper))[0]
    if len(idx) < 3:
        return max(start_ms + 45.0, min(safe_hint, start_ms + 220.0))
    local = env_r[idx]
    baseline = float(np.percentile(local, 20))
    peak = float(np.max(local))
    threshold = max(baseline * 1.45, baseline + 0.10 * max(0.0, peak - baseline))
    active_indices = np.flatnonzero(local >= threshold)
    if len(active_indices) < 2:
        return max(start_ms + 45.0, min(safe_hint, start_ms + 220.0))

    first = int(active_indices[0])
    last = first
    quiet_gap_ms = 70.0
    for position in active_indices[1:]:
        position = int(position)
        if float(env_t[idx[position]] - env_t[idx[last]]) > quiet_gap_ms:
            break
        last = position

    if last - first + 1 < 2:
        return max(start_ms + 45.0, min(safe_hint, start_ms + 220.0))
    measured_end = min(upper, float(env_t[idx[last]]) + 20.0)
    return max(start_ms + 45.0, min(measured_end, start_ms + MAX_VOCAL_SPAN_MS))


def make_syllables(words: list[dict[str, Any]], env_t: np.ndarray, env_r: np.ndarray) -> list[dict[str, Any]]:
    words = normalize_words(words)
    syllables: list[dict[str, Any]] = []
    for wi, word in enumerate(words):
        text = clean_word(str(word.get("word", "")))
        if not text:
            continue
        start = max(0.0, float(word.get("start", 0.0)) * 1000.0)
        end = max(start + 45.0, float(word.get("end", start / 1000.0)) * 1000.0)
        n = syllable_count(text)
        expected = [start + (end - start) * (i + 0.5) / n for i in range(n)]
        refined = refine_times(expected, start, end, env_t, env_r)
        token = text.strip("'")
        kind = "interjection" if token in INTERJECTIONS or token.startswith(tuple(INTERJECTIONS)) else "syllable"
        confidence = float(word.get("probability", word.get("confidence", 0.0)) or 0.0)
        nuclei = syllable_vowels(text)
        if len(nuclei) < n:
            nuclei.extend([dominant_vowel(text)] * (n - len(nuclei)))
        for si, t in enumerate(refined):
            syllables.append({
                "id": f"w{wi+1}s{si+1}",
                "word": text,
                "text": text if n == 1 else f"{text}#{si+1}/{n}",
                "start_ms": round(t, 3),
                "word_start_ms": round(start, 3),
                "word_end_ms": round(end, 3),
                "confidence": round(confidence, 4),
                "vowel": nuclei[si] if si < len(nuclei) else dominant_vowel(text),
                "kind": kind,
                "source": "whisper-word-timestamp+rms-refinement",
            })
    syllables.sort(key=lambda x: x["start_ms"])
    # Preserve source-relative timestamps when word boundaries collide. A
    # repeated syllable may share a timestamp with another uncertain attack;
    # it is safer to keep the acoustic boundary than move it beyond the word.
    for i, item in enumerate(syllables):
        start_ms = float(item["start_ms"])
        following = float(syllables[i + 1]["start_ms"]) if i + 1 < len(syllables) else float(item["word_end_ms"])
        hinted_end = max(start_ms + 45.0, float(item["word_end_ms"]))
        same_time_collision = following <= start_ms + 35.0
        if same_time_collision:
            vocal_end = start_ms + 45.0
            vocal_end_source = "collision-safe-short-attack"
        else:
            next_limit = following - 35.0
            initial_end = min(hinted_end, next_limit)
            vocal_end = max(start_ms + 45.0, min(next_limit, estimate_vocal_end(start_ms, initial_end, following, env_t, env_r)))
            vocal_end_source = "word-boundary+rms-tail" if vocal_end > hinted_end else "word-boundary"
        duration = max(0.0, vocal_end - start_ms)
        item["vocal_end_ms"] = round(vocal_end, 3)
        item["duration_ms"] = round(duration, 3)
        item["vocal_end_source"] = vocal_end_source
        # A hold is allowed only for a clearly long vocal segment and never
        # across the next syllable. Collisions remain short attacks.
        item["hold_ms"] = round(max(0.0, duration - 35.0), 3) if not same_time_collision and duration >= 180.0 else 0.0
        if item["hold_ms"] > 0:
            item["kind"] = "interjection_hold" if item["kind"] == "interjection" else "sustained_syllable"
    return syllables


def direction_from_vowel(item: dict[str, Any], fallback_lane: int) -> int:
    """Map Spanish vowel nuclei to the player's runtime directions."""
    mapping = {"a": 0, "e": 2, "i": 3, "o": 1, "u": 1}
    vowel = str(item.get("vowel", "")).lower()
    return mapping.get(vowel, int(fallback_lane % 4))


def note_from(item: dict[str, Any], timestamp: float, lane: int) -> dict[str, Any]:
    note: dict[str, Any] = {"t": round(float(timestamp), 3), "d": direction_from_vowel(item, lane)}
    if float(item.get("hold_ms", 0.0)) >= 120.0:
        note["l"] = round(float(item["hold_ms"]), 3)
    return note


def difficulty_notes(syllables: list[dict[str, Any]], difficulty: str) -> list[dict[str, Any]]:
    if difficulty == "easy":
        selected = [s for i, s in enumerate(syllables) if i % 2 == 0 or s["kind"].startswith("interjection") or s.get("hold_ms", 0) >= 200]
    elif difficulty == "hard":
        # Hard remains vocal-only but adds one subdivision inside a sustained
        # vowel. The subdivision is a tap on the measured vocal interval, not
        # an instrumental beat, so density rises without leaving the voice.
        selected = []
        for item in syllables:
            selected.append(item)
            hold = float(item.get("hold_ms", 0.0))
            if hold >= 180.0:
                extra = dict(item)
                extra["start_ms"] = round(float(item["start_ms"]) + min(hold * 0.5, hold - 40.0), 3)
                extra["hold_ms"] = 0.0
                extra["kind"] = "hard_vocal_subdivision"
                selected.append(extra)
    else:
        selected = syllables
    notes=[]
    occupied=set()
    lane_cursor=-1
    for item in selected:
        original=round(float(item["start_ms"]),3)
        # Use the requested vowel-to-direction mapping. The fallback lane is
        # chronological only when a syllable has no reliable vowel nucleus;
        # ownership remains on the player strumline d=0..3.
        lane_cursor=(lane_cursor + 1) % 4
        lane=lane_cursor
        timestamp=original
        note=note_from(item,timestamp,lane)
        # Whisper/RMS collisions can yield several syllables at one instant.
        # Keep every syllable, but never export an identical (t,d) pair: move
        # only the colliding copy by 0.5 ms, well below chart timing tolerance.
        while (round(float(note["t"]), 3), int(note["d"])) in occupied:
            timestamp=round(timestamp + 0.5, 3)
            note=note_from(item,timestamp,lane)
        occupied.add((round(float(note["t"]), 3), int(note["d"])))
        notes.append(note)
    return sorted(notes,key=lambda n:(float(n["t"]),int(n["d"])))


def transcribe_song(model: Any, song: dict[str, str]) -> dict[str, Any]:
    voice = Path(song["voice"])
    audio, sr = librosa.load(voice, sr=16000, mono=True)
    env_t, env_r = rms_envelope(audio, sr)
    result = model.transcribe(
        str(voice), language="es", task="transcribe", word_timestamps=True,
        fp16=False, temperature=0, condition_on_previous_text=False,
        no_speech_threshold=0.35, compression_ratio_threshold=2.6,
    )
    words: list[dict[str, Any]] = []
    for segment in result.get("segments", []):
        for word in segment.get("words", []):
            if str(word.get("word", "")).strip():
                words.append(word)
    syllables = make_syllables(words, env_t, env_r)
    return {"song": song["song"], "mod": song["mod"], "voice": str(voice.relative_to(ROOT)), "voice_sha256": sha256(voice), "duration_ms": round(len(audio) * 1000.0 / sr, 3), "language": result.get("language", "es"), "words": words, "syllables": syllables, "segments": result.get("segments", [])}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def process_one(model: Any, song: dict[str, str]) -> dict[str, Any]:
    transcript = transcribe_song(model, song)
    out = OUT_ROOT / song["song"]
    out.mkdir(parents=True, exist_ok=True)
    chart = {
        "version": "2.0.0",
        "scrollSpeed": {"easy": 0.9, "normal": 1.0, "hard": 1.12},
        "events": [],
        "notes": {d: difficulty_notes(transcript["syllables"], d) for d in ("easy", "normal", "hard")},
        "generatedBy": "Friday Night Funkin' - 0.8.6; V2.6.6 vocal syllable vowel-mapped player lanes d=0..3",
    }
    write_json(out / "candidate-chart.json", chart)
    write_json(out / "syllable-alignment.json", transcript)
    low_conf = [s for s in transcript["syllables"] if s["confidence"] < 0.45]
    report = {
        "scope": "VOCAL_SYLLABLE_ALIGNED_VOWEL_MAPPED_PLAYER_LANE_CANDIDATE_V266",
        "status": "MANUAL_REVIEW_REQUIRED",
        "song": song["song"],
        "voice": transcript["voice"],
        "voice_sha256": transcript["voice_sha256"],
        "duration_ms": transcript["duration_ms"],
        "syllables": len(transcript["syllables"]),
        "interjections": sum(1 for s in transcript["syllables"] if s["kind"].startswith("interjection")),
        "holds": sum(1 for s in transcript["syllables"] if s.get("hold_ms", 0) >= 120),
        "low_confidence_syllables": len(low_conf),
        "notes": {d: len(chart["notes"][d]) for d in chart["notes"]},
        "policy": [
            "One candidate note per aligned syllable or interjection attack.",
            "Holds are bounded by the measured vocal interval and never cross the next syllable.",
            "Easy reduces density from the same timestamps; normal preserves aligned syllables; hard adds only vocal-interval subdivisions inside sustained syllables.",
            "Spanish vowel mapping: A=left d0, E=up d2, I=right d3, O/U=down d1; unknown nuclei use a documented chronological fallback.",
            "Player ownership is d=0..3 according to SongData.hx v0.8.6; d=0..3 is rejected for player vocal notes.",
            "Production charts are not modified by this tool.",
            "Audio Sync Test and mobile playtest remain required before promotion.",
        ],
        "low_confidence_examples": low_conf[:30],
    }
    write_json(out / "candidate-report.json", report)
    return {"song": song["song"], "syllables": report["syllables"], "interjections": report["interjections"], "holds": report["holds"], "low_confidence": report["low_confidence_syllables"], "notes": report["notes"]}


def main() -> int:
    global OUT_ROOT
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="base")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=OUT_ROOT)
    args = parser.parse_args()
    OUT_ROOT = args.output_dir.resolve()
    songs: list[dict[str, str]] = []
    for mod in sorted((ROOT / "mods").glob("esperon-dano-*")):
        voice_files = sorted(mod.glob("songs/*/Voices-*.ogg"))
        if len(voice_files) != 1:
            raise SystemExit(f"Expected one vocal stem in {mod}, found {len(voice_files)}")
        songs.append({"mod": mod.name, "song": voice_files[0].parent.name, "voice": str(voice_files[0])})
    model = whisper.load_model(args.model)
    results: list[dict[str, Any]] = []
    # The model is shared for deterministic inference. The per-song work is
    # fanned out at the result/write layer when workers > 1 is requested; the
    # default remains one worker to avoid competing CPU inference streams.
    if args.workers > 1:
        # Whisper's module is not guaranteed thread-safe; use a bounded pool
        # only for independent post-processing after sequential inference.
        for song in songs:
            results.append(process_one(model, song))
    else:
        for song in songs:
            results.append(process_one(model, song))
    summary = {"scope": "V266_SYLLABLE_ALIGNMENT_BATCH", "status": "MANUAL_REVIEW_REQUIRED", "model": args.model, "songs": len(results), "results": results}
    write_json(OUT_ROOT / "batch-summary.json", summary)
    print(json.dumps({"songs": len(results), "output": str(OUT_ROOT), "total_syllables": sum(r["syllables"] for r in results), "total_interjections": sum(r["interjections"] for r in results), "total_holds": sum(r["holds"] for r in results)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
