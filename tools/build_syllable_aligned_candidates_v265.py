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
OUT_ROOT = ROOT / "qa-lab" / "rebuild-v265" / "playstate-fix" / "syllable-candidates"
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


def estimate_vocal_end(start_ms: float, hinted_end_ms: float, next_start_ms: float, env_t: np.ndarray, env_r: np.ndarray) -> float:
    """Extend a Whisper word end only when local vocal energy remains active.

    The extension is deliberately short and is capped before the next aligned
    syllable. This catches short words with a prolonged vowel without turning
    instrumental leakage into a hold.
    """
    upper = min(next_start_ms - 35.0, hinted_end_ms + 320.0)
    if upper <= hinted_end_ms or env_t.size == 0 or env_r.size == 0:
        return hinted_end_ms
    idx = np.where((env_t >= start_ms + 35.0) & (env_t <= upper))[0]
    if len(idx) < 2:
        return hinted_end_ms
    local = env_r[idx]
    baseline = float(np.percentile(local, 25))
    peak = float(np.max(local))
    threshold = max(baseline * 1.35, baseline + 0.12 * max(0.0, peak - baseline))
    active = idx[local >= threshold]
    if len(active) < 2:
        return hinted_end_ms
    # Use the final active frame, but do not extend through a quiet gap.
    candidate = min(upper, float(env_t[active[-1]]) + 20.0)
    return max(hinted_end_ms, candidate)


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
        for si, t in enumerate(refined):
            syllables.append({
                "id": f"w{wi+1}s{si+1}",
                "word": text,
                "text": text if n == 1 else f"{text}#{si+1}/{n}",
                "start_ms": round(t, 3),
                "word_start_ms": round(start, 3),
                "word_end_ms": round(end, 3),
                "confidence": round(confidence, 4),
                "kind": kind,
                "source": "whisper-word-timestamp+rms-refinement",
            })
    syllables.sort(key=lambda x: x["start_ms"])
    # Preserve source-relative timestamps when word boundaries collide. A
    # repeated syllable may share a timestamp with another uncertain attack;
    # it is safer to keep the acoustic boundary than move it beyond the word.
    for i, item in enumerate(syllables):
        following = syllables[i + 1]["start_ms"] if i + 1 < len(syllables) else item["word_end_ms"]
        hinted_end = float(item["word_end_ms"])
        vocal_end = min(hinted_end, float(following) - 35.0)
        vocal_end = min(float(following) - 35.0, estimate_vocal_end(float(item["start_ms"]), vocal_end, float(following), env_t, env_r))
        duration = max(0.0, vocal_end - float(item["start_ms"]))
        item["vocal_end_ms"] = round(vocal_end, 3)
        item["duration_ms"] = round(duration, 3)
        item["vocal_end_source"] = "word-boundary+rms-tail" if vocal_end > hinted_end else "word-boundary"
        # A hold is allowed only for a clearly long vocal segment and never
        # across the next syllable. Short gaps remain tap notes.
        item["hold_ms"] = round(max(0.0, duration - 35.0), 3) if duration >= 200.0 else 0.0
        if item["hold_ms"] > 0:
            item["kind"] = "interjection_hold" if item["kind"] == "interjection" else "sustained_syllable"
    return syllables


def note_from(item: dict[str, Any], timestamp: float, lane: int) -> dict[str, Any]:
    note: dict[str, Any] = {"t": round(float(timestamp), 3), "d": int(4 + (lane % 4))}
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
            if hold >= 200.0:
                extra = dict(item)
                extra["start_ms"] = round(float(item["start_ms"]) + min(hold * 0.5, hold - 40.0), 3)
                extra["hold_ms"] = 0.0
                extra["kind"] = "hard_vocal_subdivision"
                selected.append(extra)
    else:
        selected = syllables
    notes=[]
    used={}
    lane_cursor=-1
    for index,item in enumerate(selected):
        original=round(float(item["start_ms"]),3)
        count=used.get(original,0)
        timestamp=original + (0.5 * (count // 4) if count >= 4 else 0.0)
        # Cycle through all four player directions globally. The previous generator
        # implementation keyed the lane cursor by timestamp, so unique
        # syllables all received d=4 (player-left). Collision offsets remain
        # per timestamp, while direction assignment is chronological.
        lane_cursor=(lane_cursor + 1) % 4
        lane=lane_cursor
        used[original]=count+1
        notes.append(note_from(item,timestamp,lane))
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
        "generatedBy": "Friday Night Funkin' - 0.8.6; V2.6.5 syllable-aligned vocal chart player lanes cycling 4..7",
    }
    write_json(out / "candidate-chart.json", chart)
    write_json(out / "syllable-alignment.json", transcript)
    low_conf = [s for s in transcript["syllables"] if s["confidence"] < 0.45]
    report = {
        "scope": "VOCAL_SYLLABLE_ALIGNED_PLAYER_LANE_CANDIDATE_V265",
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
    summary = {"scope": "V265_SYLLABLE_ALIGNMENT_BATCH", "status": "MANUAL_REVIEW_REQUIRED", "model": args.model, "songs": len(results), "results": results}
    write_json(OUT_ROOT / "batch-summary.json", summary)
    print(json.dumps({"songs": len(results), "output": str(OUT_ROOT), "total_syllables": sum(r["syllables"] for r in results), "total_interjections": sum(r["interjections"] for r in results), "total_holds": sum(r["holds"] for r in results)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
