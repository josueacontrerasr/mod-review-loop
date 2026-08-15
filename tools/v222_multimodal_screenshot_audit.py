#!/usr/bin/env python3
from __future__ import annotations
import base64, json, os
from pathlib import Path
from openai import OpenAI

IMAGES=[
 '/home/ubuntu/upload/Screenshot_2026-08-14-18-16-25-911_me.funkin.fnf.jpg',
 '/home/ubuntu/upload/Screenshot_2026-08-14-18-16-19-505_me.funkin.fnf.jpg',
 '/home/ubuntu/upload/Screenshot_2026-08-14-18-16-09-722_me.funkin.fnf.jpg',
 '/home/ubuntu/upload/Screenshot_2026-08-14-18-15-29-783_me.funkin.fnf.jpg',
 '/home/ubuntu/upload/Screenshot_2026-08-14-18-15-22-275_me.funkin.fnf.jpg',
]

def data_url(path):
    return 'data:image/jpeg;base64,'+base64.b64encode(Path(path).read_bytes()).decode()

def main():
    client=OpenAI(); parts=[{'type':'text','text':'''Analiza estas capturas de FNF Mobile V-Slice 0.8.6 como evidencia de depuración. No inventes detalles que no sean visibles. Devuelve SOLO JSON con esta forma: {"screenshots":[{"file":"...","visible_text":"...","stage_error":true/false,"stage_id":"...","arrows_visible":true/false,"arrows_notes":"...","characters_visible":true/false,"stage_visible":true/false,"hud_visible":true/false,"observations":["..."],"likely_causes":["..."],"confidence":"high|medium|low"}],"cross_image_findings":["..."],"limitations":["..."]}. Distingue hechos visibles de hipótesis. Las flechas pueden estar visibles en los receptores aunque no haya notas descendiendo; no confundas ambas cosas.'''}]
    for p in IMAGES: parts.append({'type':'image_url','image_url':{'url':data_url(p),'detail':'high'}})
    resp=client.chat.completions.create(model='gemini-3-flash-preview',messages=[{'role':'user','content':parts}],max_tokens=6000,extra_body={'thinking':{'budget_tokens':1024}})
    text=resp.choices[0].message.content or ''
    try:
        payload=json.loads(text)
    except Exception:
        cleaned=text.strip()
        if cleaned.startswith('```'):
            cleaned=cleaned.split('\n',1)[1] if '\n' in cleaned else cleaned
            if cleaned.endswith('```'): cleaned=cleaned[:-3].rstrip()
        try: payload=json.loads(cleaned)
        except Exception: payload={'raw_model_output':text,'parse_error':True}
    root=Path('/home/ubuntu/mod-review-loop-production'); out=root/'qa-lab/rebuild-v222/multimodal-screenshot-audit.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps({'model':'gemini-3-flash-preview','source_files':IMAGES,'analysis':payload},ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':'PASS' if not payload.get('parse_error') else 'PARSE_WARNING','output':str(out)},ensure_ascii=False))
if __name__=='__main__': main()
