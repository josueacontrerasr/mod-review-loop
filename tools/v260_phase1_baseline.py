#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TODO=Path('/home/ubuntu/upload/TODO.zip')
EVID=ROOT/'qa-lab/rebuild-v260'
TODO_OUT=EVID/'todo-reference'
SONGS=['arcoloria','cortamos-y-volvemos','dano','dias-magicos','eclipsis','fango','luma','maraton-de-peliculas','me-voy-a-morir-si-no-me-besas-ahora-mismo','meteora','mi-hogar','nubia','nuestro-amor-no-es-normal','peligrosa','rompecabezas','solare','tristella','tu-dealer-de-nostalgia','un-poco-bien-un-poco-mal','volver-a-vernos']

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def safe_extract(z, out):
 if out.exists(): shutil.rmtree(out)
 out.mkdir(parents=True)
 entries=[]; blocked=[]
 for info in z.infolist():
  name=info.filename.replace('\\','/')
  target=(out/name).resolve()
  if not str(target).startswith(str(out.resolve())+ '/'): blocked.append(name); continue
  entries.append(name)
  if info.is_dir(): target.mkdir(parents=True,exist_ok=True); continue
  target.parent.mkdir(parents=True,exist_ok=True)
  with z.open(info) as src, target.open('wb') as dst: shutil.copyfileobj(src,dst)
 return entries,blocked

def main():
 EVID.mkdir(parents=True,exist_ok=True)
 todo={'present':TODO.is_file(),'sha256':None,'bytes':None,'entries':[],'roots':[],'json_files':[],'xml_files':[],'png_files':[],'suspicious_files':[],'blocked_entries':[]}
 if TODO.is_file():
  todo['sha256']=sha(TODO); todo['bytes']=TODO.stat().st_size
  with zipfile.ZipFile(TODO) as z:
   names=[i.filename for i in z.infolist()]
   todo['entries']=names
   todo['roots']=sorted({n.replace('\\','/').split('/')[0] for n in names if n})
   todo['json_files']=sorted(n for n in names if n.lower().endswith('.json'))
   todo['xml_files']=sorted(n for n in names if n.lower().endswith('.xml'))
   todo['png_files']=sorted(n for n in names if n.lower().endswith('.png'))
   todo['suspicious_files']=sorted(n for n in names if n.lower().endswith(('.py','.sh','.bat','.exe','.dll','.so')) or '/scripts/' in n.lower())
   extracted,blocked=safe_extract(z,TODO_OUT); todo['extracted_entries']=len(extracted); todo['blocked_entries']=blocked
 rows=[]
 for song in SONGS:
  mod=ROOT/'mods'/f'esperon-dano-{song}'; sd=next((mod/'data/songs').iterdir()); audio=mod/'songs'/song; chart=sd/f'{song}-chart.json'; meta=sd/f'{song}-metadata.json'; manifest=mod/'_polymod_meta.json'; voices=sorted(audio.glob('Voices-*.ogg'))
  rows.append({'song':song,'mod_version':json.loads(manifest.read_text()).get('mod_version'),'api_version':json.loads(manifest.read_text()).get('api_version'),'chart_sha256':sha(chart),'metadata_sha256':sha(meta),'inst_sha256':sha(audio/'Inst.ogg'),'inst_bytes':(audio/'Inst.ogg').stat().st_size,'voice_shas':{p.name:sha(p) for p in voices},'voice_bytes':{p.name:p.stat().st_size for p in voices},'notes':{d:len(json.loads(chart.read_text()).get('notes',{}).get(d,[])) for d in ('easy','normal','hard')},'file_count':sum(p.is_file() for p in mod.rglob('*'))})
 payload={'version':'2.6.0-phase1-baseline','status':'PASS' if len(rows)==20 and todo['present'] and not todo['blocked_entries'] else 'ERRORS_FOUND','mods':len(rows),'songs':20,'todo_zip':todo,'rows':rows}
 out=EVID/'baseline-v260.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'status':payload['status'],'mods':len(rows),'todo_present':todo['present'],'todo_entries':len(todo['entries']),'suspicious_files':len(todo['suspicious_files']),'output':str(out)},ensure_ascii=False))
 return 0 if payload['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
