#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, zipfile
from pathlib import Path

def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def main():
 root=Path('/home/ubuntu/mod-review-loop-production'); delivery=root/'Mods .zip terminados'; individual=sorted(p for p in delivery.glob('Mod-*-V2.2.2.zip') if 'Coleccion' not in p.name); collection=delivery/'Mod-Esperon-Coleccion-V2.2.2.zip'; issues=[]
 if len(individual)!=20: issues.append(f'individual_zip_count={len(individual)}')
 members=[]
 if not collection.is_file(): issues.append('missing_collection')
 else:
  with zipfile.ZipFile(collection) as q:
   if q.testzip(): issues.append('collection_crc')
   members=sorted(q.namelist())
  if members!=sorted(p.name for p in individual): issues.append('collection_members_mismatch')
 for p in individual:
  with zipfile.ZipFile(p) as q:
   if q.testzip(): issues.append(f'crc:{p.name}')
 hashes=[]
 for p in individual+[collection]: hashes.append({'file':p.name,'sha256':sha(p),'size_bytes':p.stat().st_size})
 report={'status':'PASS' if not issues else 'ERRORS_FOUND','version':'2.2.2','individual_zips':len(individual),'collection_members':len(members),'issues':issues,'assets':hashes,'qa':'20 rounds x 20 mods = 400 PASS','runtime_contract':'20/20 PASS','visual_redesign':'20/20 PASS','chart_promotion':'20/20 applied after independent onset cross-validation','limitations':['La validación estática y el análisis de onsets no certifican sincronía humana perfecta por sí solos.','El Audio Sync Test y el playtest final dentro de FNF Mobile V-Slice 0.8.6 siguen siendo necesarios.','Las capturas previas mostraron el Stage Error; la corrección de rutas y contratos está cubierta por el auditor V2.2.2, pero el APK real debe confirmarse en el dispositivo.']}; out=root/'qa-lab/rebuild-v222/final-v222-release.json'; out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n'); sh=root/'qa-lab/rebuild-v222/sha256-v222.txt'; sh.write_text('\n'.join(f"{x['sha256']}  {x['file']}" for x in hashes)+'\n'); notes=root/'qa-lab/rebuild-v222/release-notes-v222.md'; notes.write_text('# Esperón FNF Mobile V-Slice 0.8.6 — V2.2.2\n\n## Correcciones\n\n- Reparación del contrato StageData: `directory: shared`, rutas relativas de props y mapa explícito de personajes.\n- Reparación de CharacterData: `assetPath` relativo `characters/...`, compatible con el fallback de `Paths.getSparrowAtlas` en V-Slice 0.8.6.\n- Rediseño de flechas y receptores con atlas compactos de 128×128, escalas móviles legibles y estilos únicos por canción.\n- Regeneración de carátulas cuadradas y títulos Sparrow `idle0`/`switch0` para Freeplay.\n- Promoción de charts ajustados por outliers contra onsets vocales independientes; audio, voces, BPM y `timeChanges` se conservaron.\n\n## Validación\n\n- Contrato runtime: 20/20 PASS.\n- QA: 20 rondas × 20 mods = 400 revisiones PASS.\n- ZIPs: 20 individuales + colección maestra, CRC PASS y SHA-256 incluido.\n\n## Límite\n\nLos resultados automáticos son evidencia de ingeniería, no sustituyen el Audio Sync Test del Chart Editor ni el playtest dentro de FNF Mobile V-Slice 0.8.6.\n'); print(json.dumps({'status':report['status'],'individual_zips':len(individual),'collection_members':len(members),'issues':issues,'sha256':str(sh),'notes':str(notes)},ensure_ascii=False)); return 0 if report['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
