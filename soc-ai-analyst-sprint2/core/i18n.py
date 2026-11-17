"""Language of the text the agent generates itself (REPORT_LANGUAGE=en|es, default es).

Protocol values (confidence levels, statuses, roles) are not translated: the frontend does that.
shortcut: one process-wide language; a per-request language is #187.
"""
import os


def language() -> str:
    value = os.getenv("REPORT_LANGUAGE", "es").strip().lower()
    return value if value in ("en", "es") else "es"


def tr(es: str, en: str) -> str:
    """The Spanish text by default, the English one when REPORT_LANGUAGE=en."""
    return en if language() == "en" else es
