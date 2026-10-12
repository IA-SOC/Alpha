"""
MCP server — capa de negocio: ensamblaje del reporte de incidente final.
"""
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP
from core.logic import generate_report

mcp = FastMCP("report-generator")


@mcp.tool()
def build_incident_report(case: Dict[str, Any], timeline: List[Dict[str, Any]],
                           hypothesis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensambla el reporte final de incidente (case_summary, timeline, hypothesis,
    blast_radius, recommended_actions), listo para la capa de presentación o
    para exportar a un sistema tipo TheHive.

    Args:
        case: el caso original ({"case_id": ..., "alerts": [...]})
        timeline: salida de build_case_timeline.
        hypothesis: salida de generate_attack_hypothesis.
    """
    return generate_report(case, timeline, hypothesis)


if __name__ == "__main__":
    mcp.run()
