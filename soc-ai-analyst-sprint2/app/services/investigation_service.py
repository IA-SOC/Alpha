"""Use the existing LangGraph/MCP workflow in the same FastAPI process."""

import asyncio
from uuid import UUID, uuid4

from agent.graph import build_graph, investigate, submit_review
from app.schemas.investigation import ReviewDecision
from app.services.agent_adapter import adapt_case
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
