#!/usr/bin/env python3
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
mods=sorted((ROOT/'mods').glob('esperon-dano-*'))
for mod in mods:
    p=mod/'_polymod_meta.json'
    d=json.loads(p.read_text())
    d['mod_version']='2.6.4'
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
config=ROOT/'config/fnf_target.json'
d=json.loads(config.read_text())
d['mod_version']='2.6.4'
d['songs_count']=21
d['mods_per_qa_round']=21
d['qa_rounds']=20
d['qa_reviews_expected']=420
d['chart_generation_mode']='VOCAL_SYLLABLE_ALIGNED'
d['chart_syllable_policy']={'one_note_per_syllable':True,'interjections_are_separate_notes':True,'holds_from_measured_vocal_duration':True,'low_confidence_requires_manual_review':True}
d['complete_delivery_zip']='Esperon-Completo.zip'
config.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
print({'mods':len(mods),'mod_version':'2.6.4','songs_count':d['songs_count']})
