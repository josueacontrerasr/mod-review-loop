#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","si-te-vas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]
DIFFS=("easy","normal","hard")

def sha(path:Path):
    h=hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest()

def one(song):
    mod=ROOT/'mods'/f'esperon-dano-{song}'
    data=mod/'data'/'songs'/song
    chart=json.loads((data/f'{song}-chart.json').read_text())
    metadata=json.loads((data/f'{song}-metadata.json').read_text())
    lanes={}; duplicate_keys={}; notes_total=0; holds=0
    for diff in DIFFS:
        notes=chart.get('notes',{}).get(diff,[]); notes_total+=len(notes); holds+=sum(1 for n in notes if float(n.get('l',0) or 0)>0)
        lanes[diff]={str(i):sum(1 for n in notes if n.get('d')==i) for i in range(8)}
        keys=[(round(float(n.get('t',-1)),3),n.get('d')) for n in notes]; duplicate_keys[diff]=len(keys)-len(set(keys))
    album_id=metadata.get('playData',{}).get('album')
    album_path=mod/'data'/'ui'/'freeplay'/'albums'/f'{album_id}.json'
    album=json.loads(album_path.read_text()) if album_path.is_file() else {}
    art_asset=album.get('albumArtAsset',''); title_asset=album.get('albumTitleAsset','')
    art=mod/'images'/f'{art_asset}.png' if art_asset else Path('/missing')
    title=mod/'images'/f'{title_asset}.png' if title_asset else Path('/missing')
    art_info={'declared':art_asset,'exists':art.is_file(),'sha256':sha(art) if art.is_file() else None,'size':None,'bbox':None}
    if art.is_file():
        try:
            with Image.open(art) as im: art_info.update(size=list(im.size),bbox=im.getbbox())
        except Exception as exc: art_info['error']=str(exc)
    title_info={'declared':title_asset,'exists':title.is_file(),'sha256':sha(title) if title.is_file() else None,'size':None}
    if title.is_file():
        try:
            with Image.open(title) as im: title_info['size']=list(im.size)
        except Exception as exc: title_info['error']=str(exc)
    align_path=ROOT/'qa-lab'/'rebuild-v264'/'playstate-fix'/'syllable-candidates-small'/song/'syllable-alignment.json'
    align=json.loads(align_path.read_text()) if align_path.is_file() else {'syllables':[]}
    syll=align.get('syllables',[])
    starts=[float(s.get('start_ms',-1)) for s in syll]
    spans=[(float(s.get('start_ms',-1)), float(s.get('vocal_end_ms', s.get('start_ms',-1)))) for s in syll]
    end_by_start={}
    for s in syll: end_by_start.setdefault(round(float(s.get('start_ms',-1)),3),[]).append(float(s.get('vocal_end_ms',s.get('start_ms',-1))))
    coverage={}; missing_holds={}
    for diff in DIFFS:
        notes=chart.get('notes',{}).get(diff,[]); missing=[]; hold_missing=[]
        for n in notes:
            t=float(n.get('t',-1)); nearest=min((abs(t-s) for s in starts),default=99999)
            inside_span=any(start-10 <= t <= end+20 for start,end in spans)
            if nearest>45 and not inside_span: missing.append(t)
            if float(n.get('l',0) or 0)>0:
                ends=end_by_start.get(round(t,3),[])
                if ends and t+float(n['l'])+50<max(ends): hold_missing.append({'t':t,'l':float(n['l']),'vocal_end':max(ends)})
        coverage[diff]={'notes':len(notes),'syllables':len(syll),'notes_without_vocal_attack':len(missing),'examples':missing[:8]}
        missing_holds[diff]=hold_missing[:8]
    return {'song':song,'mod_version':json.loads((mod/'_polymod_meta.json').read_text()).get('mod_version'),'generatedBy':chart.get('generatedBy'),'notes_total':notes_total,'holds_total':holds,'lane_counts':lanes,'duplicate_note_keys':duplicate_keys,'album_id':album_id,'album_json_exists':album_path.is_file(),'album_art':art_info,'album_title':title_info,'syllable_count':len(syll),'coverage':coverage,'holds_suspiciously_short':missing_holds}

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool: rows=sorted(pool.map(one,SONGS),key=lambda x:x['song'])
    payload={'scope':'V264_THREE_ERRORS_DIAGNOSTIC','executed_at':datetime.now(timezone.utc).isoformat(),'songs':len(rows),'rows':rows}
    out=ROOT/'qa-lab'/'rebuild-v264'/'three-errors-diagnostic-v264.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    bad_player_lanes=sum(1 for r in rows for d in DIFFS for lane,count in r['lane_counts'][d].items() if int(lane) < 4 and count > 0)
    missing=sum(r['coverage'][d]['notes_without_vocal_attack'] for r in rows for d in DIFFS)
    print(json.dumps({'songs':len(rows),'difficulties_with_opponent_lane_notes':bad_player_lanes,'notes_without_vocal_attack_or_vocal_span':missing,'output':str(out)}))
if __name__=='__main__': main()
