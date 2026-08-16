import json
from pathlib import Path

root = Path('/home/ubuntu/mod-review-loop-production')
song = 'solare'
paths = {
    'production': root / 'mods' / f'esperon-dano-{song}' / 'data' / 'songs' / song / f'{song}-chart.json',
    'v271_candidate': root / 'qa-lab/rebuild-v271/playstate-fix/density-candidates' / song / 'candidate-chart.json',
    'v267_candidate': root / 'qa-lab/rebuild-v267/playstate-fix/syllable-candidates-small' / song / 'candidate-chart.json',
    'alignment': root / 'qa-lab/rebuild-v271/playstate-fix/alignment-source' / song / 'syllable-alignment.json',
}

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

alignment = load(paths['alignment'])
syllables = alignment['syllables']
print('ALIGNMENT', len(syllables), alignment.get('duration_ms'))
for item in syllables[:20]:
    print('SYL', round(float(item.get('start_ms', 0)), 1), round(float(item.get('vocal_end_ms', 0)), 1), item.get('text'), item.get('vowel'), item.get('audio_onset_ms'))

for label, path in paths.items():
    data = load(path)
    if label == 'alignment':
        continue
    print('\nCHART', label, data.get('generatedBy'))
    for diff in ('easy', 'normal', 'hard'):
        notes = data.get('notes', {}).get(diff, [])
        print(diff, 'count', len(notes), 'holds', sum(1 for n in notes if float(n.get('l', 0) or 0) > 0))
        for n in notes[:15]:
            print('NOTE', n)

print('\nNEAR SYLLABLE WINDOWS')
for i, item in enumerate(syllables):
    start = float(item.get('start_ms', 0))
    end = float(item.get('vocal_end_ms', start))
    if i + 1 < len(syllables):
        nxt = float(syllables[i + 1].get('start_ms', 0))
        gap = nxt - start
        if gap <= 500:
            print('PAIR', i, round(start, 1), round(end, 1), item.get('text'), '->', round(nxt, 1), syllables[i + 1].get('text'), 'gap', round(gap, 1), 'dur', round(end-start, 1))
            if i > 40:
                break
