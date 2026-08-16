import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SONGS = [
    'arcoloria', 'cortamos-y-volvemos', 'dano', 'dias-magicos', 'eclipsis', 'fango', 'luma',
    'maraton-de-peliculas', 'me-voy-a-morir-si-no-me-besas-ahora-mismo', 'meteora', 'mi-hogar',
    'nubia', 'nuestro-amor-no-es-normal', 'peligrosa', 'rompecabezas', 'si-te-vas', 'solare',
    'tristella', 'tu-dealer-de-nostalgia', 'un-poco-bien-un-poco-mal', 'volver-a-vernos',
]

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def note_near(notes, t, tol=12.0):
    return [n for n in notes if abs(float(n.get('t', 0.0)) - t) <= tol]

def pair_stats(syllables, notes):
    kept = 0
    eligible = 0
    missing = []
    for left, right in zip(syllables, syllables[1:]):
        lt = float(left.get('start_ms', 0.0))
        rt = float(right.get('start_ms', 0.0))
        gap = rt - lt
        if 80.0 <= gap <= 500.0:
            eligible += 1
            if note_near(notes, lt) and note_near(notes, rt):
                kept += 1
            else:
                missing.append({'left': left.get('text'), 'right': right.get('text'), 'left_ms': lt, 'right_ms': rt, 'gap_ms': gap, 'left_note': note_near(notes, lt), 'right_note': note_near(notes, rt)})
    return eligible, kept, missing

rows = []
all_missing = []
fal_examples = []
for song in SONGS:
    align = load(ROOT / 'qa-lab/rebuild-v272/playstate-fix/vocal-sync-candidates' / song / 'syllable-alignment.json')
    v272 = load(ROOT / 'qa-lab/rebuild-v272/playstate-fix/vocal-sync-candidates' / song / 'candidate-chart.json')
    v271 = load(ROOT / 'qa-lab/rebuild-v271/playstate-fix/density-candidates' / song / 'candidate-chart.json')
    syllables = sorted(align.get('syllables', []), key=lambda x: float(x.get('start_ms', 0.0)))
    normal272 = v272.get('notes', {}).get('normal', [])
    normal271 = v271.get('notes', {}).get('normal', [])
    eligible, kept, missing = pair_stats(syllables, normal272)
    all_missing.extend([{'song': song, **m} for m in missing])
    for i, item in enumerate(syllables):
        text = str(item.get('text', '')).lower()
        if any(token in text for token in ('fal', 'tan')):
            fal_examples.append({'song': song, 'index': i, 'text': text, 'start_ms': item.get('start_ms'), 'normal272': note_near(normal272, float(item.get('start_ms', 0.0))), 'normal271': note_near(normal271, float(item.get('start_ms', 0.0)))})
    lane_counts = Counter(int(n.get('d', -1)) for n in normal272)
    rows.append({
        'song': song,
        'syllables': len(syllables),
        'v271_normal_notes': len(normal271),
        'v272_easy_notes': len(v272.get('notes', {}).get('easy', [])),
        'v272_normal_notes': len(normal272),
        'v272_hard_notes': len(v272.get('notes', {}).get('hard', [])),
        'normal_delta_vs_v271': len(normal272) - len(normal271),
        'normal_pair_windows_80_500ms': eligible,
        'normal_pair_windows_kept_separately': kept,
        'normal_pair_keep_ratio': round(kept / max(1, eligible), 4),
        'normal_hold_count': sum(1 for n in normal272 if float(n.get('l', 0.0) or 0.0) > 0),
        'hard_hold_count': sum(1 for n in v272.get('notes', {}).get('hard', []) if float(n.get('l', 0.0) or 0.0) > 0),
        'normal_lane_counts': {str(k): lane_counts.get(k, 0) for k in range(4)},
    })

summary = {
    'songs': len(rows),
    'totals': {
        'syllables': sum(r['syllables'] for r in rows),
        'v271_normal_notes': sum(r['v271_normal_notes'] for r in rows),
        'v272_easy_notes': sum(r['v272_easy_notes'] for r in rows),
        'v272_normal_notes': sum(r['v272_normal_notes'] for r in rows),
        'v272_hard_notes': sum(r['v272_hard_notes'] for r in rows),
        'normal_delta_vs_v271': sum(r['normal_delta_vs_v271'] for r in rows),
        'pair_windows_80_500ms': sum(r['normal_pair_windows_80_500ms'] for r in rows),
        'pair_windows_kept_separately': sum(r['normal_pair_windows_kept_separately'] for r in rows),
    },
    'overall_pair_keep_ratio': round(sum(r['normal_pair_windows_kept_separately'] for r in rows) / max(1, sum(r['normal_pair_windows_80_500ms'] for r in rows)), 4),
    'rows': rows,
    'missing_close_pairs': all_missing[:300],
    'missing_close_pair_count': len(all_missing),
    'fal_tan_text_examples': fal_examples,
}
print(json.dumps(summary, ensure_ascii=False, indent=2))
