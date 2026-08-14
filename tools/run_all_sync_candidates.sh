#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-.}"
WORKERS="${WORKERS:-2}"
cd "$ROOT"
mkdir -p sync-candidates/logs sync-candidates/results
find mods -mindepth 1 -maxdepth 1 -type d -name 'esperon-dano-*' -print0 |
  xargs -0 -r -n1 -P"$WORKERS" bash -c '
    mod="$1"
    id="${mod##*/}"
    python3 tools/audio_sync_candidates.py . --mod "$mod" >"sync-candidates/logs/$id.log" 2>&1
    printf "DONE|%s\n" "$id"
  ' _
printf 'candidate_reports=%s\n' "$(find sync-candidates/results -name sync-candidate-report.json | wc -l)"
