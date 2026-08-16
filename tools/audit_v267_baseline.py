#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ALIGN_ROOT = ROOT / "qa-lab" / "rebuild-v266" / "playstate-fix" / "syllable-candidates-small"
SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "si-te-vas", "solare",
    "tristella", "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]
DIFFS = ("easy", "normal", "hard")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe_audio(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_name,sample_rate,channels", "-of", "json", str(path),
    ]
    try:
        raw = subprocess.check_output(command, text=True)
        data = json.loads(raw)
        stream = (data.get("streams") or [{}])[0]
        return {
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256(path),
            "duration_ms": round(float((data.get("format") or {}).get("duration", 0.0)) * 1000.0, 3),
            "codec": stream.get("codec_name"),
            "sample_rate": stream.get("sample_rate"),
            "channels": stream.get("channels"),
        }
    except Exception as exc:
        return {"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "error": str(exc)}


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lo = math.floor(position)
    hi = math.ceil(position)
    if lo == hi:
        return round(ordered[lo], 3)
    return round(ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo), 3)


def chart_stats(notes: list[dict[str, Any]], syllables: list[dict[str, Any]], audio_duration_ms: float) -> dict[str, Any]:
    times = [float(note.get("t", -1.0)) for note in notes]
    lanes = [int(note.get("d", -1)) for note in notes]
    holds = [float(note.get("l", 0.0) or 0.0) for note in notes if float(note.get("l", 0.0) or 0.0) > 0]
    duplicates = len(times) - len({(round(t, 3), lane) for t, lane in zip(times, lanes)})
    order_violations = sum(1 for prev, current in zip(times, times[1:]) if current < prev)
    outside_audio = sum(1 for t in times if t < 0 or t >= audio_duration_ms)
    starts = [float(item.get("start_ms", 0.0)) for item in syllables]
    intervals = [(float(item.get("start_ms", 0.0)) - 45.0, float(item.get("vocal_end_ms", item.get("start_ms", 0.0))) + 45.0) for item in syllables]
    spans = [(float(item.get("start_ms", 0.0)) - 10.0, float(item.get("vocal_end_ms", item.get("start_ms", 0.0))) + 20.0) for item in syllables]
    nearest_errors = []
    outside_vocal = 0
    unaligned = 0
    bad_holds = 0
    if starts:
        for note in notes:
            t = float(note.get("t", -1.0))
            nearest_errors.append(min(abs(t - start) for start in starts))
            if not any(lo <= t <= hi for lo, hi in intervals):
                outside_vocal += 1
            if min(abs(t - start) for start in starts) > 1.0 and not any(lo <= t <= hi for lo, hi in spans):
                unaligned += 1
            length = float(note.get("l", 0.0) or 0.0)
            if length:
                candidates = [item for item in syllables if abs(float(item.get("start_ms", 0.0)) - t) <= 1.0]
                if candidates:
                    end = t + length
                    vocal_end = max(float(item.get("vocal_end_ms", t)) for item in candidates)
                    if end > vocal_end + 50.0:
                        bad_holds += 1
    runs = []
    if lanes:
        current_lane = lanes[0]
        current_length = 1
        for lane in lanes[1:]:
            if lane == current_lane:
                current_length += 1
            else:
                runs.append((current_lane, current_length))
                current_lane = lane
                current_length = 1
        runs.append((current_lane, current_length))
    return {
        "notes": len(notes),
        "lanes": sorted(set(lanes)),
        "duplicates_t_d": duplicates,
        "order_violations": order_violations,
        "outside_audio": outside_audio,
        "holds": len(holds),
        "hold_max_ms": round(max(holds, default=0.0), 3),
        "hold_p95_ms": percentile(holds, 0.95),
        "same_lane_max_run": max((run[1] for run in runs), default=0),
        "same_lane_run_p95": percentile([float(run[1]) for run in runs], 0.95),
        "vocal_outside_interval": outside_vocal,
        "unaligned_to_syllable": unaligned,
        "bad_holds": bad_holds,
        "median_nearest_syllable_error_ms": round(median(nearest_errors), 3) if nearest_errors else 0.0,
        "p95_nearest_syllable_error_ms": percentile(nearest_errors, 0.95),
        "max_nearest_syllable_error_ms": round(max(nearest_errors, default=0.0), 3),
    }


def audit_song(song: str) -> dict[str, Any]:
    mod = ROOT / "mods" / f"esperon-dano-{song}"
    song_dir = mod / "songs" / song
    voice = sorted(song_dir.glob("Voices-*.ogg"))[0]
    inst = song_dir / "Inst.ogg"
    chart_path = mod / "data" / "songs" / song / f"{song}-chart.json"
    metadata_path = mod / "data" / "songs" / song / f"{song}-metadata.json"
    alignment_path = ALIGN_ROOT / song / "syllable-alignment.json"
    chart = json.loads(chart_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
    voice_info = probe_audio(voice)
    inst_info = probe_audio(inst)
    duration_ms = float(voice_info.get("duration_ms", alignment.get("duration_ms", 0.0)))
    difficulty_stats = {diff: chart_stats(chart.get("notes", {}).get(diff, []), alignment.get("syllables", []), duration_ms) for diff in DIFFS}
    return {
        "song": song,
        "mod": mod.name,
        "audio": {"voice": voice_info, "instrumental": inst_info},
        "metadata": {
            "version": metadata.get("version"),
            "generatedBy": metadata.get("generatedBy"),
            "timeChanges": metadata.get("timeChanges"),
            "instrumentalOffset": metadata.get("playData", {}).get("instrumentalOffset"),
            "vocalOffset": metadata.get("playData", {}).get("vocalOffset"),
        },
        "chart": {
            "version": chart.get("version"),
            "generatedBy": chart.get("generatedBy"),
            "scrollSpeed": chart.get("scrollSpeed"),
            "difficulties": difficulty_stats,
        },
        "alignment": {
            "voice_sha256": alignment.get("voice_sha256"),
            "duration_ms": alignment.get("duration_ms"),
            "syllables": len(alignment.get("syllables", [])),
            "holds": sum(1 for item in alignment.get("syllables", []) if float(item.get("hold_ms", 0.0) or 0.0) > 0),
        },
    }


def main() -> int:
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(audit_song, SONGS))
    payload = {
        "scope": "WIDE_RESEARCH_V266_BASELINE_FOR_V267",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "base_release": "esperon-vslice-086-v2.6.6",
        "target_version": "2.6.7",
        "songs": len(rows),
        "parallel_workers": 8,
        "production_untouched": True,
        "rows": sorted(rows, key=lambda row: row["song"]),
    }
    output = ROOT / "qa-lab" / "rebuild-v267" / "phase1-baseline-v266.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"scope": payload["scope"], "songs": payload["songs"], "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
