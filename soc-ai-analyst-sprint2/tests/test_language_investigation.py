"""Language selection for investigation text is evaluated at call time."""

from typing import Any

from agent.investigation import (
    build_attack_analysis,
    build_limitations,
    executive_summary,
    ordinal_confidence,
)

PROTOCOL_KEYS = {
    "confidence", "status", "role", "tags", "ids", "rule_name", "host", "user",
    "observation", "source_fields", "mapping_source",
}
SPANISH_MARKERS = (" de ", " la ", " el ", " con ", " sin ", "alerta")


def _free_text_strings(value: Any, key: str | None = None) -> list[str]:
    if isinstance(value, dict):
        return [text for item_key, item in value.items()
                for text in _free_text_strings(item, item_key)]
    if isinstance(value, list):
        return [text for item in value for text in _free_text_strings(item, key)]
    return [value] if isinstance(value, str) and key not in PROTOCOL_KEYS else []


def _alert(alert_id: str) -> dict[str, Any]:
    return {
        "id": alert_id,
        "rule_name": "brute_force",
        "tags": ["brute_force"],
        "host": "web-01",
        "user": "alice",
        "timestamp_problem": False,
        "source_fields": [],
    }


def test_investigation_text_is_english_when_requested(monkeypatch):
    monkeypatch.setenv("REPORT_LANGUAGE", "en")
    alert = _alert("A-1")
    analysis = build_attack_analysis([alert], [{
        "supporting_alert_ids": ["A-1"],
        "technique_id": "T1110",
        "technique_name": "Brute Force",
        "tactic": "Credential Access",
        "mapping_source": "local_catalog",
    }], synthetic=False)
    confidence = ordinal_confidence([alert], [], synthetic=False)
    limitations = build_limitations({"synthetic": False}, {
        "warnings": [], "untrusted_instruction_fields": [],
    })
    summary = executive_summary(
        {"case_id": "LANG-1"}, {"summary": "No sequence identified."},
        analysis["hypotheses"], processed=1,
    )
    for text in _free_text_strings({
        "analysis": analysis, "confidence": confidence, "limitations": limitations,
        "summary": summary,
    }):
        assert not any(char in text for char in "áéíóúñ¿¡"), text
        assert not any(marker in text.lower() for marker in SPANISH_MARKERS), text


def test_executive_summary_defaults_to_spanish(monkeypatch):
    monkeypatch.delenv("REPORT_LANGUAGE", raising=False)
    summary = executive_summary({"case_id": "LANG-ES"}, {"summary": ""}, [], 0)
    assert summary.startswith("Caso LANG-ES: 0 alertas procesadas.")
