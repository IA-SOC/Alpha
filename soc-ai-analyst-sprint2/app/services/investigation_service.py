"""Use the existing LangGraph/MCP workflow in the same FastAPI process."""

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from uuid import UUID, uuid4

from agent.graph import build_graph, investigate, submit_review
from agent.llm import ProviderUnavailable
from agent.render import render_markdown
from app.schemas.investigation import AnalystInstruction, ReviewDecision
from app.services.agent_adapter import adapt_case
from app.services.finding_review import validate_finding_decisions
from app.services.report_formatter import format_report
from app.services.traceability import verify_traceability
from app.storage.case_store import CaseStore


class InvestigationService:
    def __init__(self, store: CaseStore, window_seconds: int = 300) -> None:
        self.require_gemini = True
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
            "revision": 1,
            "status": "pending_review" if review == "pending" else review,
            "correlation": context["correlation"],
            "investigation_context": context,
            "report": state["report"],
            "report_markdown": state["report_markdown"],
            "validation": {**state["validation"], "traceability_ok": True},
            "audit_log": state["audit_log"],
        }

    async def run(
        self,
        case_id: UUID,
        guidance: dict | None = None,
        *,
        force: bool = True,
        require_gemini: bool = False,
        queued_only: bool = False,
    ) -> dict | None:
        async with self.locks.setdefault(str(case_id), asyncio.Lock()):
            if queued_only:
                job = await asyncio.to_thread(self.store.analysis_status, case_id)
                if job is None or job["status"] != "queued":
                    return None
            saved = await asyncio.to_thread(self.store.get_investigation, case_id)
            if not force:
                status = await asyncio.to_thread(self.store.analysis_status, case_id)
                if saved is not None and status:
                    if status["status"] == "completed":
                        return saved
                    if (
                        status["status"] == "error"
                        and status["error"] == "ProviderUnavailable"
                    ):
                        # Older runs saved the report before marking the job failed.
                        await asyncio.to_thread(
                            self.store.set_analysis_status, case_id, "completed"
                        )
                        return saved
                if status and status["status"] == "error":
                    raise ProviderUnavailable(
                        "Previous analysis failed; use force=true to retry"
                    )
            await asyncio.to_thread(self.store.set_analysis_status, case_id, "running")
            try:
                adapted = await asyncio.to_thread(self.context, case_id)
                adapted["require_gemini"] = require_gemini
                if guidance is not None:
                    adapted["analyst_guidance"] = deepcopy(guidance)
                graph, run_id = build_graph(), str(uuid4())
                state = await asyncio.wait_for(
                    investigate(adapted, thread_id=run_id, app=graph),
                    timeout=300,
                )
                result = self._result(case_id, run_id, state)
                if saved is not None:
                    result["revision"] = int(saved.get("revision", 1)) + 1
                    result["instruction_history"] = saved.get("instruction_history", [])
                await asyncio.to_thread(
                    self.store.save_investigation,
                    case_id,
                    result,
                    complete_analysis=True,
                )
                self.sessions[str(case_id)] = (graph, run_id)
                return result
            except asyncio.CancelledError:
                await asyncio.to_thread(
                    self.store.set_analysis_status, case_id, "queued"
                )
                raise
            except Exception as exc:
                await asyncio.to_thread(
                    self.store.set_analysis_status, case_id, "error", type(exc).__name__
                )
                raise

    async def worker(self) -> None:
        while True:
            case_id = await asyncio.to_thread(self.store.next_job)
            if case_id is None:
                await asyncio.sleep(0.25)
                continue
            try:
                await self.run(
                    case_id, force=False, require_gemini=True, queued_only=True
                )
            except Exception:
                pass

    async def instruct(self, case_id: UUID, instruction: AnalystInstruction) -> dict:
        async with self.locks.setdefault(str(case_id), asyncio.Lock()):
            saved = await asyncio.to_thread(self.store.get_investigation, case_id)
            if saved is None:
                raise LookupError("No completed investigation found")
            current_revision = int(saved.get("revision", 1))
            if instruction.revision != current_revision:
                raise LookupError("The investigation revision has changed; reload")
            guidance = instruction.model_dump(exclude={"revision"})
            result = await self._run_unlocked(case_id, guidance)
            result["revision"] = current_revision + 1
            result["instruction_history"] = [
                *saved.get("instruction_history", []),
                {
                    **guidance,
                    "revision": result["revision"],
                    "run_id": result["run_id"],
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                },
            ]
            await asyncio.to_thread(
                self.store.save_instruction_revision,
                case_id,
                current_revision,
                result,
            )
            return result

    async def _run_unlocked(self, case_id: UUID, guidance: dict) -> dict:
        adapted = await asyncio.to_thread(self.context, case_id)
        adapted["analyst_guidance"] = deepcopy(guidance)
        graph, run_id = build_graph(), str(uuid4())
        state = await asyncio.wait_for(
            investigate(adapted, thread_id=run_id, app=graph),
            timeout=self.window_seconds,
        )
        result = self._result(case_id, run_id, state)
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
            saved = await asyncio.to_thread(self.store.get_investigation, case_id)
            if saved is not None:
                result["revision"] = int(saved.get("revision", 1))
                result["instruction_history"] = saved.get("instruction_history", [])
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
        result["revision"] = int(saved.get("revision", 1))
        result["instruction_history"] = saved.get("instruction_history", [])
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
