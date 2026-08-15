#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
PREFIX='esperon-dano-'
EXPECTED=['easy','normal','hard']

def load(path):
    try: return json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc: return {'__error__':str(exc)}

def frames(path):
    if not path.is_file(): return []
    try: return [x.attrib.get('name','') for x in ET.parse(path).getroot().findall('.//SubTexture')]
    except Exception: return []

def audio_duration(path):
    if not path.is_file(): return None
    try:
        raw=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)],check=True,capture_output=True,text=True).stdout.strip()
        return float(raw)
    except Exception: return None

def resolve_asset(mod, asset):
    if not isinstance(asset,str) or not asset: return None
    if asset.startswith('shared:'): return mod/'shared'/'images'/asset.removeprefix('shared:')
    if asset.startswith('default:'): return None
    return mod/'images'/asset

def audit(mod):
    song=mod.name.removeprefix(PREFIX)
    issues=[]
    song_dir=mod/'data'/'songs'/song
    meta=load(song_dir/f'{song}-metadata.json')
    chart=load(song_dir/f'{song}-chart.json')
    play=meta.get('playData',{}) if isinstance(meta,dict) else {}
    album_id=play.get('album')
    album_path=mod/'data'/'ui'/'freeplay'/'albums'/f'{album_id}.json' if album_id else None
    album=load(album_path) if album_path else {}
    album_assets={}
    for key in ('albumArtAsset','albumTitleAsset'):
        val=album.get(key)
        base=mod/'images'/val if isinstance(val,str) else None
        png=base.with_suffix('.png') if base else None
        xml=base.with_suffix('.xml') if base else None
        fs=frames(xml) if xml else []
        album_assets[key]={'value':val,'png_exists':bool(png and png.is_file()),'xml_exists':bool(xml and xml.is_file()),'frames':fs}
        if isinstance(val,str) and val.startswith('freeplay/albums/'):
            issues.append(f'{key}_uses_albums_not_albumRoll')
        if not png or not png.is_file(): issues.append(f'{key}_png_missing')
        if key=='albumTitleAsset':
            if not xml or not xml.is_file(): issues.append('albumTitleAsset_xml_missing')
            if not any(f.startswith('idle0') for f in fs): issues.append('albumTitle_idle_prefix_missing')
            if not any(f.startswith('switch0') for f in fs): issues.append('albumTitle_switch_prefix_missing')
    style_id=play.get('noteStyle')
    style_path=mod/'data'/'notestyles'/f'{style_id}.json' if style_id else None
    style=load(style_path) if style_path else {}
    style_assets={}
    if not style_path or not style_path.is_file(): issues.append('note_style_json_missing')
    for group in ('note','noteStrumline'):
        spec=style.get('assets',{}).get(group,{}) if isinstance(style,dict) else {}
        asset=spec.get('assetPath') if isinstance(spec,dict) else None
        base=resolve_asset(mod,asset)
        png=base.with_suffix('.png') if base else None
        xml=base.with_suffix('.xml') if base else None
        fs=frames(xml) if xml else []
        prefixes=[]
        for obj in (spec.get('data',{}).values() if isinstance(spec,dict) else []):
            if isinstance(obj,dict) and obj.get('prefix'): prefixes.append(obj['prefix'])
        missing=[p for p in prefixes if not any(f==p or f.startswith(p) for f in fs)]
        style_assets[group]={'assetPath':asset,'resolved_base':str(base.relative_to(mod)) if base and base.exists() else str(base) if base else None,'png_exists':bool(png and png.is_file()),'xml_exists':bool(xml and xml.is_file()),'frame_count':len(fs),'prefixes':prefixes,'missing_prefixes':missing}
        if not png or not png.is_file(): issues.append(f'{group}_png_missing')
        if not xml or not xml.is_file(): issues.append(f'{group}_xml_missing')
        if missing: issues.append(f'{group}_prefixes_missing')
    notes=chart.get('notes',{}) if isinstance(chart,dict) else {}
    chart_summary={}
    for diff in EXPECTED:
        arr=notes.get(diff,[]) if isinstance(notes,dict) else []
        ts=[]
        malformed=0
        for n in arr:
            try: ts.append(float(n['t']))
            except Exception: malformed+=1
        chart_summary[diff]={'count':len(arr),'first_t':min(ts) if ts else None,'last_t':max(ts) if ts else None,'malformed':malformed}
        if not arr: issues.append(f'{diff}_notes_empty')
    audio=mod/'songs'/song/'Inst.ogg'
    dur=audio_duration(audio)
    if dur is not None:
        # Chart t is milliseconds in this contract.
        for diff,s in chart_summary.items():
            if s['last_t'] is not None and s['last_t'] > dur*1000+5000: issues.append(f'{diff}_notes_beyond_audio')
    return {'mod':mod.name,'song':song,'status':'PASS' if not issues else 'ISSUES','issues':sorted(set(issues)),'metadata':{'album':album_id,'noteStyle':style_id,'difficulties':play.get('difficulties')},'album':{'json_exists':bool(album_path and album_path.is_file()),'assets':album_assets},'note_style':style_assets,'chart':chart_summary,'audio_duration_seconds':dur}

def main():
    mods=sorted((ROOT/'mods').glob(PREFIX+'*'))
    rows=[audit(m) for m in mods if m.is_dir()]
    out={'version':'2.4.0-diagnose-freeplay-notes','mods':len(rows),'status':'PASS' if len(rows)==20 and all(r['status']=='PASS' for r in rows) else 'ISSUES_FOUND','rows':rows}
    path=ROOT/'qa-lab'/'rebuild-v240'/'diagnose-freeplay-notes-v240.json'
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    from collections import Counter
    c=Counter(i for r in rows for i in r['issues'])
    print(json.dumps({'status':out['status'],'mods':len(rows),'issue_counts':dict(c),'output':str(path)},ensure_ascii=False))

if __name__=='__main__': main()
