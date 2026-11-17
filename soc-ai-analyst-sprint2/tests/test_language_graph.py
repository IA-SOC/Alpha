"""Offline language selection tests for the investigation graph."""

SPANISH_MARKERS = ("á", "é", "í", "ó", "ú", "ñ", "¿", "¡")
SPANISH_WORDS = (" de ", " la ", " el ", " con ", " sin ", "alerta")
PROTOCOL_KEYS = {
    "id", "alert_id", "evidence_id", "tags", "rule_name", "host", "user",
    "observation", "source_fields", "mapping_source", "confidence", "status",
    "assessment", "stage", "tactic", "technique_id", "technique_name",
}
PROTOCOL_VALUES = {"media", "alta", "baja", "insuficiente"}


def _free_text(value, key=""):
    if key in PROTOCOL_KEYS:
        return
    if isinstance(value, dict):
        for child_key, child in value.items():
            yield from _free_text(child, child_key)
    elif isinstance(value, list):
        for child in value:
            yield from _free_text(child, key)
    elif isinstance(value, str) and value not in PROTOCOL_VALUES:
        yield value


def _contains_spanish(text):
    lowered = text.lower()
    return any(marker in lowered for marker in SPANISH_MARKERS + SPANISH_WORDS)


def test_english_report_uses_english_free_text_without_provider(client, monkeypatch):
    from tests.helpers import investigate, tagged

    monkeypatch.setenv("REPORT_LANGUAGE", "en")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    result = investigate(client, tagged("a", ["brute_force"]))
    report = result["report"]
    selected = {
        "executive_summary": report["executive_summary"],
        "hypotheses": report["hypotheses"],
        "recommended_actions": report["recommended_actions"],
        "limitations": report["limitations"],
        "blast_radius": {"unknowns": report["blast_radius"]["unknowns"]},
        "enrichment": {"note": report["enrichment"]["note"]},
        "timeline": report["timeline"],
        "audit_trail": report["audit_trail"],
        "audience_sections": report["audience_sections"],
        "report_markdown": result["report_markdown"],
    }
    free_text = list(_free_text(selected))
    assert free_text
    assert not [text for text in free_text if _contains_spanish(text)]
    assert "(original wording)" not in str(report["audience_sections"])


def test_mock_provider_and_instruction_follow_selected_language(monkeypatch):
    from agent.llm import MockProvider
    from agent.prompts import language_instruction

    context = {"alerts": [{"id": "a"}], "hypotheses": []}
    monkeypatch.setenv("REPORT_LANGUAGE", "en")
    english, _ = MockProvider().review(context)
    assert "Deterministic assessment" in english["initial_assessment"]["assessment"]
    assert language_instruction()
    monkeypatch.setenv("REPORT_LANGUAGE", "es")
    spanish, _ = MockProvider().review(context)
    assert "Evaluación determinista" in spanish["initial_assessment"]["assessment"]
    assert language_instruction() == ""


def test_default_spanish_output_is_preserved(client, monkeypatch):
    from tests.helpers import investigate, tagged

    monkeypatch.delenv("REPORT_LANGUAGE", raising=False)
    result = investigate(client, tagged("a", ["brute_force"]))
    assert "alertas" in result["report"]["executive_summary"]
    assert "en host" in result["report"]["timeline"][0]["description"]
