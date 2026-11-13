"""Plantillas de prompt versionadas de la skill soc-case-investigator."""
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

PROMPT_FILE = Path(__file__).with_name("soc_investigation_v1.json")


@lru_cache(maxsize=1)
def load_prompts() -> Dict[str, Any]:
    return json.loads(PROMPT_FILE.read_text(encoding="utf-8"))


def prompt_version() -> str:
    return load_prompts()["version"]


def system_instruction(task: str) -> str:
    """Instrucción de sistema para una tarea; KeyError si la tarea no existe."""
    return load_prompts()["tasks"][task]["instruction"]


def output_shape(task: str) -> Dict[str, Any]:
    """Forma de salida esperada de la tarea (documentada para la validación #153)."""
    return load_prompts()["tasks"][task].get("output", {})
