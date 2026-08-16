import json
from collections import defaultdict
from pathlib import Path

root = Path('/home/ubuntu/mod-review-loop-production/qa-lab/rebuild-v271/playstate-fix/alignment-source')
acc = defaultdict(list)
for path in sorted(root.glob('*/syllable-alignment.json')):
    data = json.loads(path.read_text(encoding='utf-8'))
    for item in data.get('syllables', []):
        acc[str(item.get('kind', ''))].append(float(item.get('hold_ms', 0.0) or 0.0))
for kind in sorted(acc):
    vals = sorted(acc[kind])
    print(kind, 'n=', len(vals), 'ge120=', sum(v>=120 for v in vals), 'ge180=', sum(v>=180 for v in vals), 'ge240=', sum(v>=240 for v in vals), 'median=', vals[len(vals)//2], 'p90=', vals[int(len(vals)*.9)-1], 'max=', max(vals))
