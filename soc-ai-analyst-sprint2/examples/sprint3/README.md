# Casos sintéticos del Sprint 3

Estos doce archivos son entradas válidas del contrato backend v1.0. Son datos
de laboratorio; no representan exportaciones reales del cliente ni validan
la compatibilidad con N8N. `expectations.json` es el manifiesto de pruebas y
no debe enviarse al endpoint de casos.

| Tarea asignada | Entradas | Qué comprueban |
| --- | --- | --- |
| US4: fixtures de timeline | `us4_elastic.json`, `us4_wazuh.json`, `us4_mixed.json` | Entradas desordenadas, equivalencia de offsets -05:00/+02:00, empates conservando orden de entrada, eventos sin fecha y fechas sin zona. |
| US5: muestras MITRE | `us5_positive.json`, `us5_negative.json`, `us5_unknown.json` | Cinco técnicas del catálogo local, actividad legítima y patrones no cubiertos. |
| US6: escenarios de hipótesis | `us6_attack.json`, `us6_benign.json`, `us6_ambiguous.json` | Evidencia a favor, ausencia de hipótesis para actividad legítima y evidencia contradictoria que reduce confianza. |
| US7: trazabilidad | `us7_nested_custom.json`, `us7_missing.json`, `us7_conflicting_providers.json` | Campos personalizados, `_source`, claves con `/` y `~`, nulos originales, campos ausentes y resultados contradictorios de proveedores. |

## Ejecución

Desde `soc-ai-analyst-sprint2/`, con el entorno virtual activado:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest tests/sprint3 -q
python -m pytest tests -q
```

Las pruebas crean una base SQLite temporal, presentan los casos por la API y
ejecutan la investigación real. No requieren iniciar un servidor manualmente
ni introducir credenciales. El workflow existente recoge las pruebas nuevas.

Para probar una entrada manualmente, enviar el contenido del archivo a
`POST /api/v1/cases` y después invocar
`POST /api/v1/cases/{case_id}/investigate` con el UUID devuelto.
Reenviar el mismo `case_id` a la misma base produce el conflicto esperado de
unicidad; para repetir, usar una base de pruebas nueva o un identificador nuevo.

## Resultados esperados

`expectations.json` fija los valores esperados fuera de la lógica de producción.
Las expectativas MITRE no se calculan leyendo `core.logic.RULES`.

- US4: secuencia con tiempo conocido `early`, `tie-b`, `tie-a`, `late`.
  `missing` y `no-zone` no reciben una fecha inventada. El defecto existente
  sobre su ubicación antes/después de los eventos fechados sigue pendiente.
- US5: positivos T1110, T1021, T1566, T1041 y T1486 como candidatos del
  catálogo local. Negativos y desconocidos no generan mapeos ni hipótesis.
  No se afirma cobertura completa ni una versión oficial de ATT&CK.
- US6: ataque compatible con confianza `media`; actividad legítima sin
  hipótesis; caso ambiguo con confianza `baja` y la alerta `approved` como
  evidencia en contra. Son hipótesis, no ataques confirmados.
- US7: el payload original queda intacto; las referencias resuelven a sus
  valores originales. Los dos proveedores conservan resultados separados y
  ningún veredicto agregado se inventa. Se rechazan referencias y resultados
  adulterados deliberadamente por las pruebas.

Los proveedores, IP y hosts son sintéticos. Estas entradas usan el contrato
backend; no deben introducirse directamente en `agent/run_synthetic.py`, que
consume el formato legado del agente.
