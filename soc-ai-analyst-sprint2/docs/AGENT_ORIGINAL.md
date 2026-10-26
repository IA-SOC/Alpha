# SOC AI Analyst — agente investigador de casos SOC

Agente que investiga un caso de alertas de seguridad (Elastic ECS o Wazuh),
propone hipótesis MITRE ATT&CK con evidencia citada, reconstruye la
cronología y el alcance, y entrega un reporte para que un analista lo valide,
corrija o rechace. No ejecuta acciones de respuesta ni cierra casos.

Es un prototipo académico que trabaja **solo con datos simulados**.

- El workflow está hecho en **LangGraph** y sigue las seis fases de la skill
  [`soc-case-investigator`](skills/soc-case-investigator/SKILL.md).
- El análisis corre en cuatro **MCP servers** independientes sobre
  `core/logic.py`.

> **Estado.** El motor de análisis usa reglas deterministas, sin LLM: el mismo
> caso produce siempre el mismo reporte, y solo reconoce las señales que su
> catálogo nombra. En el caso de control `data/holdout/` (Kerberoasting, RDP y
> exfiltración con rclone) no detecta ninguna técnica. Ver
> [Limitaciones](#limitaciones).

## Inicio rápido

Requiere Python 3.12 o superior.

```bash
python -m venv venv
source venv/bin/activate            # Windows (PowerShell): venv\Scripts\Activate.ps1
pip install -r requirements.txt

python agent/graph.py data/synthetic/phishing_ecs.json   # investiga un caso e imprime el borrador
python -m pytest tests -q                                  # pruebas del agente
```

Cada caso tarda unos 7 segundos; casi todo es el arranque de los MCP servers.

## Cómo funciona

```
recibir_validar → investigar_hipotesis → cronologia_alcance
    → consumir_ioc → generar_validar_reporte → revision_humana (pausa)
```

| Fase | Qué hace | Dónde |
| --- | --- | --- |
| 1. Recibir y validar | Detecta ECS, Elastic Security, Wazuh o el formato interno. Normaliza timestamps a UTC conservando el original. Registra campos faltantes y texto con forma de instrucción, que se trata como dato. | `agent/normalize.py` |
| 2. Investigar hipótesis | Llama a `map_to_mitre` y `generate_attack_hypothesis`. Ordena hipótesis con confianza ordinal (alta, media, baja o insuficiente) y evidencia a favor y en contra. | MCP + `agent/investigation.py` |
| 3. Cronología y alcance | Llama a `build_case_timeline`. Separa activos observados de sospechosos; nunca marca activos como confirmados. | MCP + `agent/investigation.py` |
| 4. Consumir IoC | Usa solo el enriquecimiento adjunto al caso, cruzado por valor exacto. No consulta servicios externos. | `agent/investigation.py` |
| 5. Generar y validar | Arma el reporte JSON (esquema 1.1 de la skill) y el borrador Markdown. Ejecuta el validador de la skill; si falla, el grafo termina sin pasar a revisión. | `agent/graph.py`, `agent/render.py` |
| 6. Revisión humana | Pausa con `interrupt()`. El reporte queda en `pending` hasta que llega la decisión del analista (`submit_review`). | `agent/graph.py` |

Cada fase agrega una entrada a `audit_log` con su hora y duración. El estado
se guarda por `thread_id` en un checkpointer, hoy en memoria.

### Uso desde Python

```python
import asyncio, json
from agent.graph import build_graph, investigate, submit_review

app = build_graph()
case = json.load(open("data/synthetic/bruteforce_wazuh.json", encoding="utf-8"))

state = asyncio.run(investigate(case, thread_id="caso-1", app=app))   # fases 1–5
print(state["report_markdown"])                                       # borrador en pending

state = asyncio.run(submit_review(app, "caso-1", {"status": "validated", "analyst": "analista-l2"}))
```

La decisión acepta `validated`, `corrected` o `rejected`.

### Formato de un caso

```json
{
  "case_id": "SYN-PHISH-001",
  "synthetic": true,
  "alerts": [ { "...": "alertas ECS, Wazuh o formato interno" } ],
  "enrichment": [ { "indicator": "198.51.100.23", "type": "ip", "verdict": "malicious", "source": "feed" } ]
}
```

`enrichment` es opcional. Ejemplos completos en `data/synthetic/`.

## Casos de prueba

| Archivo | Escenario | Formato |
| --- | --- | --- |
| `data/synthetic/phishing_ecs.json` | Phishing con robo de credenciales; texto hostil en el asunto | Elastic ECS |
| `data/synthetic/bruteforce_wazuh.json` | Fuerza bruta SSH y un respaldo legítimo que la vuelve ambigua | Wazuh |
| `data/synthetic/exfiltration.json` | Exfiltración desde servidor de archivos | Interno |
| `data/synthetic/pre_ransomware.json` | SMB, borrado de shadow copies y cifrado | Interno |
| `data/synthetic/benign_noise.json` | Ruido benigno con timestamps defectuosos | Interno |
| `data/sample_case_bruteforce.json` | Caso original del scaffold | Interno |
| `data/holdout/kerberoast_rdp_rclone_ecs.json` | Caso de control, no usado para ajustar reglas | Elastic ECS |

Los casos de `data/synthetic/` se diseñaron junto con las reglas del
catálogo, así que miden comportamiento, no capacidad de detección.

```bash
python agent/run_synthetic.py      # regenera data/reportes_sinteticos/ (JSON + Markdown)
python demo/build_demo.py          # regenera demo/soc-demo.html con esos reportes
```

`demo/soc-demo.html` es una página autocontenida para mostrar los reportes
al equipo; se abre directo en el navegador.

## Estructura

```
├── agent/                       # Workflow LangGraph: graph, normalize, investigation, render
├── core/logic.py                # Reglas y lógica de negocio pura (sin protocolo MCP)
├── servers/                     # MCP servers: mitre, timeline, hypothesis, report
├── orchestrator/client.py       # Orquestador MCP original (sin LangGraph)
├── skills/soc-case-investigator/# Skill V3: SKILL.md, protocolo, esquema 1.1, plantilla, validador
├── data/                        # Casos sintéticos, caso de control y reportes generados
├── demo/                        # Generador de la página de demo
└── tests/                       # Pruebas del agente sobre los casos sintéticos
```

El orquestador original sigue funcionando por separado:
`python orchestrator/client.py data/sample_case_bruteforce.json`.

## Limitaciones

- **Cobertura del catálogo.** `core/logic.py` tiene cinco reglas por palabra
  clave. No cubre, entre otros, el login exitoso tras una fuerza bruta,
  `sudo` a root, reglas de reenvío de correo, Kerberoasting ni exfiltración a
  la nube. El borrado de shadow copies se asigna a T1486 y no a T1490.
- **Sin medición de precisión.** Las pruebas verifican el procedimiento y el
  formato. Medir precisión requiere casos etiquetados por analistas.
- **Estado en memoria.** Un caso pendiente de revisión se pierde si el proceso
  se reinicia.
- **Latencia.** No se probó un caso de 50 alertas; el requisito es 5 minutos.
- **Ruta del validador en la skill.** `SKILL.md` indica una ruta fija
  `/home/ubuntu/...`; el agente usa la ruta del repositorio.

## Próximos pasos

1. Ampliar el catálogo de `core/logic.py` con la guía MITRE del cliente y
   correlaciones de secuencia (fallos seguidos de éxito).
2. Armar un conjunto de casos etiquetados por analistas y medir precisión.
3. Usar un checkpointer persistente (SQLite o Postgres) y mantener abiertas
   las sesiones MCP durante todo el caso.
4. Agregar un nodo con LLM en la fase 2, detrás del mismo validador.
5. Exponer `investigate` y `submit_review` en una API para la interfaz del
   analista.

## Notas técnicas

- **Transporte MCP:** stdio; cada servidor corre como subproceso. Se puede
  migrar a HTTP/SSE sin tocar `core/logic.py`.
- **Versión del SDK:** `mcp` 2.x (API `MCPServer`, antes `FastMCP` en la v1).
- **Resultado estructurado:** se lee `result.structured_content`, porque
  MCPServer puede partir una lista de retorno en varios bloques de texto.
