#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-.}"
WORKERS="${WORKERS:-3}"
cd "$ROOT"
mkdir -p analysis/stems logs/stem-separation
find . -maxdepth 1 -type f -iname '*.m4a' -print0 |
  xargs -0 -r -n1 -P"$WORKERS" bash -c '
    audio="$1"
    name="$(basename "$audio" .m4a)"
    log="logs/stem-separation/${name//\//_}.log"
    target="analysis/stems/htdemucs/$name/vocals.wav"
    if [[ -s "$target" ]]; then
      printf "SKIP|%s\n" "$audio"
      exit 0
    fi
    python3 -m demucs.separate --two-stems=vocals -n htdemucs -o analysis/stems "$audio" >"$log" 2>&1
    printf "DONE|%s\n" "$audio"
  ' _
printf 'vocal_stems=%s\n' "$(find analysis/stems -type f -name vocals.wav | wc -l)"
