"""MCP server de solo lectura: IoC pre-enriquecidos y casos anonimizados almacenados."""
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mcp.server.mcpserver import MCPServer
from core import context_store

DB_PATH = Path(os.getenv("CONTEXT_DB_PATH") or ROOT / "data" / "context" / "context.sqlite3")

mcp = MCPServer("context")


@mcp.tool()
def lookup_iocs(value: str, observable_type: Optional[str] = None) -> Dict[str, Any]:
    """IoC almacenados para un observable, con proveedor, veredicto crudo y origen."""
    return context_store.lookup_iocs(DB_PATH, value, observable_type)


@mcp.tool()
def lookup_case(case_id: str) -> Dict[str, Any]:
    """Metadatos anonimizados de un caso almacenado y sus IoC vinculados."""
    return context_store.lookup_case(DB_PATH, case_id)


if __name__ == "__main__":
    mcp.run()
