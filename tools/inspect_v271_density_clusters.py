#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def groups(notes: list[dict]) -> list[dict]:
    result = []
    for note in sorted(notes, key=lambda row: float(row.get("t", 0.0))):
        t = float(note.get("t", 0.0))
        if not result or t - result[-1]["last_t"] > 1.0:
            result.append({"t": t, "last_t": t, "notes": [note]})
        else:
            result[-1]["last_t"] = t
            result[-1]["notes"].append(note)
    for row in result:
        row["size"] = len(row["notes"])
        row["lanes"] = sorted(int(note.get("d", -1)) for note in row["notes"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("song")
    parser.add_argument("difficulty")
    args = parser.parse_args()
    path = ROOT / "qa-lab/rebuild-v271/playstate-fix/density-candidates" / args.song / "candidate-chart.json"
    chart = json.loads(path.read_text(encoding="utf-8"))
    rows = groups(chart["notes"][args.difficulty])
    for index, row in enumerate(rows):
        for window, threshold in ((500.0, 2), (1000.0, 3)):
            end = index
            while end + 1 < len(rows) and rows[end + 1]["t"] - row["t"] <= window:
                end += 1
            raw = sum(rows[pos]["size"] for pos in range(index, end + 1))
            if raw > threshold:
                payload = {"window_ms": window, "threshold": threshold, "start": row["t"], "end": row["t"] + window, "raw": raw, "groups": [{"t": rows[pos]["t"], "size": rows[pos]["size"], "lanes": rows[pos]["lanes"], "notes": rows[pos]["notes"]} for pos in range(index, end + 1)]}
                print(json.dumps(payload, ensure_ascii=False))
                break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
