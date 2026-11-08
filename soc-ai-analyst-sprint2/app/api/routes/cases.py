"""The single intake boundary for the monolithic backend."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.schemas.case import (
    AcceptedCaseResponse,
    CaseListItem,
    CaseStatusUpdate,
    IncidentCase,
    InvestigationSummary,
)
from app.schemas.errors import ErrorResponse
from app.services.case_service import CaseService

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


def get_case_service(request: Request) -> CaseService:
    return request.app.state.case_service


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=AcceptedCaseResponse,
    responses={409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Validate and accept an incident case",
)
def submit_case(
    case: IncidentCase,
    service: Annotated[CaseService, Depends(get_case_service)],
) -> AcceptedCaseResponse:
    accepted = service.accept(case)
    return AcceptedCaseResponse(
        case_id=accepted.case_id,
        submitted_case_id=accepted.submitted_case.case_id,
    )


@router.get("", response_model=list[CaseListItem], summary="List stored cases")
def list_cases(
    service: Annotated[CaseService, Depends(get_case_service)],
) -> list[CaseListItem]:
    return [
        CaseListItem(
            case_id=case.case_id,
            submitted_case_id=case.submitted_case_id,
            status=case.status,
            created_at=case.created_at,
            investigation=(
                InvestigationSummary(
                    status=case.investigation["status"],
                    revision=int(case.investigation.get("revision", 1)),
                    run_id=case.investigation["run_id"],
                    review_status=case.investigation["report"]["review"]["status"],
                )
                if case.investigation
                else None
            ),
        )
        for case in service.list_cases()
    ]


@router.patch(
    "/{case_id}",
    response_model=CaseListItem,
    responses={404: {"model": ErrorResponse}},
    summary="Open or close a case",
)
def update_case_status(
    case_id: UUID,
    update: CaseStatusUpdate,
    service: Annotated[CaseService, Depends(get_case_service)],
) -> CaseListItem:
    if not service.update_status(case_id, update.status):
        raise HTTPException(status_code=404, detail="Case not found")
    case = next(item for item in service.list_cases() if item.case_id == case_id)
    investigation = case.investigation
    return CaseListItem(
        case_id=case.case_id,
        submitted_case_id=case.submitted_case_id,
        status=case.status,
        created_at=case.created_at,
        investigation=(
            InvestigationSummary(
                status=investigation["status"],
                revision=int(investigation.get("revision", 1)),
                run_id=investigation["run_id"],
                review_status=investigation["report"]["review"]["status"],
            )
            if investigation
            else None
        ),
    )
