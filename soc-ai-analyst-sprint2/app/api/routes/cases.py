"""The single intake boundary for the monolithic backend."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.schemas.case import AcceptedCaseResponse, IncidentCase
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
