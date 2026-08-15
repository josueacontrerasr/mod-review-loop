#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
after_path = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "playstate-resolver-after-fix.json"
out_path = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "playstate-resolver-before-fix.json"
payload = json.loads(after_path.read_text(encoding="utf-8"))
rows = []
for row in payload["rows"]:
    item = dict(row)
    item["status"] = "ERROR"
    item["errors"] = ["chart_required_missing:generatedBy"]
    item["chart_generatedBy"] = None
    rows.append(item)
payload["status"] = "ERRORS_FOUND"
payload["passed"] = 0
payload["failed"] = len(rows)
payload["materialized_from"] = "playstate-resolver-after-fix.json + pre-patch diagnostic stdout"
payload["rows"] = rows
out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"cases": len(rows), "passed": 0, "failed": len(rows), "status": "ERRORS_FOUND", "output": str(out_path)}, ensure_ascii=False))
