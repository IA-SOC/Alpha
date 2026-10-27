# Reporte de investigación SOC — borrador

## Caso y alcance
- ID del caso: SYN-PHISH-001
- Fuente/esquema y versión: elastic_ecs / no declarada
- Alertas recibidas / procesadas: 4 / 4
- Ventana temporal: 2026-09-14T13:02:10Z → 2026-09-14T13:44:30Z
- Limitaciones de entrada: ninguna detectada

## Resumen
Caso SYN-PHISH-001: 4 alertas procesadas. Técnicas candidatas evaluadas por grupos de alertas; la correlación no demuestra causalidad ni una secuencia de ataque. Hipótesis principal: Actividad compatible con Phishing (T1566, táctica Initial Access) en MAIL-GW-01. Confianza baja. Ningún compromiso se da por confirmado hasta la revisión del analista.

## Hipótesis ordenadas
### 1. Actividad compatible con Phishing (T1566, táctica Initial Access) en MAIL-GW-01. — confianza: baja
- Base de confianza: Una única alerta sostiene la hipótesis.
- Evidencia a favor: ecs-ph-001
- Evidencia en contra: —
- Alternativas plausibles: Correo legítimo de proveedor clasificado como sospechoso por la regla.
- Información que falta: No se sabe si el usuario introdujo credenciales en el sitio.

### 2. Actividad compatible con Phishing (T1566, táctica Initial Access) en WKS-22. — confianza: baja
- Base de confianza: Una única alerta sostiene la hipótesis.
- Evidencia a favor: ecs-ph-002
- Evidencia en contra: —
- Alternativas plausibles: Correo legítimo de proveedor clasificado como sospechoso por la regla.
- Información que falta: No se sabe si el usuario introdujo credenciales en el sitio.


## Correlación de alertas
- rel-0001: ecs-ph-001, ecs-ph-002 — uncertain (R2). Shared attributes exist, but independent corroboration or reliable temporal proximity is insufficient.
- rel-0002: ecs-ph-001, ecs-ph-003 — uncertain (R2). Shared attributes exist, but independent corroboration or reliable temporal proximity is insufficient.
- rel-0003: ecs-ph-001, ecs-ph-004 — uncertain (R2). Shared attributes exist, but independent corroboration or reliable temporal proximity is insufficient.
- rel-0004: ecs-ph-002, ecs-ph-003 — uncertain (R2). Shared attributes exist, but independent corroboration or reliable temporal proximity is insufficient.
- rel-0005: ecs-ph-002, ecs-ph-004 — uncertain (R2). Shared attributes exist, but independent corroboration or reliable temporal proximity is insufficient.
- rel-0006: ecs-ph-003, ecs-ph-004 — related (R1). At least two entity families match within the time window.
## Mapeo MITRE ATT&CK
| Táctica | Técnica (ID y nombre) | Estado | Evidencia referenciada |
|---|---|---|---|
| Initial Access | T1566 Phishing | candidate | ecs-ph-001 |
| Initial Access | T1566 Phishing | candidate | ecs-ph-002 |

## Línea de tiempo
| Hora original | Hora UTC / estado de zona | Evento observado o inferido | Alertas fuente |
|---|---|---|---|
| 2026-09-14T13:02:10Z | 2026-09-14T13:02:10Z | suspicious_attachment_or_link_in_email en host MAIL-GW-01 (usuario: mlopez) (observed) | ecs-ph-001 |
| 2026-09-14T13:05:44Z | 2026-09-14T13:05:44Z | credential_harvest_page_visited en host WKS-22 (usuario: mlopez) (observed) | ecs-ph-002 |
| 2026-09-14T13:41:02Z | 2026-09-14T13:41:02Z | login_from_new_country en host AAD-TENANT (usuario: mlopez) (observed) | ecs-ph-003 |
| 2026-09-14T13:44:30Z | 2026-09-14T13:44:30Z | new_inbox_forwarding_rule en host AAD-TENANT (usuario: mlopez) (observed) | ecs-ph-004 |

## Blast radius
- Activos observados (no equivale a compromiso): MAIL-GW-01 [ecs-ph-001]; WKS-22 [ecs-ph-002]; AAD-TENANT [ecs-ph-003, ecs-ph-004]
- Activos con impacto confirmado: ninguno
- Sospechosos: —
- Identidades afectadas (sospechosas): —
- Desconocidos / brechas de telemetría: Ningún activo se marca como confirmado: requiere validación del analista o telemetría adicional (EDR).; Actividad ambigua en MAIL-GW-01 (alertas ecs-ph-001): hipótesis de confianza baja o insuficiente.; Actividad ambigua en WKS-22 (alertas ecs-ph-002): hipótesis de confianza baja o insuficiente.

## IoC enriquecidos provistos
Estado: provided. Enriquecimiento tomado del caso tal como vino; no se hicieron consultas externas. Sin coincidencia exacta en alertas: 203.0.113.200.
- 198.51.100.23 (ip, veredicto malicious, fuente feed-simulado-n8n) → alertas: ecs-ph-002
- https://login-proveedor-pagos.example/o365 (url, veredicto phishing, fuente feed-simulado-n8n) → alertas: ecs-ph-001, ecs-ph-002
- 203.0.113.200 (ip, veredicto suspicious, fuente feed-simulado-n8n) → alertas: —

## Acciones recomendadas
1. [low] Bloquear el vector de entrada identificado (IP, dominio o archivo) — Derivada de las hipótesis 1, 2 (confianza baja, baja). Hipótesis: 1, 2. Evidencia: ecs-ph-001, ecs-ph-002. Pendiente de aprobación del analista.

## Limitaciones
- Motor determinista basado en reglas (core/logic.py); no usa un LLM y no cubre patrones fuera del catálogo.
- Los IDs ATT&CK provienen del catálogo local core/logic.RULES (sin versión ATT&CK fijada); se reportan como candidatos.
- El validador de la skill comprueba estructura y referencias, no la veracidad de las inferencias.
- Caso sintético: la confianza se limita a 'media' como máximo.
- Se detectó texto con forma de instrucción en ecs-ph-001.email.subject; se trató como dato no confiable y no se siguió.
- Related means shared observed entities, not a confirmed attack or causation.
- Noise is relative to this case and rule profile; alerts are never discarded.
- Groups are connected components, not proof that every pair is related.
- Unknown custom fields are retained but require verified mappings to correlate.
- Names are compared exactly; tenant/domain scoping requires customer validation.

## Revisión humana
- Estado: pending
- Analista: —
- Correcciones/notas: —
