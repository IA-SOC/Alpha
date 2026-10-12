"""
MCP server — capa de negocio: mapeo de alertas a técnicas MITRE ATT&CK.

Correr standalone (para debug):
    python servers/mitre_server.py
El orquestador lo levanta como subproceso vía stdio, no hace falta correrlo
a mano en uso normal.
"""
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP
from core.logic import map_alerts_to_mitre

mcp = FastMCP("mitre-mapper")


@mcp.tool()
def map_to_mitre(alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Mapea una lista de alertas a técnicas MITRE ATT&CK candidatas.

    Args:
        alerts: lista de alertas del caso (cada una con al menos id, rule_name, tags).

    Returns:
        Lista de técnicas detectadas, cada una con technique_id, technique_name,
        tactic, supporting_alert_ids y confidence. Ordenada por confianza descendente.
    """
    return map_alerts_to_mitre(alerts)


if __name__ == "__main__":
    mcp.run()
