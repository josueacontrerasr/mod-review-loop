#!/usr/bin/env python3
"""Construye charts candidatos desde actividad vocal/onsets; no certifica sincronía humana."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import librosa
import numpy as np


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def merge_segments(mask: np.ndarray, hop_ms: float) -> list[tuple[float, float]]:
    raw: list[tuple[int, int]] = []
    start: int | None = None
    for index, active in enumerate(mask):
        if active and start is None:
            start = index
        elif not active and start is not None:
            raw.append((start, index))
            start = None
    if start is not None:
        raw.append((start, len(mask)))
    merged: list[tuple[int, int]] = []
    for begin, end in raw:
        if merged and (begin - merged[-1][1]) * hop_ms <= 175:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((begin, end))
    return [(begin * hop_ms, end * hop_ms) for begin, end in merged if (end - begin) * hop_ms >= 145]


def candidate_onsets(audio: np.ndarray, sr: int, *, use_vocal_stem: bool) -> tuple[list[float], list[tuple[float, float]]]:
    hop = 256
    rms = librosa.feature.rms(y=audio, frame_length=2048, hop_length=hop)[0]
    db = librosa.amplitude_to_db(np.maximum(rms, 1e-10), ref=np.max)
    # Los stems vocales permiten un umbral sensible; las mezclas completas usan uno conservador.
    percentile = 60 if use_vocal_stem else 76
    segments = merge_segments(db >= np.percentile(db, percentile), hop * 1000.0 / sr)
    onset_frames = librosa.onset.onset_detect(y=audio, sr=sr, hop_length=hop, backtrack=True, units="frames")
    raw = [float(frame) * hop * 1000.0 / sr for frame in onset_frames]
    active = [t for t in raw if any(start <= t <= end for start, end in segments)]
    selected: list[float] = []
    for timestamp in active:
        if timestamp < 1600:
            continue
        if not selected or timestamp - selected[-1] >= 155:
            selected.append(timestamp)
    return selected, segments


def notes_for_times(times: list[float], difficulty: str, owner: int) -> list[dict[str, float | int]]:
    step = {"easy": 2, "normal": 1, "hard": 1}[difficulty]
    notes: list[dict[str, float | int]] = []
    for index, timestamp in enumerate(times[::step]):
        direction = owner + (index % 4)
        note: dict[str, float | int] = {"t": round(timestamp, 3), "d": direction}
        if difficulty == "hard" and index + 1 < len(times[::step]):
            gap = times[::step][index + 1] - timestamp
            if 420 <= gap <= 1500 and index % 5 == 0:
                note["l"] = round(min(650.0, gap * 0.7), 3)
        notes.append(note)
    return notes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mod", type=Path)
    parser.add_argument("--vocal-stem", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--singer-side", choices=("player", "opponent"), default="player")
    args = parser.parse_args()
    mod = args.mod.resolve()
    song_dirs = [path for path in (mod / "data" / "songs").iterdir() if path.is_dir()]
    if len(song_dirs) != 1:
        raise SystemExit("El mod debe contener exactamente una canción.")
    song_dir = song_dirs[0]
    song_id = song_dir.name
    metadata_path = song_dir / f"{song_id}-metadata.json"
    chart_path = song_dir / f"{song_id}-chart.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    final_audio = mod / "songs" / song_id / "Inst.ogg"
    source = args.vocal_stem if args.vocal_stem and args.vocal_stem.is_file() else final_audio
    use_stem = source != final_audio
    audio, sr = librosa.load(source, sr=22050, mono=True)
    reference, ref_sr = librosa.load(final_audio, sr=22050, mono=True)
    times, segments = candidate_onsets(audio, sr, use_vocal_stem=use_stem)
    if len(times) < 24:
        raise SystemExit(f"Actividad insuficiente para chart candidato: {len(times)} ataques")
    tempo, beat_frames = librosa.beat.beat_track(y=reference, sr=ref_sr, hop_length=256)
    bpm = float(np.asarray(tempo).reshape(-1)[0])
    beat_ms = [round(float(frame) * 256 * 1000.0 / ref_sr, 3) for frame in beat_frames]
    owner = 0 if args.singer_side == "player" else 4
    chart = {
        "version": "2.0.0",
        "scrollSpeed": {"easy": 0.9, "normal": 1.0, "hard": 1.12},
        "events": [{"t": round(t, 3), "e": "FocusCamera", "v": {"char": 0 if args.singer_side == "player" else 1}} for t in times[::32]],
        "notes": {difficulty: notes_for_times(times, difficulty, owner) for difficulty in ("easy", "normal", "hard")},
        "generatedBy": "Audio-vocal candidate chart; requires Chart Editor Audio Sync Test and mobile playtest"
    }
    # Solo un tempo candidato: no se inventan cambios de BPM sin anclajes humanos revisados.
    metadata["charter"] = "Manus AI — chart candidato guiado por actividad vocal"
    metadata["timeChanges"] = [{"t": 0, "b": 0, "bpm": round(bpm, 3), "bt": [4, 4, 4, 4]}]
    metadata["generatedBy"] = "Friday Night Funkin' - 0.8.6; timing candidate requires manual sync review"
    chart_path.write_text(json.dumps(chart, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    anchors = []
    for index, timestamp in enumerate(times[::8]):
        anchors.append({"section": f"candidate-{index // 8 + 1}", "label": f"vocal-onset-{index + 1}", "expected_ms": round(timestamp, 3), "direction": owner + ((index * 8) % 4), "evidence": "AUTO_CANDIDATE_REQUIRES_HUMAN_REVIEW"})
    evidence = {
        "scope": "AUDIO_VOCAL_CANDIDATE_CHART",
        "status": "REQUIRES_HUMAN_REVIEW",
        "song": song_id,
        "final_audio": str(final_audio.relative_to(mod)),
        "final_audio_sha256": sha256(final_audio),
        "analysis_audio": str(source),
        "analysis_audio_sha256": sha256(source),
        "analysis_mode": "VOCAL_STEM" if use_stem else "FULL_MIX_PROXY",
        "beat_tracker_bpm_candidate": round(bpm, 3),
        "beat_candidates_ms": beat_ms,
        "candidate_vocal_segments": [{"start_ms": round(start, 3), "end_ms": round(end, 3)} for start, end in segments],
        "candidate_vocal_onsets_ms": [round(t, 3) for t in times],
        "singer_side": args.singer_side,
        "limitations": [
            "Los timestamps son candidatos de análisis; no prueban sílabas ni artista.",
            "No se declara sincronía aprobada sin Audio Sync Test en Chart Editor y playtest móvil.",
            "No se infieren cambios de BPM sin revisión humana de anclajes y forma de onda."
        ]
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / f"{song_id}-anchors-candidates.json", {"anchors": anchors})
    write_json(args.output_dir / f"{song_id}-alignment-evidence.json", evidence)
    evidence_dir = ROOT / "qa-lab" / "rebuild-v220" / "evidence" / song_id
    evidence_dir.mkdir(parents=True, exist_ok=True)
    write_json(evidence_dir / "sync-report.json", {
        "scope": "AUTO_VOCAL_ONSET_CANDIDATE_CHART",
        "status": "REQUIRES_HUMAN_REVIEW",
        "evidence": str((args.output_dir / f"{song_id}-alignment-evidence.json").relative_to(ROOT) if args.output_dir.is_relative_to(ROOT) else args.output_dir / f"{song_id}-alignment-evidence.json"),
        "limitations": evidence["limitations"]
    })
    print(json.dumps({"song": song_id, "onsets": len(times), "bpm": round(bpm, 3), "mode": evidence["analysis_mode"]}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
