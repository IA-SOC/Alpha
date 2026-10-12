"""
MCP server — capa de negocio: reconstrucción de línea de tiempo del ataque.
"""
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP
from core.logic import build_timeline

mcp = FastMCP("timeline-builder")


@mcp.tool()
def build_case_timeline(alerts: List[Dict[str, Any]],
                         mitre_mappings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Construye la línea de tiempo cronológica del caso.

    Args:
        alerts: lista de alertas del caso.
        mitre_mappings: salida de la herramienta map_to_mitre, usada para
            clasificar cada evento en una etapa del ataque.

    Returns:
        Lista de eventos ordenados cronológicamente, cada uno con alert_id,
        timestamp, description y stage (initial_access | progression | impact).
    """
    return build_timeline(alerts, mitre_mappings)


if __name__ == "__main__":
    mcp.run()
