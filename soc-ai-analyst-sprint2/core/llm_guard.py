"""Contexto mínimo y validación de salida de las tareas del modelo (hipótesis, evidencia, acciones)."""
import json
import re
from typing import Any, Dict, List, Optional

from agent.normalize import INJECTION_PATTERN

REDACTED = "[contenido no confiable omitido]"
TECHNIQUE = re.compile(r"\bT\d{4}(?:\.\d{3})?\b")
# shortcut: keyword heuristic (en/es) for "confirmed compromise" wording; swap for a claim
# classifier if it rejects legitimate text or misses paraphrases.
_CONFIRM = r"(?:confirm\w*|definitiv\w*|proven|probado)"
_COMPROMISE = r"(?:compromis\w*|exfiltrat\w*|exfiltrad\w*|breach\w*|brecha\w*|theft|robo)"
OVERCLAIM = re.compile(
    rf"\b{_CONFIRM}\W+(?:\w+\W+){{0,3}}{_COMPROMISE}|\b{_COMPROMISE}\W+(?:\w+\W+){{0,3}}{_CONFIRM}",
    re.IGNORECASE,
)
NEGATION = re.compile(r"\b(?:not|no|never|without|sin|ni)\b|n't", re.IGNORECASE)
PRIORITIES = {"low", "medium", "high", "urgent"}
TASK_KEYS = {"initial_assessment": ("assessment", "cited_alert_ids", "gaps"),
             "evidence": ("rank", "for", "against"),
             "suggested_actions": ("action", "priority", "rationale", "cited_alert_ids")}


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
    case_alerts = [_alert_view(alert, max_chars, stats) for alert in alerts[:50]]
    stats["case_alerts_sent"] = len(case_alerts)
    stats["chars"] = len(json.dumps({"hypotheses": items, "alerts": case_alerts}, ensure_ascii=False))
    return {"hypotheses": items, "alerts": case_alerts, "stats": stats}


def _overclaims(text: str) -> bool:
    """True when the text states a confirmed compromise that was not negated just before it."""
    return any(not NEGATION.search(text[max(0, m.start() - 30):m.start()]) for m in OVERCLAIM.finditer(text))


def _techniques(context: Dict[str, Any]) -> set:
    """Technique IDs the model may mention: those already in the hypothesis statements."""
    return set(TECHNIQUE.findall(" ".join(str(h.get("statement")) for h in context.get("hypotheses", []))))


def check_model_output(output: Any, context: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Acepta únicamente referencias y evaluaciones permitidas por el contexto."""
    if not isinstance(output, dict) or not isinstance(output.get("items"), list):
        return {"items": [], "rejected": [{"index": None, "reason": "salida sin lista items"}]}
    allowed = {item.get("rank"): set(item.get("evidence_for_ids", [])) | set(item.get("evidence_against_ids", []))
               for item in context.get("hypotheses", []) if isinstance(item, dict)}
    techniques = _techniques(context)
    valid, rejected, seen = [], [], set()
    for index, item in enumerate(output["items"]):
        if not isinstance(item, dict):
            rejected.append({"index": index, "reason": "item no es objeto"})
            continue
        rank, assessment = item.get("rank"), item.get("assessment")
        explanation, cited = item.get("explanation"), item.get("cited_alert_ids")
        if type(rank) is not int or rank not in allowed:
            reason = "rango desconocido"
        elif rank in seen:
            reason = "rango duplicado"
        elif not isinstance(assessment, str) or assessment not in {"supports", "weak", "contradicts"}:
            reason = "evaluación inválida"
        elif not isinstance(explanation, str) or not explanation.strip() or len(explanation) > 600:
            reason = "explicación inválida"
        elif INJECTION_PATTERN.search(explanation):
            reason = "explicación no confiable"
        elif _overclaims(explanation):
            reason = "conclusión no respaldada"
        elif set(TECHNIQUE.findall(explanation)) - techniques:
            reason = "técnica no disponible"
        elif not isinstance(cited, list) or not cited or any(not isinstance(ref, str) or ref not in allowed[rank] for ref in cited):
            reason = "referencias inválidas"
        else:
            seen.add(rank)
            valid.append({"rank": rank, "assessment": assessment, "explanation": explanation,
                          "cited_alert_ids": cited})
            continue
        rejected.append({"index": index, "reason": reason})
    return {"items": valid, "rejected": rejected}


def _text(value: Any, techniques: set, limit: int = 600) -> Optional[str]:
    """Reason a free-text field is not acceptable, or None."""
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        return "texto inválido"
    if INJECTION_PATTERN.search(value):
        return "texto no confiable"
    if _overclaims(value):
        return "conclusión no respaldada"
    if set(TECHNIQUE.findall(value)) - techniques:
        return "técnica no disponible"
    return None


def _refs_ok(refs: Any, allowed: set) -> bool:
    return isinstance(refs, list) and bool(refs) and all(isinstance(r, str) and r in allowed for r in refs)


def _initial_assessment(entry: Any, techniques: set, allowed: set, ranks: dict) -> Optional[str]:
    if not isinstance(entry, dict):
        return "salida no es objeto"
    gaps = entry.get("gaps")
    if not isinstance(gaps, list):
        return "gaps inválidos"
    if not _refs_ok(entry.get("cited_alert_ids"), allowed):
        return "referencias inválidas"
    return next(filter(None, (_text(t, techniques, 300) for t in [entry.get("assessment"), *gaps])), None)


def _evidence(entry: Any, techniques: set, allowed: set, ranks: dict) -> Optional[str]:
    if not isinstance(entry, dict):
        return "item no es objeto"
    rank = entry.get("rank")
    if type(rank) is not int or rank not in ranks:
        return "rango desconocido"
    sides = [entry.get("for"), entry.get("against")]
    if not all(isinstance(side, list) for side in sides) or not any(sides):
        return "evidencia inválida"
    for ref in sides[0] + sides[1]:
        if not isinstance(ref, dict) or not isinstance(ref.get("alert_id"), str) or ref["alert_id"] not in ranks[rank]:
            return "referencias inválidas"
        if not isinstance(ref.get("field"), str) or not ref["field"].strip():
            return "campo inválido"
        problem = _text(ref.get("observation"), techniques, 300)
        if problem:
            return problem
    return None


def _action(entry: Any, techniques: set, allowed: set, ranks: dict) -> Optional[str]:
    if not isinstance(entry, dict):
        return "item no es objeto"
    if not isinstance(entry.get("priority"), str) or entry["priority"] not in PRIORITIES:
        return "prioridad inválida"
    if not _refs_ok(entry.get("cited_alert_ids"), allowed):
        return "referencias inválidas"
    return _text(entry.get("action"), techniques, 300) or _text(entry.get("rationale"), techniques)


TASK_CHECKS = {"initial_assessment": _initial_assessment, "evidence": _evidence, "suggested_actions": _action}


def check_task_output(task: str, output: Any, context: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Valida la salida de una tarea del prompt: estructura, referencias y texto sin conclusiones no respaldadas."""
    if task == "hypotheses":
        return check_model_output(output, context)
    check = TASK_CHECKS.get(task)
    if check is None:
        return {"items": [], "rejected": [{"index": None, "reason": "tarea desconocida"}]}
    if task == "initial_assessment":
        entries = [output]
    elif isinstance(output, dict) and isinstance(output.get("items"), list):
        entries = output["items"]
    else:
        return {"items": [], "rejected": [{"index": None, "reason": "salida sin lista items"}]}
    ranks = {h.get("rank"): set(h.get("evidence_for_ids", [])) | set(h.get("evidence_against_ids", []))
             for h in context.get("hypotheses", []) if isinstance(h, dict)}
    allowed = {str(a.get("id")) for a in context.get("alerts", []) if isinstance(a, dict)}.union(*ranks.values())
    techniques = _techniques(context)
    valid, rejected, seen = [], [], set()
    for index, entry in enumerate(entries):
        rank = entry.get("rank") if isinstance(entry, dict) else None
        if task == "evidence" and type(rank) is int and rank in seen:
            reason = "rango duplicado"
        else:
            reason = check(entry, techniques, allowed, ranks)
        if reason:
            rejected.append({"index": index, "reason": reason})
            continue
        seen.add(rank)
        valid.append({key: entry[key] for key in TASK_KEYS[task]})
    return {"items": valid, "rejected": rejected}
