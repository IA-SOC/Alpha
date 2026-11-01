"""Integrated pipeline endpoints, addressed by the generated application UUID."""

import json
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response

from app.schemas.investigation import AnalystInstruction, ReviewDecision
from app.services.investigation_service import InvestigationService

router = APIRouter(prefix="/api/v1/cases", tags=["investigations"])
logger = logging.getLogger(__name__)


def get_service(request: Request) -> InvestigationService:
    return request.app.state.investigation_service


Service = Annotated[InvestigationService, Depends(get_service)]


@router.get("/{case_id}")
def read_case(case_id: UUID, service: Service):
    accepted = service.store.get_by_id(case_id)
    if accepted is None:
        raise HTTPException(404, "Case not found")
    return {
        "case_id": str(case_id),
        "submitted_case": accepted.submitted_case.model_dump(exclude_unset=True),
    }


@router.get("/{case_id}/context")
def read_context(case_id: UUID, service: Service):
    try:
        return service.context(case_id)["investigation_context"]
    except KeyError as exc:
        raise HTTPException(404, "Case not found") from exc


@router.post("/{case_id}/investigate")
async def investigate_case(case_id: UUID, service: Service):
    if service.store.get_by_id(case_id) is None:
        raise HTTPException(404, "Case not found")
    try:
        return await service.run(case_id)
    except TimeoutError as exc:
        raise HTTPException(
            504, "Investigation exceeded the 300-second timeout"
        ) from exc
    except Exception as exc:
        logger.error("Investigation failed for %s (%s)", case_id, type(exc).__name__)
        raise HTTPException(
            502, "Investigation failed; accepted evidence is retained"
        ) from exc


@router.get("/{case_id}/investigation")
def read_investigation(case_id: UUID, service: Service):
    result = service.store.get_investigation(case_id)
    if result is None:
        raise HTTPException(404, "No completed investigation found")
    return result


@router.get("/{case_id}/report")
def read_report(case_id: UUID, service: Service):
    result = service.store.get_investigation(case_id)
    if result is None:
        raise HTTPException(404, "No completed investigation found")
    return {
        "case_id": result["case_id"],
        "report": result["report"],
        "audience_sections": result["report"]["audience_sections"],
        "report_markdown": result["report_markdown"],
    }


@router.post("/{case_id}/instructions")
async def submit_instruction(
    case_id: UUID,
    instruction: AnalystInstruction,
    service: Service,
    analyst_header: Annotated[str, Header(alias="X-Analyst-Id")],
):
    if service.store.get_by_id(case_id) is None:
        raise HTTPException(404, "Case not found")
    if analyst_header != instruction.analyst_id:
        raise HTTPException(403, "X-Analyst-Id does not match analyst_id")
    try:
        result = await service.instruct(case_id, instruction)
        return {key: value for key, value in result.items() if key != "_graph"}
    except LookupError as exc:
        raise HTTPException(409, str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(504, "Follow-up investigation timed out") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/{case_id}/review")
async def review_case(case_id: UUID, decision: ReviewDecision, service: Service):
    if service.store.get_by_id(case_id) is None:
        raise HTTPException(404, "Case not found")
    try:
        return await service.review(case_id, decision)
    except LookupError as exc:
        raise HTTPException(409, str(exc)) from exc

    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/{case_id}/export")
def export_investigation(case_id: UUID, service: Service):
    result = service.store.get_investigation(case_id)
    if result is None:
        raise HTTPException(404, "No completed investigation found")
    return Response(
        content=json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": (
                f'attachment; filename="investigation-{case_id}.json"'
            )
        },
    )
