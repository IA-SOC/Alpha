"""Expose field paths and rule codes without echoing entire submitted payloads."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas.errors import CaseValidationError, ErrorResponse, ValidationIssue


def structural_rule(error: dict[str, Any]) -> str:
    path = list(error["loc"])[1:]
    kind = error["type"]
    if kind == "json_invalid":
        return "JSON"
    if kind == "extra_forbidden":
        return "CONTRACT"
    if not path:
        return "CONTRACT"
    if len(path) == 1:
        field = path[0]
        if field == "schema_version":
            return "VR-01" if kind == "missing" else "VR-02"
        if field == "alerts":
            return {"too_short": "VR-07", "too_long": "VR-08"}.get(kind, "VR-06")
        return {
            "case_id": "VR-03",
            "submitted_at": "VR-05",
            "enrichments": "VR-21",
        }.get(str(field), "CONTRACT")
    if path[0] == "alerts" and len(path) >= 3:
        field = path[2]
        if field == "source_system":
            return "VR-12" if kind == "missing" else "VR-13"
        if field == "raw_alert":
            return "VR-15" if kind == "missing" else "VR-16"
        return {
            "alert_id": "VR-09",
            "source_version": "VR-19",
            "ecs_version": "VR-20",
        }.get(str(field), "CONTRACT")
    if path[0] == "enrichments" and len(path) >= 3:
        if path[2] in ("provider", "observable"):
            return "VR-22"
    return "CONTRACT"


def structural_issues(errors: list[dict[str, Any]]) -> list[ValidationIssue]:
    """Remove optional-model union labels from public JSON field paths."""
    issues = []
    for error in errors:
        # Explicit null is already rejected by ContractModel's before validator.
        # The None union branch only adds duplicate, internal diagnostics.
        if error["type"] == "none_required":
            continue
        loc = list(error["loc"])
        branches = {"enrichments": "list[Enrichment]", "correlation": "Correlation"}
        if len(loc) > 2 and loc[2] == branches.get(loc[1]):
            del loc[2]
        issues.append(
            ValidationIssue(
                rule=structural_rule({**error, "loc": loc}),
                loc=loc,
                msg=error["msg"],
                type=error["type"],
            )
        )
    return issues


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def request_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        body = ErrorResponse(detail=structural_issues(exc.errors()))
        return JSONResponse(status_code=422, content=body.model_dump())

    @app.exception_handler(CaseValidationError)
    async def case_error(request: Request, exc: CaseValidationError) -> JSONResponse:
        body = ErrorResponse(detail=exc.issues)
        return JSONResponse(status_code=exc.status_code, content=body.model_dump())
