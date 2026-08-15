from pathlib import Path
import json
import whisper
ROOT=Path(__file__).resolve().parents[1]
model=whisper.load_model('small')
for song in ['maraton-de-peliculas','nubia']:
    voice=next((ROOT/'mods').glob(f'esperon-dano-*/songs/{song}/Voices-*.ogg'))
    result=model.transcribe(str(voice),language='es',word_timestamps=True,fp16=False,temperature=0,condition_on_previous_text=False,no_speech_threshold=0.35,compression_ratio_threshold=2.6)
    words=[w for s in result.get('segments',[]) for w in s.get('words',[]) if str(w.get('word','')).strip()]
    out={'song':song,'language':result.get('language'),'segments':len(result.get('segments',[])),'words':len(words),'first_words':words[:30],'last_words':words[-20:]}
    p=ROOT/'qa-lab/rebuild-v263/playstate-fix'/f'whisper-small-{song}.json'
    p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'song':song,'words':len(words),'segments':len(result.get('segments',[]))}))
