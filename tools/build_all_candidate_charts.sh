#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-.}"
WORKERS="${WORKERS:-2}"
cd "$ROOT"
mkdir -p analysis/all-candidates logs/chart-candidates
find mods -mindepth 1 -maxdepth 1 -type d -name 'esperon-dano-*' ! -name 'esperon-dano-solare' -print0 |
  xargs -0 -r -n1 -P"$WORKERS" bash -c '
    mod="$1"
    id="${mod##*/}"
    song_dir=$(find "$mod/data/songs" -mindepth 1 -maxdepth 1 -type d | head -n1)
    song="${song_dir##*/}"
    out="analysis/all-candidates/$song"
    mkdir -p "$out"
    python3 tools/build_voice_aligned_candidate_chart.py "$mod" --output-dir "$out" --singer-side player >"logs/chart-candidates/$id.log" 2>&1
    python3 /home/ubuntu/skills/fnf-mobile-vslice-mods/scripts/analyze_audio_timing.py "$mod/songs/$song/Inst.ogg" -o "$out/final-ogg-evidence.json" >>"logs/chart-candidates/$id.log" 2>&1
    python3 /home/ubuntu/skills/fnf-mobile-vslice-mods/scripts/compare_chart_audio.py "$song_dir/$song-chart.json" "$out/$song-anchors-candidates.json" --audio-evidence "$out/final-ogg-evidence.json" --difficulty normal -o "$out/static-comparison.json" >>"logs/chart-candidates/$id.log" 2>&1
    printf "DONE|%s\n" "$id"
  ' _
printf 'candidate_reports=%s\n' "$(find analysis/all-candidates -name static-comparison.json | wc -l)"
