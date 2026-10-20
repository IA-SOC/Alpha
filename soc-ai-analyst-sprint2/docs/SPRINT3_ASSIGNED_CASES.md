# Sprint 3: implementación de las tareas de casos y pruebas

Fecha de verificación: 19 de octubre de 2026, zona America/Bogota.
Base: ZIP Alpha-main recibido para esta implementación.

## Alcance completado

Se implementaron las cuatro tareas de preparación de casos asignadas en el
Sprint Backlog. No se declara la aceptación completa de US4–US7 ni se asignan
horas reales a ninguna persona.

| Historia | Trabajo entregado | Evidencia ejecutable |
| --- | --- | --- |
| US4 | Tres entradas de timeline: Elastic, Wazuh y mixta; offsets, empates, falta de fecha y falta de zona. | `examples/sprint3/us4_*.json`; `tests/sprint3/test_us4_cases.py`: 9 pruebas. |
| US5 | Tres entradas: cinco técnicas positivas del catálogo local, negativos legítimos y comportamiento desconocido. Expectativas independientes de RULES. | `examples/sprint3/us5_*.json`; `tests/sprint3/test_us5_cases.py`: 7 pruebas. |
| US6 | Ataque compatible, actividad legítima y evidencia ambigua; soporte, contradicciones, alternativas, incógnitas y confianza. | `examples/sprint3/us6_*.json`; `tests/sprint3/test_us6_cases.py`: 4 pruebas. |
| US7 | Exportación anidada y campos personalizados, valores ausentes y proveedores contradictorios; preservación del original y rechazo de evidencia adulterada. | `examples/sprint3/us7_*.json`; `tests/sprint3/test_us7_cases.py`: 9 pruebas. |

Se añadieron 12 casos, un manifiesto de expectativas y 29 pruebas. Las entradas
son JSON válidos del backend v1.0; el manifiesto se mantiene separado para no
modificar el contrato de entrada. Las pruebas existentes de otros integrantes
se conservan sin cambios.

## Verificación realizada

Entorno: Linux, Python 3.12.14 y dependencias de `requirements-dev.txt`.
Se utilizó un entorno virtual aislado. No se modificaron requisitos ni versiones
del proyecto. Python 3.14 no se ejecutó localmente; sigue incluido en la matriz
del workflow existente, que todavía debe ejecutarse en GitHub tras subir cambios.

| Comprobación | Resultado |
| --- | --- |
| Suite antes del cambio | 214 passed, 3 xfailed, 40.61 s. |
| `python -m pytest tests/sprint3 -q` | 29 passed, 17.49 s. |
| `python -m pytest tests -q --junitxml=docs/verification/sprint3-assigned-pytest.xml` | 243 passed, 3 xfailed, 60.46 s. |
| `python -m ruff check app tests demo/run_pipeline.py demo/verify_local.py --exclude tests/test_agent_graph.py` | All checks passed. Mismo alcance del CI existente. |

Logs de esta ejecución: `docs/verification/sprint3-assigned-pytest.log`,
`sprint3-assigned-pytest.xml` y `sprint3-assigned-lint.log`.
La exclusión de `test_agent_graph.py` en lint ya estaba en el workflow original.

Los doce casos se presentan mediante el endpoint real de aceptación y se
investigan mediante el endpoint real de investigación. La base SQLite es
temporal y no requiere datos reales del cliente. Las verificaciones incluyen
valores esperados explícitos, preservación de payload y manipulación deliberada
de referencias para comprobar su rechazo. No se ejecutaron pruebas de carga ni
se midió cobertura de código.

## Defectos previos que siguen abiertos

Los tres `xfail(strict=True)` ya estaban en el ZIP y siguen activos:

| Pendiente | Prueba existente | Estado |
| --- | --- | --- |
| Ubicar eventos sin fecha o sin zona después de la secuencia fechada. | `tests/test_timeline_order.py`, tarea #28. | Continúa fallando de forma esperada. |
| Separar borrado de shadow copies (T1490 esperado) de cifrado de archivos. | `tests/test_mitre_mapping.py`, tarea #33. | Continúa fallando de forma esperada. |
| Evitar secuencias de ataque entre alertas no relacionadas en la ruta directa del agente. | `tests/test_hypotheses.py`, tarea #38. | Continúa fallando de forma esperada. |

Un `xfail` representa un defecto conocido: no es una prueba aprobada ni una
funcionalidad completada. Las 243 pruebas aprobadas se cuentan aparte de esos
tres defectos. Las tareas de corrección de producción de otros integrantes
no se implementan en esta entrega de fixtures.

No se afirma integración con N8N ni compatibilidad con muestras reales del
cliente. Las reglas actuales son deterministas y no se añadió un LLM.

## Incorporar los cambios

Desde la raíz del repositorio, los cambios se limitan a:

- `soc-ai-analyst-sprint2/examples/sprint3/`: entradas, expectativas y guía.
- `soc-ai-analyst-sprint2/tests/sprint3/`: pruebas, carga y entorno temporal.
- `soc-ai-analyst-sprint2/docs/SPRINT3_ASSIGNED_CASES.md`: este informe.
- `soc-ai-analyst-sprint2/docs/verification/sprint3-assigned-*`: resultados.
- `soc-ai-analyst-sprint2/README.md`: enlace a esta entrega.

El ZIP entregado conserva el proyecto original y añade estos cambios. Para
integrarlo en una rama con avances posteriores, incorporar esas rutas y el
enlace del README, revisar el diff y ejecutar las pruebas. No es necesario
reemplazar los archivos de producción de los compañeros.

No se modificó Jira ni el Sprint Backlog. Después de revisión del equipo, se
pueden enlazar estos archivos, el commit/PR y los resultados a las cuatro
tareas de preparación de casos. Las historias completas requieren comprobar
los criterios y tareas restantes; las horas reales y la clasificación de uso
de IA deben registrarse con lo que efectivamente hizo y revisó cada integrante.
