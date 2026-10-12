"""
Corre el agente sobre todos los casos sintéticos y guarda los borradores.

Uso:
    python agent/run_synthetic.py
Salida: data/reportes_sinteticos/<caso>.json y <caso>.md (review.status = pending).
"""
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.graph import investigate

OUT = ROOT / "data" / "reportes_sinteticos"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    cases = [ROOT / "data" / "sample_case_bruteforce.json", *sorted((ROOT / "data" / "synthetic").glob("*.json"))]
    for path in cases:
        case = json.loads(path.read_text(encoding="utf-8"))
        started = time.perf_counter()
        state = asyncio.run(investigate(case, thread_id=path.stem))
        elapsed = time.perf_counter() - started
        report = state["report"]
        (OUT / f"{path.stem}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        (OUT / f"{path.stem}.md").write_text(state["report_markdown"], encoding="utf-8")
        hypotheses = "; ".join(
            f"{h['rank']}. {h['statement'].split(' en ')[0].replace('Actividad compatible con ', '')} = {h['confidence']}"
            for h in report["hypotheses"]
        ) or "sin hipótesis"
        print(f"{path.stem}: formato={report['input']['source_format']}, alertas={report['input']['alert_count']}, "
              f"validador={'OK' if state['validation']['ok'] else 'FALLÓ'}, {elapsed:.1f}s, "
              f"IoC={report['enrichment']['status']}, "
              f"sospechosos={[a['asset'] for a in report['blast_radius']['suspected_assets']]}, "
              f"acciones={len(report['recommended_actions'])} | {hypotheses}")


if __name__ == "__main__":
    main()
