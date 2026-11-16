
import asyncio
import json
from datetime import datetime, timezone
from uuid import UUID

from agent.llm import get_provider, review_timeout_seconds
from app.schemas.chat import AnalystMessage, AssistantAnswer
from core.llm_guard import _safe


class InvalidModelAnswer(Exception):
    pass


class ChatService:
    def __init__(self, investigation_service):
        self.investigations = investigation_service
        self.store = investigation_service.store

    def evidence(self, case_id: UUID) -> dict:
        accepted = self.store.get_by_id(case_id)
        if accepted is None:
            raise KeyError("Case not found")
        saved = self.store.get_investigation(case_id)
        if saved is None:
            raise LookupError("Wait for an investigation before sending messages")
        evidence = {
            f"alert:{alert.alert_id}": {
                "source": "submitted_case",
                "alert_id": alert.alert_id,
                "data": alert.model_dump(exclude_unset=True),
            }
            for alert in accepted.submitted_case.alerts
        }
        report = saved["report"]
        for section in ("hypotheses", "timeline", "attack_mapping"):
            for index, item in enumerate(report.get(section, [])):
                evidence[f"mcp:{saved['run_id']}:{section}:{index}"] = {
                    "source": "investigation",
                    "section": section,
                    "data": item,
                }
        enrichment = report.get("enrichment", {})
        for index, item in enumerate(enrichment.get("items", [])):
            evidence[f"mcp:{saved['run_id']}:ioc:{index}"] = {
                "source": "investigation",
                "section": "ioc",
                "data": item,
            }
        return evidence

    async def send(self, case_id: UUID, request: AnalystMessage) -> dict:
        async with self.investigations.locks.setdefault(str(case_id), asyncio.Lock()):
            catalog = await asyncio.to_thread(self.evidence, case_id)
            unknown = set(request.evidence_refs) - catalog.keys()
            if unknown:
                raise ValueError(
                    "Evidence references do not belong to this investigation"
                )
            history = await asyncio.to_thread(self.store.messages, case_id)
            default_refs = [ref for ref in catalog if ref.startswith("alert:")][:20] + [
                ref for ref in catalog if ref.startswith("mcp:")
            ][:10]
            previous_refs = list(
                dict.fromkeys(
                    ref
                    for message in history[-20:]
                    for ref in message.get("evidence_refs", [])
                    if ref in catalog
                )
            )[-20:]
            refs = list(
                dict.fromkeys(
                    [
                        *request.evidence_refs,
                        *previous_refs,
                        *default_refs,
                    ]
                )
            )
            stats = {"redacted_fields": 0}
            evidence = {ref: _safe(catalog[ref], 1000, stats) for ref in refs}
            saved = await asyncio.to_thread(self.store.get_investigation, case_id)
            accepted = await asyncio.to_thread(self.store.get_by_id, case_id)
            case_context = _safe(
                {
                    "title": accepted.submitted_case.title,
                    "description": accepted.submitted_case.description,
                    "executive_summary": saved["report"].get("executive_summary"),
                    "limitations": saved["report"].get("limitations", []),
                    "review": saved["report"].get("review"),
                },
                2000,
                stats,
            )
            context = {
                "case_context": case_context,
                "case_id": str(case_id),
                "messages": history[-20:],
                "current_message": request.message,
                "requested_evidence_refs": request.evidence_refs,
                "evidence": evidence,
                "limitations": [
                    "Only the last 20 messages and selected evidence are sent."
                ],
            }
            if len(json.dumps(context, ensure_ascii=False)) > 150000:
                raise ValueError("Context too large; select fewer evidence references")
            provider = get_provider("gemini")
            raw = await asyncio.wait_for(
                asyncio.to_thread(provider.chat, context),
                # Margin so the provider's own deadline fires first.
                timeout=review_timeout_seconds() + 5,
            )
            try:
                answer = AssistantAnswer.model_validate(raw)
            except Exception as exc:
                raise InvalidModelAnswer("Invalid Gemini response") from exc
            if set(answer.evidence_refs) - evidence.keys():
                raise InvalidModelAnswer("Gemini cited evidence outside its context")
            now = datetime.now(timezone.utc).isoformat()
            user = {
                "role": "user",
                "analyst_id": request.analyst_id,
                "content": request.message,
                "evidence_refs": request.evidence_refs,
                "created_at": now,
            }
            assistant = {
                "role": "assistant",
                "content": answer.answer,
                "evidence_refs": answer.evidence_refs,
                "created_at": now,
            }
            await asyncio.to_thread(
                self.store.append_exchange, case_id, user, assistant
            )
            return {"case_id": str(case_id), "message": assistant}
