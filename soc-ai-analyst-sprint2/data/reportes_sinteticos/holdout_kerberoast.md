# Reporte de investigación SOC — borrador

## Caso y alcance
- ID del caso: HOLDOUT-KRB-006
- Fuente/esquema y versión: elastic_ecs / no declarada
- Alertas recibidas / procesadas: 5 / 5
- Ventana temporal: 2026-09-19T14:03:12Z → 2026-09-19T15:21:30Z
- Limitaciones de entrada: ninguna detectada

## Resumen
Caso HOLDOUT-KRB-006: 5 alertas procesadas. Técnicas candidatas evaluadas por grupos de alertas; la correlación no demuestra causalidad ni una secuencia de ataque. Hipótesis principal: Actividad compatible con Remote Services (T1021, táctica Lateral Movement) en SRV-ERP-02. Confianza baja. Ningún compromiso se da por confirmado hasta la revisión del analista.

## Hipótesis ordenadas
### 1. Actividad compatible con Remote Services (T1021, táctica Lateral Movement) en SRV-ERP-02. — confianza: baja
- Base de confianza: Una única alerta sostiene la hipótesis.
- Evidencia a favor: ho-003
- Evidencia en contra: —
- Alternativas plausibles: Tarea administrativa o de respaldo legítima entre servidores.
- Información que falta: Falta confirmar si la sesión remota tenía un cambio aprobado.


## Correlación de alertas
- rel-0001: ho-001, ho-002 — uncertain (R2). Shared attributes exist, but independent corroboration or reliable temporal proximity is insufficient.
- rel-0002: ho-001, ho-003 — unrelated (R3). No shared values across at least two comparable entity families; unrelated under this rule profile, not proof of benign activity.
- rel-0003: ho-001, ho-004 — unrelated (R3). No shared values across at least two comparable entity families; unrelated under this rule profile, not proof of benign activity.
- rel-0004: ho-001, ho-005 — unrelated (R3). No shared values across at least two comparable entity families; unrelated under this rule profile, not proof of benign activity.
- rel-0005: ho-002, ho-003 — uncertain (R2). Shared attributes exist, but independent corroboration or reliable temporal proximity is insufficient.
- rel-0006: ho-002, ho-004 — unrelated (R3). No shared values across at least two comparable entity families; unrelated under this rule profile, not proof of benign activity.
- rel-0007: ho-002, ho-005 — unrelated (R3). No shared values across at least two comparable entity families; unrelated under this rule profile, not proof of benign activity.
- rel-0008: ho-003, ho-004 — uncertain (R2). Shared attributes exist, but independent corroboration or reliable temporal proximity is insufficient.
- rel-0009: ho-003, ho-005 — uncertain (R2). Shared attributes exist, but independent corroboration or reliable temporal proximity is insufficient.
- rel-0010: ho-004, ho-005 — related (R1). At least two entity families match within the time window.
## Mapeo MITRE ATT&CK
| Táctica | Técnica (ID y nombre) | Estado | Evidencia referenciada |
|---|---|---|---|
| Lateral Movement | T1021 Remote Services | candidate | ho-003 |

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
- Desconocidos / brechas de telemetría: Ningún activo se marca como confirmado: requiere validación del analista o telemetría adicional (EDR).; Actividad ambigua en SRV-ERP-02 (alertas ho-003): hipótesis de confianza baja o insuficiente.

## IoC enriquecidos provistos
Estado: no_disponible. El caso no trae enriquecimiento de IoC; no se hicieron consultas externas.

## Acciones recomendadas
1. [medium] Aislar los hosts involucrados de la red — Derivada de la hipótesis 1 (confianza baja). Evidencia: ho-003. Requiere aprobación humana.
2. [medium] Revisar reglas de segmentación entre los hosts afectados — Derivada de la hipótesis 1 (confianza baja). Evidencia: ho-003. Requiere aprobación humana.

## Limitaciones
- Motor determinista basado en reglas (core/logic.py); no usa un LLM y no cubre patrones fuera del catálogo.
- Los IDs ATT&CK provienen del catálogo local core/logic.RULES (sin versión ATT&CK fijada); se reportan como candidatos.
- El validador de la skill comprueba estructura y referencias, no la veracidad de las inferencias.
- Caso sintético: la confianza se limita a 'media' como máximo.
- Related means shared observed entities, not a confirmed attack or causation.
- Noise is relative to this case and rule profile; alerts are never discarded.
- Groups are connected components, not proof that every pair is related.
- Unknown custom fields are retained but require verified mappings to correlate.
- Names are compared exactly; tenant/domain scoping requires customer validation.

## Revisión humana
- Estado: pending
- Analista: —
- Correcciones/notas: —
