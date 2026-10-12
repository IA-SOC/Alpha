"""
Orquestador (MCP Host/Client).

Recibe un caso, levanta los 4 MCP servers de la capa de negocio como
subprocesos (transporte stdio), y encadena las llamadas:

    map_to_mitre → build_case_timeline → generate_attack_hypothesis → build_incident_report

Este es el único componente que conoce el orden del pipeline. Cada server
es independiente y no sabe nada de los demás — así se puede reemplazar,
testear o escalar cada uno por separado.

Uso:
    python orchestrator/client.py data/sample_case_bruteforce.json
"""
import asyncio
import json
import sys
from pathlib import Path
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent
SERVERS = {
    "mitre": ROOT / "servers" / "mitre_server.py",
    "timeline": ROOT / "servers" / "timeline_server.py",
    "hypothesis": ROOT / "servers" / "hypothesis_server.py",
    "report": ROOT / "servers" / "report_server.py",
}


class McpToolClient:
    """Envoltorio delgado: abre una sesión MCP contra un server y llama una tool."""

    def __init__(self, script_path: Path):
        self.params = StdioServerParameters(command=sys.executable, args=[str(script_path)])

    async def call(self, stack: AsyncExitStack, tool_name: str, arguments: dict):
        read, write = await stack.enter_async_context(stdio_client(self.params))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        result = await session.call_tool(tool_name, arguments)
        if result.isError:
            error_text = "; ".join(c.text for c in result.content if hasattr(c, "text"))
            raise RuntimeError(f"MCP tool '{tool_name}' failed: {error_text}")
        # FastMCP serializa el valor de retorno estructurado en structuredContent;
        # es más confiable que reconstruirlo desde los bloques de texto (que
        # FastMCP puede partir en un TextContent por elemento si la tool
        # devuelve una lista).
        structured = result.structuredContent
        if structured is not None and "result" in structured:
            return structured["result"]
        if structured is not None:
            return structured
        # Fallback: un solo bloque de texto con el JSON completo.
        return json.loads(result.content[0].text)


async def investigate(case: dict) -> dict:
    async with AsyncExitStack() as stack:
        mitre_client = McpToolClient(SERVERS["mitre"])
        timeline_client = McpToolClient(SERVERS["timeline"])
        hypothesis_client = McpToolClient(SERVERS["hypothesis"])
        report_client = McpToolClient(SERVERS["report"])

        mitre_mappings = await mitre_client.call(
            stack, "map_to_mitre", {"alerts": case["alerts"]}
        )
        timeline = await timeline_client.call(
            stack, "build_case_timeline",
            {"alerts": case["alerts"], "mitre_mappings": mitre_mappings},
        )
        hypothesis = await hypothesis_client.call(
            stack, "generate_attack_hypothesis", {"mitre_mappings": mitre_mappings}
        )
        report = await report_client.call(
            stack, "build_incident_report",
            {"case": case, "timeline": timeline, "hypothesis": hypothesis},
        )
        return report


def load_case(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    case_path = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "data" / "sample_case_bruteforce.json")
    case = load_case(case_path)
    result = asyncio.run(investigate(case))
    print(json.dumps(result, indent=2, ensure_ascii=False))
