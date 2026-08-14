#!/usr/bin/env python3
"""Genera una matriz legible de revisión manual a partir de la evidencia vocal consolidada."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    source = root / "sync-candidates" / "vocal-stem-consolidation.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    rows = []
    for entry in data["entries"]:
        rows.append(
            f"| `{entry['song']}` | {entry['status']} | {entry['candidate_base_notes']} | Pendiente | Pendiente | `MANUAL_REVIEW_REQUIRED` |"
        )
    report = """# Matriz de revisión oficial de sincronía vocal

## Estado de la evidencia automática

La separación vocal serial y el análisis de candidatos se completaron sobre las 20 canciones. Cada stem se verificó por SHA-256, se vinculó con el hash del OGG distribuido y generó un candidate chart aislado. No se modificaron charts de producción.

> Esta tabla **no certifica sincronía vocal perfecta**. `PASS` solo indica que el stem y el candidato son trazables y estructuralmente válidos. La aprobación musical exige el Audio Sync Test y el playtest móvil del motor oficial.

| Canción | Evidencia stem/candidato | Notas candidatas base | Audio Sync Test | Playtest V-Slice móvil | Estado de promoción |
|---|---:|---:|---|---|---|
""" + "\n".join(rows) + """

## Protocolo por canción

En el Chart Editor, cargar el OGG indicado en el manifiesto, abrir el chart candidato solo como referencia y ejecutar **Audio Sync Test**. Revisar, como mínimo, el primer downbeat, primera entrada vocal, sección central, un hold largo, una sección densa, cada cambio de BPM y el último downbeat. Registrar offsets independientes de instrumental y voces cuando correspondan.

Después, exportar el chart aprobado y probar inicio, centro y final en FNF Mobile V-Slice 0.8.6. La latencia del teléfono debe calibrarse como ajuste del jugador, no desplazando silenciosamente el chart. Si todos los controles son correctos, registrar hashes del OGG final, resultado de Audio Sync Test y evidencia del playtest antes de promover el candidato.

## Limitación del entorno actual

No se detectaron `adb`, emulador Android, APK instalada de FNF Mobile ni ejecutable de FNF V-Slice en el entorno de trabajo. Por eso estas dos pruebas oficiales no pueden simularse ni declararse completadas desde aquí.

## Referencias

[1] [FunkinCrew — Chart Editor](https://funkincrew-funkin-59.mintlify.app/tools/chart-editor)

[2] [FunkinCrew — Gameplay timing y offsets](https://funkincrew-funkin-59.mintlify.app/systems/gameplay)
"""
    target = root / "docs" / "matriz_revision_oficial_sincronia.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report, encoding="utf-8")
    print(target)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
