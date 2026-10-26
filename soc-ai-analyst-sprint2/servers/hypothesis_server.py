"""
MCP server — capa de negocio: generación de hipótesis de ataque.
"""
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.mcpserver import MCPServer
from core.logic import generate_hypothesis

mcp = MCPServer("hypothesis-generator")


@mcp.tool()
def generate_attack_hypothesis(mitre_mappings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Genera la hipótesis de ataque principal a partir de las técnicas MITRE detectadas.

    Args:
        mitre_mappings: salida de la herramienta map_to_mitre.

    Returns:
        Dict con summary (narrativa), confidence (0-1), mitre_techniques
        (ordenadas según la kill chain) y evidence_alert_ids.
    """
    return generate_hypothesis(mitre_mappings)


if __name__ == "__main__":
    mcp.run()
