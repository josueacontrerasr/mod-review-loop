from pathlib import Path
import json
import sys
import librosa
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import build_syllable_aligned_candidates_v263 as gen
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'qa-lab/rebuild-v263/playstate-fix/syllable-candidates-small'
for d in sorted(p for p in SRC.iterdir() if p.is_dir()):
    align_path=d/'syllable-alignment.json'
    align=json.loads(align_path.read_text())
    voice=ROOT/align['voice']
    audio,sr=librosa.load(voice,sr=16000,mono=True)
    env_t,env_r=gen.rms_envelope(audio,sr)
    syll=gen.make_syllables(align['words'],env_t,env_r)
    align['syllables']=syll
    align_path.write_text(json.dumps(align,ensure_ascii=False,indent=2)+'\n')
    chart={
      'version':'2.0.0','scrollSpeed':{'easy':0.9,'normal':1.0,'hard':1.12},'events':[],
      'notes':{diff:gen.difficulty_notes(syll,diff) for diff in ('easy','normal','hard')},
      'generatedBy':"Friday Night Funkin' - 0.8.6; V2.6.3 syllable-aligned candidate; requires Audio Sync Test"
    }
    (d/'candidate-chart.json').write_text(json.dumps(chart,ensure_ascii=False,indent=2)+'\n')
    low=[s for s in syll if float(s.get('confidence',0))<0.45]
    report={'scope':'VOCAL_SYLLABLE_ALIGNED_CANDIDATE','status':'MANUAL_REVIEW_REQUIRED','song':d.name,'voice':align['voice'],'voice_sha256':align['voice_sha256'],'duration_ms':align['duration_ms'],'syllables':len(syll),'interjections':sum(1 for s in syll if s['kind'].startswith('interjection')),'holds':sum(1 for s in syll if float(s.get('hold_ms',0))>=120),'low_confidence_syllables':len(low),'notes':{x:len(chart['notes'][x]) for x in chart['notes']},'policy':['One note per aligned syllable/interjection attack.','Holds bounded by measured vocal interval.','Production is not modified by this candidate rebuild.'],'low_confidence_examples':low[:30]}
    (d/'candidate-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('repaired',len(list(SRC.iterdir())))
