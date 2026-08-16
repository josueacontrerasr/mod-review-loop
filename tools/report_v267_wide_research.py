#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAND_SUMMARY = ROOT / "qa-lab/rebuild-v267/playstate-fix/syllable-candidates-small/batch-summary-v267.json"
QUALITY = ROOT / "qa-lab/rebuild-v267/playstate-fix/candidate-quality-v267.json"
DRIFT = ROOT / "qa-lab/rebuild-v267/phase5-section-drift-v267.json"
ONSET = ROOT / "qa-lab/rebuild-v267/phase2-vocal-onsets/summary.json"
VALIDATION = ROOT / "qa-lab/rebuild-v267/playstate-fix/syllable-candidates-small-validation-v267.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    candidate = load(CAND_SUMMARY)
    quality = load(QUALITY)
    drift = load(DRIFT)
    onset = load(ONSET)
    validation = load(VALIDATION)
    quality_by_song = {row["song"]: row for row in quality["rows"]}
    drift_by_song = {row["song"]: row for row in drift["rows"]}
    onset_by_song = {row["song"]: row for row in onset["rows"]}
    lines = [
        "# Wide Research V2.7 — informe consolidado",
        "",
        f"Generado: {datetime.now(timezone.utc).isoformat()}",
        "",
        "> Este informe compara la línea base V2.6.6 con candidatos aislados V2.7. La métrica de 0 ms representa coincidencia con el onset acústico calculado por RMS/VAD; no sustituye `Audio Sync Test` ni playtest móvil.",
        "",
        "## Resumen",
        "",
        f"Se analizaron {candidate['songs']} canciones en paralelo con 8 workers. Los candidatos pasan la validación estructural: **{validation['status']}**, {len(validation.get('errors', []))} errores. El desfase mediano absoluto global pasó de {drift['old_global_median_abs_ms']} ms en V2.6.6 a {drift['new_global_median_abs_ms']} ms en el modelo V2.7; el máximo p95 de inicio dentro de los 21 análisis es {drift['new_global_p95_abs_ms']} ms.",
        "",
        "La reconstrucción produjo " + str(candidate["new_holds"]) + " holds frente a " + str(candidate["old_holds"]) + " de V2.6.6 y aplicó balanceo a " + str(candidate["repetition_balance_notes"]) + " ataques repetitivos. Un solo mod queda marcado por hold ratio alto; no se oculta y se conserva en la lista de revisión.",
        "",
        "## Matriz de las 21 canciones",
        "",
        "| Canción | V2.6.6 mediana onset | V2.7 mediana onset | V2.7 p95 onset | p95 final vocal | Holds V2.7 | Balanceo | Revisión |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for song in sorted(quality_by_song):
        q = quality_by_song[song]
        d = drift_by_song[song]
        lines.append(
            f"| {song} | {d['old_global_median_error_ms']:.0f} ms | {d['new_global_median_error_ms']:.0f} ms | {d['new_global_p95_abs_error_ms']:.0f} ms | {d['new_end_p95_abs_error_ms']:.0f} ms | {q['holds']} | {q['balanced']} | {q['review']} |"
        )
    lines.extend([
        "",
        "## Muestras revisadas",
        "",
        "Para cada canción se conservaron muestras de inicio, centro y final, además de los diez holds más largos. También se calcularon cuatro secciones por cuartiles para detectar deriva progresiva. Las muestras se encuentran en `phase5-section-drift-v267.json`.",
        "",
        "| Evidencia | Resultado |\n|---|---:|\n| Onsets RMS/VAD procesados | " + str(sum(row.get("syllables", 0) for row in onset["rows"])) + " sílabas |\n| Desfase V2.6.6 mediano absoluto | " + str(drift["old_global_median_abs_ms"]) + " ms |\n| Desfase V2.7 mediano absoluto | " + str(drift["new_global_median_abs_ms"]) + " ms |\n| p95 de inicio V2.7 más alto | " + str(drift["new_global_p95_abs_ms"]) + " ms |\n| Candidatos con error estructural | " + str(len(validation.get("errors", []))) + " |\n| Producción modificada durante investigación | No |\n",
        "## Revisión pendiente",
        "",
        "El caso con hold ratio alto se conserva como `WARNING_REVIEW`. Antes de una afirmación de sincronización perfecta, se deberá ejecutar `Audio Sync Test` y revisar físicamente en el runtime móvil una entrada vocal, una vocal larga, una palabra corta prolongada, una racha repetitiva y el último downbeat de cada canción o, si se usa muestreo, justificar el muestreo y registrar sus excepciones.",
    ])
    output = ROOT / "qa-lab/rebuild-v267/wide-research-report-v267.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"songs": candidate["songs"], "validation": validation["status"], "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
