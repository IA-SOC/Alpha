"""MCP server para preparar y validar la segunda opinión del modelo."""
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.mcpserver import MCPServer
from core.llm_guard import build_model_context, check_model_output as validate_model_output
from core.llm_guard import check_task_output as validate_task_output

mcp = MCPServer("guard")


@mcp.tool()
def prepare_model_context(alerts: List[Dict[str, Any]], hypotheses: List[Dict[str, Any]],
                          correlation: Dict[str, Any] | None = None,
                          mappings: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    return build_model_context(alerts, hypotheses, correlation=correlation, mappings=mappings)


@mcp.tool()
def check_model_output(output: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return validate_model_output(output, context)


@mcp.tool()
def check_task_output(task: str, output: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return validate_task_output(task, output, context)


if __name__ == "__main__":
    mcp.run()
