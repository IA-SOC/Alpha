"""Shared error shape for Pydantic and service validation failures."""

from pydantic import BaseModel


class ValidationIssue(BaseModel):
    rule: str
    loc: list[str | int]
    msg: str
    type: str


class ErrorResponse(BaseModel):
    detail: list[ValidationIssue]


class CaseValidationError(Exception):
    def __init__(self, issues: list[ValidationIssue], status_code: int = 422) -> None:
        super().__init__("Case validation failed")
        self.issues = issues
        self.status_code = status_code
