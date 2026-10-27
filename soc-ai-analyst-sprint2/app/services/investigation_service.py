"""Use the existing LangGraph/MCP workflow in the same FastAPI process."""

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from uuid import UUID, uuid4

from agent.graph import build_graph, investigate, submit_review
from agent.render import render_markdown
from app.schemas.investigation import ReviewDecision
from app.services.agent_adapter import adapt_case
from app.services.finding_review import validate_finding_decisions
from app.services.report_formatter import format_report
from app.services.traceability import verify_traceability
from app.storage.case_store import CaseStore


class InvestigationService:
    def __init__(self, store: CaseStore, window_seconds: int = 300) -> None:
        self.store = store
        self.window_seconds = window_seconds
        self.sessions: dict[str, tuple] = {}
        self.locks: dict[str, asyncio.Lock] = {}

    def context(self, case_id: UUID) -> dict:
        accepted = self.store.get_by_id(case_id)
        if accepted is None:
            raise KeyError("Case not found")
        return adapt_case(accepted, self.window_seconds)

    def _result(self, case_id, run_id, state):
        if not state["validation"]["ok"]:
            raise ValueError("Agent report validation failed")
        context = state["case"]["investigation_context"]
        verify_traceability(context, state["report"])
        review = state["report"]["review"]["status"]
        return {
            "case_id": str(case_id),
            "run_id": run_id,
            "status": "pending_review" if review == "pending" else review,
            "correlation": context["correlation"],
            "investigation_context": context,
            "report": state["report"],
            "report_markdown": state["report_markdown"],
            "validation": {**state["validation"], "traceability_ok": True},
            "audit_log": state["audit_log"],
        }

    async def run(self, case_id: UUID) -> dict:
        async with self.locks.setdefault(str(case_id), asyncio.Lock()):
            adapted = await asyncio.to_thread(self.context, case_id)
            graph, run_id = build_graph(), str(uuid4())
            state = await asyncio.wait_for(
                investigate(adapted, thread_id=run_id, app=graph),
                timeout=300,
            )
            result = self._result(case_id, run_id, state)
            await asyncio.to_thread(self.store.save_investigation, case_id, result)
            self.sessions[str(case_id)] = (graph, run_id)
            return result

    async def review(self, case_id: UUID, decision: ReviewDecision) -> dict:
        async with self.locks.setdefault(str(case_id), asyncio.Lock()):
            if decision.run_id is not None or decision.findings:
                return await self._review_findings(case_id, decision)
            session = self.sessions.get(str(case_id))
            if session is None:
                raise LookupError("No resumable investigation in this process")
            graph, run_id = session
            snapshot = graph.get_state({"configurable": {"thread_id": run_id}})
            if snapshot.next != ("revision_humana",):
                raise LookupError("The investigation is not awaiting review")
            state = await submit_review(graph, run_id, decision.model_dump())
            result = self._result(case_id, run_id, state)
            await asyncio.to_thread(self.store.save_investigation, case_id, result)
            return result

    async def _review_findings(self, case_id: UUID, decision: ReviewDecision) -> dict:
        saved = await asyncio.to_thread(self.store.get_investigation, case_id)
        if saved is None:
            raise LookupError("No completed investigation found")
        if saved["run_id"] != decision.run_id:
            raise LookupError("The investigation run has changed; reload")
        if saved["report"]["review"]["status"] != "pending":
            raise LookupError("The investigation is not awaiting review")
        validate_finding_decisions(saved["report"], decision)
        result = deepcopy(saved)
        now = datetime.now(timezone.utc).isoformat()
        result["report"]["review"] = {
            "status": decision.status,
            "analyst": decision.analyst,
            "notes": decision.notes,
            "reviewed_at": now,
            "run_id": decision.run_id,
            "findings": [item.model_dump() for item in decision.findings],
        }
        result["status"] = decision.status
        result["report"]["audience_sections"] = format_report(result["report"])
        result["report_markdown"] = render_markdown(result["report"])
        verify_traceability(result["investigation_context"], result["report"])
        result["audit_log"].append(
            {
                "phase": 6,
                "node": "revision_humana",
                "finished_at": now,
                "duration_ms": 0,
                "detail": "Structured per-finding analyst review",
            }
        )
        await asyncio.to_thread(
            self.store.save_review, case_id, decision.run_id, result
        )
        self.sessions.pop(str(case_id), None)
        return result
