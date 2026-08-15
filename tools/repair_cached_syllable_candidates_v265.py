from pathlib import Path
import json
import sys

import librosa

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_syllable_aligned_candidates_v265 as gen

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "qa-lab/rebuild-v263/playstate-fix/syllable-candidates-small"
DEST = ROOT / "qa-lab/rebuild-v265/playstate-fix/syllable-candidates-small"
DEST.mkdir(parents=True, exist_ok=True)

count = 0
for source_dir in sorted(path for path in SRC.iterdir() if path.is_dir()):
    align_path = source_dir / "syllable-alignment.json"
    align = json.loads(align_path.read_text(encoding="utf-8"))
    voice = ROOT / align["voice"]
    audio, sr = librosa.load(voice, sr=16000, mono=True)
    env_t, env_r = gen.rms_envelope(audio, sr)
    syllables = gen.make_syllables(align["words"], env_t, env_r)
    align["syllables"] = syllables

    destination = DEST / source_dir.name
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "syllable-alignment.json").write_text(
        json.dumps(align, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    chart = {
        "version": "2.0.0",
        "scrollSpeed": {"easy": 0.9, "normal": 1.0, "hard": 1.12},
        "events": [],
        "notes": {difficulty: gen.difficulty_notes(syllables, difficulty) for difficulty in ("easy", "normal", "hard")},
        "generatedBy": "Friday Night Funkin' - 0.8.6; V2.6.5 syllable-aligned vocal chart player lanes cycling 4..7",
    }
    (destination / "candidate-chart.json").write_text(
        json.dumps(chart, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    low_confidence = [item for item in syllables if float(item.get("confidence", 0)) < 0.45]
    report = {
        "scope": "VOCAL_SYLLABLE_ALIGNED_PLAYER_LANE_CANDIDATE_V265",
        "status": "MANUAL_REVIEW_REQUIRED",
        "song": source_dir.name,
        "voice": align["voice"],
        "voice_sha256": align["voice_sha256"],
        "duration_ms": align["duration_ms"],
        "syllables": len(syllables),
        "interjections": sum(1 for item in syllables if item["kind"].startswith("interjection")),
        "holds": sum(1 for item in syllables if float(item.get("hold_ms", 0)) >= 120),
        "low_confidence_syllables": len(low_confidence),
        "notes": {difficulty: len(chart["notes"][difficulty]) for difficulty in chart["notes"]},
        "lane_policy": "Player notes cycle through d=4..7; d=0..3 is rejected by V2.6.5 gates.",
        "policy": [
            "One note per aligned syllable/interjection attack.",
            "Holds bounded by measured vocal interval.",
            "Production is not modified by this candidate rebuild.",
        ],
        "low_confidence_examples": low_confidence[:30],
    }
    (destination / "candidate-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    count += 1

summary = {
    "scope": "VOCAL_SYLLABLE_ALIGNED_PLAYER_LANE_CANDIDATES_V265",
    "songs": count,
    "source": str(SRC.relative_to(ROOT)),
    "output": str(DEST.relative_to(ROOT)),
    "status": "PASS" if count == 21 else "ERRORS_FOUND",
}
(DEST / "batch-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False))
