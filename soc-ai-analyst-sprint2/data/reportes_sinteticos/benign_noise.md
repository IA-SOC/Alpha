# Reporte de investigación SOC — borrador

## Caso y alcance
- ID del caso: SYN-BENIGN-005
- Fuente/esquema y versión: unknown / no declarada
- Alertas recibidas / procesadas: 3 / 3
- Ventana temporal: 2026-09-18T09:00:00Z → 2026-09-18T09:00:00Z
- Limitaciones de entrada: bn-3: timestamp

## Resumen
Caso SYN-BENIGN-005: 3 alertas procesadas. Ninguna coincide con el catálogo de técnicas; no se sostiene una hipótesis de ataque con estos datos.

## Hipótesis ordenadas
_Sin hipótesis sostenidas por los datos._

## Correlación de alertas
- rel-0001: bn-1, bn-2 — uncertain (R4). Insufficient comparable entity evidence; absence is not disproof.
- rel-0002: bn-1, bn-3 — uncertain (R2). Shared attributes exist, but independent corroboration or reliable temporal proximity is insufficient.
- rel-0003: bn-2, bn-3 — uncertain (R4). Insufficient comparable entity evidence; absence is not disproof.
## Mapeo MITRE ATT&CK
| Táctica | Técnica (ID y nombre) | Estado | Evidencia referenciada |
|---|---|---|---|

## Línea de tiempo
| Hora original | Hora UTC / estado de zona | Evento observado o inferido | Alertas fuente |
|---|---|---|---|
| 2026-09-18T09:00:00Z | 2026-09-18T09:00:00Z | software_update_installed en host WKS-40 (usuario: sccm_svc) (observed) | bn-1 |

### Eventos sin hora UTC utilizable (fuera de la secuencia)
| Hora original | Estado de zona | Evento observado o inferido | Alertas fuente |
|---|---|---|---|
| 2026-09-18 09:30:00 | zona desconocida | authorized_vulnerability_scan en host SCANNER-01 (observed) | bn-2 |
| — | sin timestamp | service_restarted en host WKS-40 (observed) | bn-3 |

## Blast radius
- Activos observados (no equivale a compromiso): WKS-40 [bn-1, bn-3]; SCANNER-01 [bn-2]
- Activos con impacto confirmado: ninguno
- Sospechosos: —
- Identidades afectadas (sospechosas): —
- Desconocidos / brechas de telemetría: Ningún activo se marca como confirmado: requiere validación del analista o telemetría adicional (EDR).

## IoC enriquecidos provistos
Estado: no_disponible. El caso no trae enriquecimiento de IoC; no se hicieron consultas externas.

## Acciones recomendadas
_Sin acciones propuestas._

## Limitaciones
- Motor determinista basado en reglas (core/logic.py); no usa un LLM y no cubre patrones fuera del catálogo.
- Los IDs ATT&CK provienen del catálogo local core/logic.RULES (sin versión ATT&CK fijada); se reportan como candidatos.
- El validador de la skill comprueba estructura y referencias, no la veracidad de las inferencias.
- Caso sintético: la confianza se limita a 'media' como máximo.
- bn-2: timestamp sin zona horaria (2026-09-18 09:30:00); no se asume UTC.
- Formato interno simplificado del scaffold (no es ECS ni Wazuh nativo).
- Related means shared observed entities, not a confirmed attack or causation.
- Noise is relative to this case and rule profile; alerts are never discarded.
- Groups are connected components, not proof that every pair is related.
- Unknown custom fields are retained but require verified mappings to correlate.
- Names are compared exactly; tenant/domain scoping requires customer validation.

## Revisión humana
- Estado: pending
- Analista: —
- Correcciones/notas: —
