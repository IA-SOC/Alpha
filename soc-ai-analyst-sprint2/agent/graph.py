"""
Agente investigador SOC como workflow explícito en LangGraph.

El grafo implementa las seis fases obligatorias de la skill
skills/soc-case-investigator (SKILL.md), en el mismo orden y sin atajos:

    recibir_validar → investigar_hipotesis → cronologia_alcance
        → consumir_ioc → generar_validar_reporte → revision_humana

- Las fases 2 y 3 llaman a los MCP servers existentes (map_to_mitre,
  generate_attack_hypothesis, build_case_timeline); la lógica sigue en core/.
- La fase 5 ejecuta el validador de la skill (scripts/validate_report.py).
  Si falla, el grafo termina sin pasar el reporte a revisión.
- La fase 6 pausa el grafo con interrupt(): el reporte queda con
  review.status = "pending" hasta que un analista lo valide, corrija o
  rechace. El estado se guarda en un checkpointer, así el caso puede
  retomarse después con el mismo thread_id.
- Cada fase agrega una entrada a audit_log para demostrar el orden.

Uso:
    python agent/graph.py data/synthetic/phishing_ecs.json
"""
import asyncio
import json
import operator
import os
import subprocess
import sys
import tempfile
import time
from contextlib import AsyncExitStack
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, TypedDict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from agent import investigation as inv
from agent.normalize import normalize_case
from agent.render import render_markdown
from app.services.agent_adapter import correlate_direct
from app.services.report_formatter import format_report, validate_audience_sections
from orchestrator.client import SERVERS, McpToolClient

SKILL_DIR = ROOT / "skills" / "soc-case-investigator"
VALIDATOR = SKILL_DIR / "scripts" / "validate_report.py"
SKILL_NAME = "soc-case-investigator"
SCHEMA_ID = "urn:soc-investigation-report:schema:1.1"

PHASES = [
    "recibir_validar",
    "investigar_hipotesis",
    "cronologia_alcance",
    "consumir_ioc",
    "generar_validar_reporte",
    "revision_humana",
]


class InvestigationState(TypedDict, total=False):
    case: Dict[str, Any]
    alerts: List[Dict[str, Any]]
    input_summary: Dict[str, Any]
    mitre_mappings: List[Dict[str, Any]]
    chain: Dict[str, Any]
    correlation: Optional[Dict[str, Any]]
    attack_mapping: List[Dict[str, Any]]
    hypotheses: List[Dict[str, Any]]
    timeline: List[Dict[str, Any]]
    blast_radius: Dict[str, Any]
    enrichment: Dict[str, Any]
    report: Dict[str, Any]
    report_markdown: str
    validation: Dict[str, Any]
    audit_log: Annotated[List[Dict[str, Any]], operator.add]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _audit(phase: str, started: float, detail: str) -> Dict[str, Any]:
    return {"phase": PHASES.index(phase) + 1, "node": phase, "finished_at": _now(),
            "duration_ms": round((time.perf_counter() - started) * 1000), "detail": detail}


def _mcp_view(alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Solo los campos que usa core/logic.py; el registro original no viaja por MCP."""
    keys = ("id", "timestamp", "rule_name", "tags", "host", "user", "source_ip", "dest_ip")
    return [{k: a.get(k) for k in keys} for a in alerts]


async def call_tool(server: str, tool: str, arguments: Dict[str, Any]) -> Any:
    async with AsyncExitStack() as stack:
        return await McpToolClient(SERVERS[server]).call(stack, tool, arguments)


# --- Fase 1 -----------------------------------------------------------------
def recibir_validar(state: InvestigationState) -> Dict[str, Any]:
    started = time.perf_counter()
    alerts, summary = normalize_case(state["case"])
    return {
        "alerts": alerts,
        "input_summary": summary,
        "audit_log": [_audit("recibir_validar", started,
                             f"{summary['processed_alert_count']} alertas, formato {summary['source_format']}")],
    }


# --- Fase 2 -----------------------------------------------------------------
async def investigar_hipotesis(state: InvestigationState) -> Dict[str, Any]:
    started = time.perf_counter()
    alerts = state["alerts"]
    mappings = await call_tool("mitre", "map_to_mitre", {"alerts": _mcp_view(alerts)}) if alerts else []
    chain = await call_tool("hypothesis", "generate_attack_hypothesis", {"mitre_mappings": mappings})
    synthetic = bool(state["case"].get("synthetic"))
    context = state["case"].get("investigation_context", {})
    correlation = (context["correlation"] if context.get("adapter_version") == "backend-v1"
                   else correlate_direct(state["case"], alerts) if alerts else None)
    # The legacy chain combines techniques globally, across unrelated alerts;
    # never present that as an established attack sequence.
    if correlation:
        analysis = inv.correlated_attack_analysis(alerts, mappings, synthetic, {"correlation": correlation})
        chain = {**chain, "summary": "Técnicas candidatas evaluadas por grupos de alertas; "
                 "la correlación no demuestra causalidad ni una secuencia de ataque."}
    else:
        analysis = inv.build_attack_analysis(alerts, mappings, synthetic)
        if mappings:
            chain = {**chain, "summary": "Técnicas candidatas evaluadas sin correlación de alertas; "
                     "no se afirma una secuencia de ataque."}
    return {
        "mitre_mappings": mappings,
        "chain": chain,
        "correlation": correlation,
        **analysis,
        "audit_log": [_audit("investigar_hipotesis", started,
                             f"{len(mappings)} técnicas candidatas, {len(analysis['hypotheses'])} hipótesis")],
    }


# --- Fase 3 -----------------------------------------------------------------
async def cronologia_alcance(state: InvestigationState) -> Dict[str, Any]:
    started = time.perf_counter()
    alerts = state["alerts"]
    mcp_timeline = await call_tool(
        "timeline", "build_case_timeline",
        {"alerts": _mcp_view(alerts), "mitre_mappings": state["mitre_mappings"]},
    ) if alerts else []
    blast = inv.build_blast_radius(alerts, state["hypotheses"])
    return {
        "timeline": inv.build_timeline(alerts, mcp_timeline),
        "blast_radius": blast,
        "audit_log": [_audit("cronologia_alcance", started,
                             f"{len(mcp_timeline)} eventos, {len(blast['observed_assets'])} activos observados")],
    }


# --- Fase 4 -----------------------------------------------------------------
def consumir_ioc(state: InvestigationState) -> Dict[str, Any]:
    started = time.perf_counter()
    enrichment = inv.consume_enrichment(state["case"], state["alerts"])
    return {
        "enrichment": enrichment,
        "hypotheses": inv.attach_ioc_references(state["hypotheses"], enrichment),
        "audit_log": [_audit("consumir_ioc", started,
                             f"estado {enrichment['status']}, {len(enrichment['items'])} IoC")],
    }


# --- Fase 5 -----------------------------------------------------------------
def run_skill_validator(case: Dict[str, Any], report: Dict[str, Any]) -> Dict[str, Any]:
    audience_error = ""
    try:
        validate_audience_sections(report)
    except (ValueError, KeyError, TypeError) as exc:
        audience_error = str(exc)
    with tempfile.TemporaryDirectory() as tmp:
        case_path, report_path = Path(tmp) / "case.json", Path(tmp) / "report.json"
        case_path.write_text(json.dumps(case, ensure_ascii=False), encoding="utf-8")
        report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(VALIDATOR), "--case", str(case_path), "--report", str(report_path)],
            capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
    return {"ok": proc.returncode == 0 and not audience_error,
            "returncode": proc.returncode or (1 if audience_error else 0),
            "output": (proc.stdout + proc.stderr + "\n" + audience_error).strip()}


def generar_validar_reporte(state: InvestigationState) -> Dict[str, Any]:
    started = time.perf_counter()
    case, summary = state["case"], state["input_summary"]
    report = {
        "case_id": str(case.get("case_id") or "sin-id"),
        "generated_at": _now(),
        "methodology": {"skill": SKILL_NAME, "report_schema": SCHEMA_ID,
                        "engine": "LangGraph + MCP servers (reglas deterministas)",
                        "attack_catalog": inv.CATALOG_VERSION},
        "input": {k: v for k, v in summary.items() if k != "untrusted_instruction_fields"},
        "executive_summary": inv.executive_summary(case, state["chain"], state["hypotheses"],
                                                   summary["processed_alert_count"]),
        "attack_mapping": state["attack_mapping"],
        "hypotheses": [{k: v for k, v in h.items() if k != "tactic"} for h in state["hypotheses"]],
        "timeline": state["timeline"],
        "blast_radius": state["blast_radius"],
        "enrichment": state["enrichment"],
        "recommended_actions": inv.build_actions(state["hypotheses"]),
        "limitations": inv.build_limitations(case, summary),
        "audit_trail": state["audit_log"],
        "review": {"status": "pending", "analyst": None, "notes": None, "reviewed_at": None},
    }
    context = case.get("investigation_context", {})
    if context.get("adapter_version") == "backend-v1":
        report["submitted_case_id"] = context["submitted_case_id"]
    if state.get("correlation"):
        report["correlation"] = state["correlation"]
        report["limitations"] += state["correlation"]["limitations"]
    elif state["alerts"]:
        report["limitations"].append(
            "No se pudo correlacionar las alertas (IDs duplicados o alertas fuera del contrato v1.0); "
            "las hipótesis agrupan por técnica y pueden mezclar actividad no relacionada.")
    report["audience_sections"] = format_report(report)
    validation = run_skill_validator(case, report)
    return {
        "report": report,
        "report_markdown": render_markdown(report),
        "validation": validation,
        "audit_log": [_audit("generar_validar_reporte", started,
                             "validador OK" if validation["ok"] else "validador FALLÓ")],
    }


def ruta_tras_validacion(state: InvestigationState) -> str:
    return "revision_humana" if state["validation"]["ok"] else END


# --- Fase 6 -----------------------------------------------------------------
def revision_humana(state: InvestigationState) -> Dict[str, Any]:
    started = time.perf_counter()
    decision = interrupt({
        "case_id": state["report"]["case_id"],
        "message": "Borrador listo. Valide, corrija o rechace los hallazgos.",
        "report_markdown": state["report_markdown"],
    })
    status = decision.get("status")
    if status not in ("validated", "corrected", "rejected"):
        raise ValueError(f"Decisión de revisión inválida: {status!r}")
    report = dict(state["report"])
    report["review"] = {"status": status, "analyst": decision.get("analyst"),
                        "notes": decision.get("notes"), "reviewed_at": _now()}
    report["audience_sections"] = format_report(report)
    return {
        "report": report,
        "report_markdown": render_markdown(report),
        "audit_log": [_audit("revision_humana", started, f"decisión del analista: {status}")],
    }


def build_graph(checkpointer: Optional[Any] = None):
    graph = StateGraph(InvestigationState)
    graph.add_node("recibir_validar", recibir_validar)
    graph.add_node("investigar_hipotesis", investigar_hipotesis)
    graph.add_node("cronologia_alcance", cronologia_alcance)
    graph.add_node("consumir_ioc", consumir_ioc)
    graph.add_node("generar_validar_reporte", generar_validar_reporte)
    graph.add_node("revision_humana", revision_humana)

    graph.add_edge(START, "recibir_validar")
    graph.add_edge("recibir_validar", "investigar_hipotesis")
    graph.add_edge("investigar_hipotesis", "cronologia_alcance")
    graph.add_edge("cronologia_alcance", "consumir_ioc")
    graph.add_edge("consumir_ioc", "generar_validar_reporte")
    graph.add_conditional_edges("generar_validar_reporte", ruta_tras_validacion, ["revision_humana", END])
    graph.add_edge("revision_humana", END)
    return graph.compile(checkpointer=checkpointer or InMemorySaver())


async def investigate(case: Dict[str, Any], thread_id: str, app=None) -> Dict[str, Any]:
    """Corre las fases 1-5 y se detiene en la revisión humana (o en END si el validador falla)."""
    app = app or build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    await app.ainvoke({"case": case, "audit_log": []}, config)
    return app.get_state(config).values


async def submit_review(app, thread_id: str, decision: Dict[str, Any]) -> Dict[str, Any]:
    config = {"configurable": {"thread_id": thread_id}}
    await app.ainvoke(Command(resume=decision), config)
    return app.get_state(config).values


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    case_path = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "data" / "sample_case_bruteforce.json")
    with open(case_path, encoding="utf-8") as f:
        case = json.load(f)
    state = asyncio.run(investigate(case, thread_id=str(case.get("case_id"))))
    print(state["report_markdown"])
    print(f"Validador de la skill: {state['validation']['output']}", file=sys.stderr)
