"""
Pruebas del agente LangGraph con los casos sintéticos de data/.

Cada caso recorre el grafo real: levanta los MCP servers por stdio y ejecuta
el validador de la skill soc-case-investigator. Son smoke tests de
comportamiento, no una medición de precisión.
"""
import asyncio
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.graph import PHASES, build_graph, ruta_tras_validacion, run_skill_validator, submit_review
from agent.investigation import build_actions
from langgraph.graph import END

CASES = {
    "bruteforce_simple": ROOT / "data" / "sample_case_bruteforce.json",
    "phishing_ecs": ROOT / "data" / "synthetic" / "phishing_ecs.json",
    "bruteforce_wazuh": ROOT / "data" / "synthetic" / "bruteforce_wazuh.json",
    "exfiltration": ROOT / "data" / "synthetic" / "exfiltration.json",
    "pre_ransomware": ROOT / "data" / "synthetic" / "pre_ransomware.json",
    "benign_noise": ROOT / "data" / "synthetic" / "benign_noise.json",
}

EXPECTED_TECHNIQUES = {
    "bruteforce_simple": {"T1110", "T1021"},
    "phishing_ecs": {"T1566"},
    "bruteforce_wazuh": {"T1110", "T1021"},
    "exfiltration": {"T1041"},
    "pre_ransomware": {"T1021", "T1569.002", "T1490", "T1486"},
    "benign_noise": set(),
}

EXPECTED_FORMAT = {
    "bruteforce_simple": "unknown",
    "phishing_ecs": "elastic_ecs",
    "bruteforce_wazuh": "wazuh",
    "exfiltration": "unknown",
    "pre_ransomware": "unknown",
    "benign_noise": "unknown",
}


def load(name):
    return json.loads(CASES[name].read_text(encoding="utf-8"))


async def _run(name):
    app = build_graph()
    config = {"configurable": {"thread_id": name}}
    await app.ainvoke({"case": load(name), "audit_log": []}, config)
    snapshot = app.get_state(config)
    return app, snapshot


@pytest.fixture(scope="module")
def runs():
    """Corre cada caso una vez hasta la pausa de revisión humana."""
    return {name: asyncio.run(_run(name)) for name in CASES}


@pytest.mark.parametrize("name", CASES)
def test_pausa_en_revision_humana_con_reporte_valido(runs, name):
    _, snapshot = runs[name]
    state = snapshot.values
    assert state["validation"]["ok"], state["validation"]["output"]
    assert snapshot.next == ("revision_humana",)
    assert state["report"]["review"]["status"] == "pending"


@pytest.mark.parametrize("name", CASES)
def test_fases_1_a_5_en_orden(runs, name):
    _, snapshot = runs[name]
    assert [e["node"] for e in snapshot.values["audit_log"]] == PHASES[:5]


@pytest.mark.parametrize("name", CASES)
def test_tecnicas_y_formato_esperados(runs, name):
    report = runs[name][1].values["report"]
    assert {m["technique_id"] for m in report["attack_mapping"]} == EXPECTED_TECHNIQUES[name]
    assert all(m["status"] == "candidate" for m in report["attack_mapping"])
    assert report["input"]["source_format"] == EXPECTED_FORMAT[name]


@pytest.mark.parametrize("name", CASES)
def test_sin_porcentajes_ni_confirmaciones(runs, name):
    report = runs[name][1].values["report"]
    assert report["blast_radius"]["confirmed_assets"] == []
    assert all(h["confidence"] in {"alta", "media", "baja", "insuficiente"} for h in report["hypotheses"])
    assert "%" not in report["executive_summary"]
    assert all(a["requires_human_approval"] for a in report["recommended_actions"])


def test_sinteticos_no_superan_confianza_media(runs):
    for name in CASES:
        if load(name).get("synthetic"):
            assert all(h["confidence"] != "alta" for h in runs[name][1].values["report"]["hypotheses"])


def test_wazuh_respaldo_legitimo_queda_ambiguo(runs):
    report = runs["bruteforce_wazuh"][1].values["report"]
    lateral = next(h for h in report["hypotheses"] if "T1021" in h["statement"])
    assert {e["alert_id"] for e in lateral["evidence_against"]} == {"1726388101.1007", "1726388160.1008"}
    assert lateral["confidence"] in {"baja", "insuficiente"}
    assert "db-02" not in {a["asset"] for a in report["blast_radius"]["suspected_assets"]}
    assert "db-02" in {a["asset"] for a in report["blast_radius"]["observed_assets"]}
    # Timestamps -0500 normalizados a UTC sin perder el original.
    first = report["timeline"][0]
    assert first["timestamp_original"] == "2026-09-15T03:02:11.000-0500"
    assert first["timestamp_utc"] == "2026-09-15T08:02:11Z"


def test_phishing_texto_hostil_es_dato_no_instruccion(runs):
    report = runs["phishing_ecs"][1].values["report"]
    assert report["review"]["status"] == "pending"
    assert any("ecs-ph-001.email.subject" in l and "no confiable" in l for l in report["limitations"])


def test_phishing_ioc_solo_del_caso_por_valor_exacto(runs):
    enrichment = runs["phishing_ecs"][1].values["report"]["enrichment"]
    by_value = {i["indicator"]: i["matched_alert_ids"] for i in enrichment["items"]}
    assert by_value["198.51.100.23"] == ["ecs-ph-002"]
    assert by_value["https://login-proveedor-pagos.example/o365"] == ["ecs-ph-001", "ecs-ph-002"]
    assert by_value["203.0.113.200"] == []
    assert "203.0.113.200" in enrichment["note"]


def test_sin_enriquecimiento_se_declara_no_disponible(runs):
    assert runs["exfiltration"][1].values["report"]["enrichment"]["status"] == "no_disponible"


def test_ruido_benigno_sin_hipotesis_y_con_limitaciones(runs):
    report = runs["benign_noise"][1].values["report"]
    assert report["hypotheses"] == [] and report["recommended_actions"] == []
    assert "bn-3: timestamp" in report["input"]["missing_fields"]
    assert any("bn-2" in l and "sin zona horaria" in l for l in report["limitations"])
    bn2 = next(t for t in report["timeline"] if t["alert_ids"] == ["bn-2"])
    assert bn2["timezone_unknown"] is True and bn2["timestamp_utc"] is None


def test_ransomware_prioriza_impacto(runs):
    actions = runs["pre_ransomware"][1].values["report"]["recommended_actions"]
    assert actions[0]["priority"] == "urgent"


def test_acciones_comparten_tactica_y_unen_evidencia():
    actions = build_actions([
        {"rank": 1, "tactic": "Initial Access", "confidence": "media",
         "evidence_for": [{"alert_id": "a-1"}]},
        {"rank": 3, "tactic": "Initial Access", "confidence": "baja",
         "evidence_for": [{"alert_id": "a-2"}, {"alert_id": "a-1"}]},
    ])
    assert len(actions) == 1
    assert actions[0]["hypothesis_ranks"] == [1, 3]
    assert actions[0]["evidence_ids"] == ["a-1", "a-2"]
    assert actions[0]["approval_status"] == "pending"


def test_retomar_con_decision_del_analista(runs):
    app, _ = runs["bruteforce_simple"]
    state = asyncio.run(submit_review(app, "bruteforce_simple",
                                      {"status": "validated", "analyst": "analista-l2", "notes": "OK"}))
    assert [e["node"] for e in state["audit_log"]] == PHASES
    assert state["report"]["review"]["status"] == "validated"
    assert state["report"]["review"]["analyst"] == "analista-l2"
    assert app.get_state({"configurable": {"thread_id": "bruteforce_simple"}}).next == ()


def test_decision_invalida_se_rechaza(runs):
    app, _ = runs["exfiltration"]
    with pytest.raises(ValueError):
        asyncio.run(submit_review(app, "exfiltration", {"status": "closed"}))


def test_validador_rechaza_referencia_rota_y_el_grafo_no_pasa_a_revision(runs):
    state = runs["pre_ransomware"][1].values
    report = json.loads(json.dumps(state["report"]))
    report["blast_radius"]["observed_assets"][0]["basis_alert_ids"] = ["not-an-alert"]
    result = run_skill_validator(state["case"], report)
    assert not result["ok"] and "not-an-alert" in result["output"]
    assert ruta_tras_validacion({"validation": result}) == END


def test_validador_rechaza_rango_de_hipotesis_inexistente(runs):
    state = runs["pre_ransomware"][1].values
    report = json.loads(json.dumps(state["report"]))
    report["recommended_actions"][0]["hypothesis_ranks"] = [999]
    result = run_skill_validator(state["case"], report)
    assert not result["ok"] and "unknown hypothesis rank 999" in result["output"]


def _pointer(case, path):
    value = case
    for part in path.lstrip("/").split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


@pytest.mark.parametrize("name", CASES)
def test_evidencia_cita_campos_originales_en_ruta_directa(runs, name):
    """#43: timeline, mapeo MITRE e hipótesis citan el campo crudo por JSON Pointer."""
    case, report = load(name), runs[name][1].values["report"]
    evidence = [*report["timeline"]]
    evidence += [e for m in report["attack_mapping"] for e in m["evidence"]]
    evidence += [e for h in report["hypotheses"] for e in h["evidence_for"] + h["evidence_against"]]
    for item in evidence:
        assert item["source_fields"]
        for field in item["source_fields"]:
            assert _pointer(case, field["path"]) == field["value"]
