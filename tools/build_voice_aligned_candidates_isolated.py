#!/usr/bin/env python3
"""Build isolated voice-onset chart candidates; never edits production mods."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import librosa
import numpy as np

SR = 22050
HOP = 256
MIN_SPACING_MS = 155.0


def merge_segments(mask: np.ndarray, hop_ms: float) -> list[tuple[float, float]]:
    raw=[]; start=None
    for i, active in enumerate(mask):
        if bool(active) and start is None: start=i
        elif not bool(active) and start is not None:
            raw.append((start,i)); start=None
    if start is not None: raw.append((start,len(mask)))
    merged=[]
    for a,b in raw:
        sa, sb = a*hop_ms, b*hop_ms
        if sb-sa < 140: continue
        if merged and sa-merged[-1][1] <= 180: merged[-1]=(merged[-1][0],sb)
        else: merged.append((sa,sb))
    return merged


def vocal_onsets(stem: Path) -> tuple[list[float], list[tuple[float,float]], float]:
    y, sr = librosa.load(stem, sr=SR, mono=True)
    hop_ms=HOP*1000/sr
    rms=librosa.feature.rms(y=y, frame_length=2048, hop_length=HOP)[0]
    db=librosa.amplitude_to_db(np.maximum(rms,1e-10), ref=np.max)
    segments=merge_segments(db >= np.percentile(db,60), hop_ms)
    env=librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
    frames=librosa.onset.onset_detect(onset_envelope=env, sr=sr, hop_length=HOP, backtrack=True, units='frames')
    raw=[float(f)*hop_ms for f in frames]
    selected=[]
    for t in raw:
        if t < 1600: continue
        if not any(a <= t <= b for a,b in segments): continue
        if not selected or t-selected[-1] >= MIN_SPACING_MS: selected.append(round(t,3))
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr, hop_length=HOP)
    bpm=float(np.asarray(tempo).reshape(-1)[0])
    return selected, segments, bpm


def make_chart(times: list[float]) -> dict:
    charts={}
    for difficulty, step in (("easy",2),("normal",1),("hard",1)):
        chosen=times[::step]
        notes=[]
        for i,t in enumerate(chosen):
            note={"t":round(t,3),"d":4+(i%4)}
            # Holds only where there is a clearly long vocal gap; this keeps
            # sustained notes conservative rather than inventing overlaps.
            if difficulty == "hard" and i+1 < len(chosen):
                gap=chosen[i+1]-t
                if 650 <= gap <= 1500 and i % 6 == 0:
                    note["l"]=round(min(700.0,gap*0.65),3)
            notes.append(note)
        charts[difficulty]=notes
    return {"version":"2.0.0","scrollSpeed":{"easy":0.9,"normal":1.0,"hard":1.12},"events":[{"t":round(t,3),"e":"FocusCamera","v":{"char":0}} for t in times[::32]],"notes":charts,"candidateOnly":True,"generatedBy":"Voice-stem onset candidate; isolated from production; requires Audio Sync Test and mobile playtest"}


def main() -> int:
    root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
    songs=[]
    for mod in sorted((root/'mods').glob('esperon-dano-*')):
        song_dirs=[p for p in (mod/'data/songs').iterdir() if p.is_dir()]
        if len(song_dirs)!=1: raise SystemExit(f"song dir inválido: {mod}")
        song=song_dirs[0].name; stem=root/'sync-candidates/vocal-stems'/song/'vocals.wav'
        times,segments,bpm=vocal_onsets(stem)
        out=root/'sync-candidates/voice-aligned-charts'/song
        out.mkdir(parents=True,exist_ok=True)
        (out/f'{song}-chart.json').write_text(json.dumps(make_chart(times),ensure_ascii=False,indent=2)+'\n')
        report={"scope":"ISOLATED_VOICE_ALIGNED_CHART_CANDIDATE","status":"REQUIRES_HUMAN_REVIEW","song":song,"source_vocal_stem":str(stem.relative_to(root)),"onsets":len(times),"candidate_bpm":round(bpm,3),"segments":[{"start_ms":round(a,3),"end_ms":round(b,3)} for a,b in segments],"limitations":["Onsets no identifican sílaba, personaje ni dirección por sí solos.","No se modifica el chart de producción.","Audio Sync Test y playtest móvil siguen siendo obligatorios."]}
        (out/'evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        songs.append({"song":song,"onsets":len(times),"bpm":round(bpm,3),"output":str((out/f'{song}-chart.json').relative_to(root))})
        print(json.dumps(songs[-1],ensure_ascii=False),flush=True)
    summary={"status":"PASS" if len(songs)==20 else "ERRORS_FOUND","songs":len(songs),"results":songs,"production_changed":False}
    out=root/'qa-lab/rebuild-v221/voice-aligned-candidate-summary.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({"status":summary["status"],"songs":len(songs),"output":str(out)},ensure_ascii=False))
    return 0 if summary["status"]=="PASS" else 1

if __name__=='__main__': raise SystemExit(main())
