# Reporte de investigación SOC — borrador

## Caso y alcance
- ID del caso: HOLDOUT-KRB-006
- Fuente/esquema y versión: elastic_ecs / no declarada
- Alertas recibidas / procesadas: 5 / 5
- Ventana temporal: 2026-09-19T14:03:12Z → 2026-09-19T15:21:30Z
- Limitaciones de entrada: ninguna detectada

## Resumen
Caso HOLDOUT-KRB-006: 5 alertas procesadas. Ninguna coincide con el catálogo de técnicas; no se sostiene una hipótesis de ataque con estos datos.

## Hipótesis ordenadas
_Sin hipótesis sostenidas por los datos._
## Mapeo MITRE ATT&CK
| Táctica | Técnica (ID y nombre) | Estado | Evidencia referenciada |
|---|---|---|---|

## Línea de tiempo
| Hora original | Hora UTC / estado de zona | Evento observado o inferido | Alertas fuente |
|---|---|---|---|
| 2026-09-19T14:03:12Z | 2026-09-19T14:03:12Z | Microsoft Office Child Process Spawned PowerShell en host WKS-31 (usuario: rquispe) (observed) | ho-001 |
| 2026-09-19T14:19:40Z | 2026-09-19T14:19:40Z | Kerberos Service Ticket Requests with RC4 Encryption Burst en host DC-01 (usuario: rquispe) (observed) | ho-002 |
| 2026-09-19T15:02:05Z | 2026-09-19T15:02:05Z | RDP Logon to Server from Workstation with Service Account en host SRV-ERP-02 (usuario: svc_sqlreport) (observed) | ho-003 |
| 2026-09-19T15:20:48Z | 2026-09-19T15:20:48Z | Rclone Execution with Cloud Remote en host SRV-ERP-02 (usuario: svc_sqlreport) (observed) | ho-004 |
| 2026-09-19T15:21:30Z | 2026-09-19T15:21:30Z | Unusual Volume of Outbound Data to Cloud Storage en host SRV-ERP-02 (usuario: svc_sqlreport) (observed) | ho-005 |

## Blast radius
- Activos observados (no equivale a compromiso): WKS-31 [ho-001]; DC-01 [ho-002]; SRV-ERP-02 [ho-003, ho-004, ho-005]
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

## Revisión humana
- Estado: pending
- Analista: —
- Correcciones/notas: —
