#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ALIGN_ROOT = ROOT / "qa-lab" / "rebuild-v267" / "playstate-fix" / "syllable-candidates-small"
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
    raw = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_name,sample_rate,channels", "-of", "json", str(path),
    ], text=True)
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


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return round(ordered[low], 3)
    return round(ordered[low] + (ordered[high] - ordered[low]) * (position - low), 3)


def collapse_attack_groups(notes: list[dict[str, Any]], tolerance_ms: float = 1.0) -> list[dict[str, Any]]:
    ordered = sorted(notes, key=lambda note: float(note.get("t", 0.0)))
    groups: list[dict[str, Any]] = []
    for note in ordered:
        t = float(note.get("t", 0.0))
        if not groups or t - float(groups[-1]["last_t"]) > tolerance_ms:
            groups.append({"t": round(t, 3), "last_t": t, "notes": [note]})
        else:
            groups[-1]["last_t"] = t
            groups[-1]["notes"].append(note)
    for group in groups:
        group["size"] = len(group["notes"])
        group["lanes"] = sorted({int(note.get("d", -1)) for note in group["notes"]})
        group.pop("last_t", None)
    return groups


def max_window(groups: list[dict[str, Any]], window_ms: float) -> tuple[int, float, list[dict[str, Any]]]:
    best_count = 0
    best_start = 0.0
    best_groups: list[dict[str, Any]] = []
    left = 0
    for right, group in enumerate(groups):
        current_t = float(group["t"])
        while left <= right and current_t - float(groups[left]["t"]) > window_ms:
            left += 1
        selected = groups[left:right + 1]
        count = sum(int(item["size"]) for item in selected)
        if count > best_count:
            best_count = count
            best_start = float(groups[left]["t"])
            best_groups = selected
    return best_count, round(best_start, 3), best_groups


def run_stats(notes: list[dict[str, Any]], syllables: list[dict[str, Any]], duration_ms: float) -> dict[str, Any]:
    groups = collapse_attack_groups(notes)
    raw_times = [float(note.get("t", -1.0)) for note in notes]
    starts = [float(item.get("start_ms", 0.0)) for item in syllables]
    holds = [float(note.get("l", 0.0) or 0.0) for note in notes if float(note.get("l", 0.0) or 0.0) > 0]
    collisions = [group for group in groups if int(group["size"]) > 1]
    windows_1000 = []
    windows_500 = []
    for window, target in ((1000.0, windows_1000), (500.0, windows_500)):
        count, start, selected = max_window(groups, window)
        target.extend([{"start_ms": start, "end_ms": round(start + window, 3), "raw_notes": count, "attack_groups": len(selected), "max_group_size": max((int(item["size"]) for item in selected), default=0)}])
    # Count every cluster, keeping only the densest representative rows.
    dense_1000 = []
    dense_500 = []
    for index, group in enumerate(groups):
        for window, target, threshold in ((1000.0, dense_1000, 3), (500.0, dense_500, 2)):
            right = index
            while right + 1 < len(groups) and float(groups[right + 1]["t"]) - float(group["t"]) <= window:
                right += 1
            raw_count = sum(int(groups[pos]["size"]) for pos in range(index, right + 1))
            if raw_count > threshold:
                target.append({"start_ms": float(group["t"]), "end_ms": round(float(group["t"]) + window, 3), "raw_notes": raw_count, "attack_groups": right - index + 1})
    lanes = [int(note.get("d", -1)) for note in sorted(notes, key=lambda note: (float(note.get("t", 0.0)), int(note.get("d", -1))))]
    lane_runs: list[int] = []
    if lanes:
        current = 1
        for previous, lane in zip(lanes, lanes[1:]):
            if lane == previous:
                current += 1
            else:
                lane_runs.append(current)
                current = 1
        lane_runs.append(current)
    nearest_errors = [min(abs(float(note.get("t", 0.0)) - start) for start in starts) for note in notes] if starts else []
    unaligned = sum(1 for error in nearest_errors if error > 1.0)
    outside_audio = sum(1 for time in raw_times if time < 0 or time >= duration_ms)
    return {
        "notes": len(notes),
        "unique_attack_groups": len(groups),
        "collision_groups_gt1ms": len(collisions),
        "max_collision_size": max((int(group["size"]) for group in collisions), default=0),
        "max_1000ms": windows_1000[0],
        "max_500ms": windows_500[0],
        "clusters_gt3_in_1000ms": len(dense_1000),
        "clusters_gt2_in_500ms": len(dense_500),
        "densest_1000_examples": dense_1000[:20],
        "densest_500_examples": dense_500[:20],
        "holds": len(holds),
        "hold_max_ms": round(max(holds, default=0.0), 3),
        "hold_p95_ms": percentile(holds, 0.95),
        "same_lane_max_run": max(lane_runs, default=0),
        "same_lane_run_p95": percentile([float(run) for run in lane_runs], 0.95),
        "lane_counts": {str(lane): lanes.count(lane) for lane in range(4)},
        "median_nearest_syllable_error_ms": round(median(nearest_errors), 3) if nearest_errors else 0.0,
        "p95_nearest_syllable_error_ms": percentile(nearest_errors, 0.95),
        "unaligned_notes": unaligned,
        "outside_audio": outside_audio,
    }


def audit_song(song: str) -> dict[str, Any]:
    mod = ROOT / "mods" / f"esperon-dano-{song}"
    song_dir = mod / "songs" / song
    voice = sorted(song_dir.glob("Voices-*.ogg"))[0]
    inst = song_dir / "Inst.ogg"
    data_dir = mod / "data" / "songs" / song
    chart_path = data_dir / f"{song}-chart.json"
    metadata_path = data_dir / f"{song}-metadata.json"
    alignment_path = ALIGN_ROOT / song / "syllable-alignment.json"
    chart = json.loads(chart_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
    voice_info = probe_audio(voice)
    inst_info = probe_audio(inst)
    duration = float(voice_info["duration_ms"])
    return {
        "song": song,
        "mod": mod.name,
        "voice": voice_info,
        "instrumental": inst_info,
        "metadata": {"version": metadata.get("version"), "timeChanges": metadata.get("timeChanges"), "playData": metadata.get("playData", {})},
        "chart_generatedBy": chart.get("generatedBy"),
        "alignment": {"voice_sha256": alignment.get("voice_sha256"), "duration_ms": alignment.get("duration_ms"), "syllables": len(alignment.get("syllables", []))},
        "difficulties": {diff: run_stats(chart.get("notes", {}).get(diff, []), alignment.get("syllables", []), duration) for diff in DIFFS},
    }


def main() -> int:
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(audit_song, SONGS))
    payload = {
        "scope": "WIDE_RESEARCH_V271_V267_DENSITY_BASELINE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "base_release": "esperon-vslice-086-v2.6.7",
        "target_version": "2.7.1",
        "songs": len(rows),
        "parallel_workers": 8,
        "production_untouched": True,
        "rules": {"window_1000_ms": ">3 raw notes", "window_500_ms": ">2 raw notes", "collision_tolerance_ms": 1.0, "literal_submillisecond_offsets_are_collisions": True},
        "rows": sorted(rows, key=lambda row: row["song"]),
    }
    output = ROOT / "qa-lab" / "rebuild-v271" / "phase1-density-baseline-v271.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    totals = {"clusters_gt3_in_1000ms": 0, "clusters_gt2_in_500ms": 0, "collision_groups_gt1ms": 0}
    for row in rows:
        for diff in DIFFS:
            for key in totals:
                totals[key] += int(row["difficulties"][diff][key])
    print(json.dumps({"scope": payload["scope"], "songs": payload["songs"], **totals, "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
