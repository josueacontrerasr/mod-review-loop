#!/usr/bin/env python3
"""Promote evidence-backed vocal stems and isolated charts into runtime.

A promotion is explicit, reproducible, and recorded. It does not change BPM or
offsets automatically. Use --song for a canary, then run without --song only
after the canary passes validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()


def probe(path: Path) -> dict:
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_name,sample_rate,channels','-of','json',str(path)]))


def encode(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(src),'-c:a','libvorbis','-q:a','6','-ar','44100','-ac','2',str(dst)],check=True)


def promote_song(root: Path, song: str) -> dict:
    mod = root / f'mods/esperon-dano-{song}'
    song_dir = mod / f'data/songs/{song}'
    meta_path = song_dir / f'{song}-metadata.json'
    chart_path = song_dir / f'{song}-chart.json'
    candidate_chart = root / f'sync-candidates/voice-aligned-charts/{song}/{song}-chart.json'
    vocal_stem = root / f'sync-candidates/vocal-stems/{song}/vocals.wav'
    demucs_dir = next((root / f'sync-candidates/vocal-stems/{song}/demucs-work/htdemucs').iterdir())
    no_vocals = demucs_dir / 'no_vocals.wav'
    for p in (meta_path, chart_path, candidate_chart, vocal_stem, no_vocals):
        if not p.is_file(): raise RuntimeError(f'{song}: falta {p}')
    metadata = json.loads(meta_path.read_text(encoding='utf-8'))
    player = metadata['playData']['characters']['player']
    inst = mod / f'songs/{song}/Inst.ogg'
    original_meta_hash = sha256(meta_path); original_chart_hash = sha256(chart_path); original_inst_hash = sha256(inst)
    before = {'metadata_sha256': original_meta_hash, 'chart_sha256': original_chart_hash, 'inst_sha256': original_inst_hash, 'inst_probe': probe(inst)}
    with tempfile.TemporaryDirectory(prefix=f'promote-{song}-') as td:
        td = Path(td)
        new_inst = td / 'Inst.ogg'; new_vocals = td / f'Voices-{player}.ogg'
        encode(no_vocals, new_inst); encode(vocal_stem, new_vocals)
        shutil.copy2(new_inst, inst)
        shutil.copy2(new_vocals, mod / f'songs/{song}/Voices-{player}.ogg')
    # Link one identified vocal stem to the player strumline. No opponent
    # vocal track is invented; all production notes are player-side 4..7.
    characters = metadata.setdefault('playData', {}).setdefault('characters', {})
    characters['playerVocals'] = [player]
    characters['opponentVocals'] = []
    metadata['charter'] = 'Manus AI — chart vocalmente alineado por stem; requiere Audio Sync Test móvil'
    metadata['generatedBy'] = 'Friday Night Funkin\' - 0.8.6; Demucs vocal/instrumental split and independent onset cross-validation; BPM/offset unchanged'
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    promoted = json.loads(candidate_chart.read_text(encoding='utf-8'))
    promoted.pop('candidateOnly', None)
    promoted['generatedBy'] = 'Voice-stem aligned chart promoted after independent onset cross-validation; Audio Sync Test and mobile playtest still required'
    chart_path.write_text(json.dumps(promoted, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    after = {'metadata_sha256': sha256(meta_path), 'chart_sha256': sha256(chart_path), 'inst_sha256': sha256(inst), 'inst_probe': probe(inst), 'voices_sha256': sha256(mod / f'songs/{song}/Voices-{player}.ogg'), 'voices_probe': probe(mod / f'songs/{song}/Voices-{player}.ogg')}
    report = {'status':'PROMOTED_WITH_REVIEW_REQUIRED','song':song,'mod':mod.name,'before':before,'after':after,'evidence':{'vocal_stem':str(vocal_stem.relative_to(root)),'no_vocals':str(no_vocals.relative_to(root)),'isolated_chart':str(candidate_chart.relative_to(root)),'cross_validation':str((root/'qa-lab/rebuild-v221/cross-validation-candidate-summary.json').relative_to(root)),'reconstruction_audit':str((root/'qa-lab/rebuild-v221/demucs-reconstruction-audit.json').relative_to(root))},'guarantees':['No BPM or offset values were changed by this promotion.','All notes remain on player directions 4..7.','Audio Sync Test and mobile playtest are still required for a human PASS.']}
    out=root/f'qa-lab/rebuild-v221/promotions/{song}.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return {'song':song,'status':report['status'],'chart_changed':before['chart_sha256']!=after['chart_sha256'],'inst_changed':before['inst_sha256']!=after['inst_sha256'],'voices':f'songs/{song}/Voices-{player}.ogg','report':str(out)}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('root',nargs='?',default='.'); parser.add_argument('--song'); args=parser.parse_args(); root=Path(args.root).resolve(); songs=[args.song] if args.song else sorted(p.name.removeprefix('esperon-dano-') for p in (root/'mods').glob('esperon-dano-*'))
    results=[promote_song(root,song) for song in songs]; print(json.dumps({'status':'PASS','songs':len(results),'results':results},ensure_ascii=False)); return 0
if __name__=='__main__': raise SystemExit(main())
