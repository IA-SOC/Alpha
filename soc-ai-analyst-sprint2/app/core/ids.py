"""Accepted-case identifiers, separate from submitted and native alert IDs."""

from uuid import UUID, uuid4


def generate_case_id() -> UUID:
    """Generate a UUID4 only when called after successful validation."""
    return uuid4()
