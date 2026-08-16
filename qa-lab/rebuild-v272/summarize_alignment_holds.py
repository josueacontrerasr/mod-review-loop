import json
from collections import Counter, defaultdict
from pathlib import Path

root = Path('/home/ubuntu/mod-review-loop-production/qa-lab/rebuild-v271/playstate-fix/alignment-source')
rows = []
for path in sorted(root.glob('*/syllable-alignment.json')):
    data = json.loads(path.read_text(encoding='utf-8'))
    syllables = data.get('syllables', [])
    holds = [float(item.get('hold_ms', 0.0) or 0.0) for item in syllables]
    types = Counter(str(item.get('kind', '')) for item in syllables)
    rows.append({
        'song': path.parent.name,
        'syllables': len(syllables),
        'holds_ge_120': sum(v >= 120 for v in holds),
        'holds_ge_180': sum(v >= 180 for v in holds),
        'holds_ge_240': sum(v >= 240 for v in holds),
        'holds_ge_300': sum(v >= 300 for v in holds),
        'median_hold': sorted(holds)[len(holds)//2] if holds else 0.0,
        'max_hold': max(holds, default=0.0),
        'types': dict(types),
    })
print(json.dumps({'songs': len(rows), 'totals': {
    'syllables': sum(r['syllables'] for r in rows),
    'holds_ge_120': sum(r['holds_ge_120'] for r in rows),
    'holds_ge_180': sum(r['holds_ge_180'] for r in rows),
    'holds_ge_240': sum(r['holds_ge_240'] for r in rows),
    'holds_ge_300': sum(r['holds_ge_300'] for r in rows),
}, 'rows': rows}, ensure_ascii=False, indent=2))
