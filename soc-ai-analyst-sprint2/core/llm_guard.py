"""Contexto mínimo y validación de salida para una segunda opinión de modelo."""
import json
from typing import Any, Dict, List

from agent.normalize import INJECTION_PATTERN

REDACTED = "[contenido no confiable omitido]"


def _safe(value: Any, max_chars: int, stats: Dict[str, int]) -> Any:
    if isinstance(value, str):
        if value == REDACTED:
            return value
        if INJECTION_PATTERN.search(value):
            stats["redacted_fields"] += 1
            return REDACTED
        return value[:max_chars]
    if isinstance(value, list):
        return [_safe(item, max_chars, stats) for item in value]
    if isinstance(value, dict):
        return {key: _safe(item, max_chars, stats) for key, item in value.items()}
    return value


def _alert_view(alert: Dict[str, Any], max_chars: int, stats: Dict[str, int]) -> Dict[str, Any]:
    return _safe({"id": alert.get("id"), "timestamp": alert.get("timestamp"), "host": alert.get("host"),
                  "rule_name": alert.get("rule_name"), "tags": alert.get("tags", [])}, max_chars, stats)


def _ioc_view(item: Dict[str, Any], max_chars: int, stats: Dict[str, int]) -> Dict[str, Any]:
    observable = item.get("observable") if isinstance(item.get("observable"), dict) else {}
    return _safe({"indicator": observable.get("value") or item.get("indicator"),
                  "type": observable.get("type") or item.get("type"), "provider": item.get("provider"),
                  "verdict": item.get("verdict")}, max_chars, stats)


def build_model_context(alerts: List[Dict[str, Any]], hypotheses: List[Dict[str, Any]],
                        max_alerts_per_hypothesis: int = 10, max_chars: int = 300) -> Dict[str, Any]:
    """Reduce y sanea datos no confiables antes de entregarlos a un proveedor."""
    by_id = {str(alert.get("id")): alert for alert in alerts}
    stats = {"alerts_sent": 0, "iocs_sent": 0, "redacted_fields": 0}
    items = []
    for hypothesis in hypotheses:
        evidence_for = [str(item.get("alert_id")) for item in hypothesis.get("evidence_for", [])]
        evidence_against = [str(item.get("alert_id")) for item in hypothesis.get("evidence_against", [])]
        ids = list(dict.fromkeys(evidence_for + evidence_against))[:max_alerts_per_hypothesis]
        selected = [_alert_view(by_id[alert_id], max_chars, stats) for alert_id in ids if alert_id in by_id]
        iocs = [_ioc_view(item, max_chars, stats) for item in hypothesis.get("ioc_evidence", [])]
        stats["alerts_sent"] += len(selected)
        stats["iocs_sent"] += len(iocs)
        items.append(_safe({"rank": hypothesis.get("rank"), "statement": hypothesis.get("statement"),
                            "confidence": hypothesis.get("confidence"), "evidence_for_ids": evidence_for,
                            "evidence_against_ids": evidence_against, "alerts": selected, "iocs": iocs},
                           max_chars, stats))
    stats["chars"] = len(json.dumps(items, ensure_ascii=False))
    return {"hypotheses": items, "stats": stats}


def check_model_output(output: Any, context: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Acepta únicamente referencias y evaluaciones permitidas por el contexto."""
    if not isinstance(output, dict) or not isinstance(output.get("items"), list):
        return {"items": [], "rejected": [{"index": None, "reason": "salida sin lista items"}]}
    allowed = {item.get("rank"): set(item.get("evidence_for_ids", [])) | set(item.get("evidence_against_ids", []))
               for item in context.get("hypotheses", []) if isinstance(item, dict)}
    valid, rejected, seen = [], [], set()
    for index, item in enumerate(output["items"]):
        if not isinstance(item, dict):
            rejected.append({"index": index, "reason": "item no es objeto"})
            continue
        rank, assessment = item.get("rank"), item.get("assessment")
        explanation, cited = item.get("explanation"), item.get("cited_alert_ids")
        if rank not in allowed:
            reason = "rango desconocido"
        elif rank in seen:
            reason = "rango duplicado"
        elif assessment not in {"supports", "weak", "contradicts"}:
            reason = "evaluación inválida"
        elif not isinstance(explanation, str) or not explanation.strip() or len(explanation) > 600:
            reason = "explicación inválida"
        elif INJECTION_PATTERN.search(explanation):
            reason = "explicación no confiable"
        elif not isinstance(cited, list) or not cited or any(not isinstance(ref, str) or ref not in allowed[rank] for ref in cited):
            reason = "referencias inválidas"
        else:
            seen.add(rank)
            valid.append({"rank": rank, "assessment": assessment, "explanation": explanation,
                          "cited_alert_ids": cited})
            continue
        rejected.append({"index": index, "reason": reason})
    return {"items": valid, "rejected": rejected}
