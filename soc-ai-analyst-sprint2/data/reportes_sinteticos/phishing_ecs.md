# Reporte de investigación SOC — borrador

## Caso y alcance
- ID del caso: SYN-PHISH-001
- Fuente/esquema y versión: elastic_ecs / no declarada
- Alertas recibidas / procesadas: 4 / 4
- Ventana temporal: 2026-09-14T13:02:10Z → 2026-09-14T13:44:30Z
- Limitaciones de entrada: ninguna detectada

## Resumen
Caso SYN-PHISH-001: 4 alertas procesadas. Secuencia de ataque sugerida: Phishing (T1566, táctica: Initial Access). Hipótesis principal: Actividad compatible con Phishing (T1566, táctica Initial Access) en MAIL-GW-01, WKS-22. Confianza media. Ningún compromiso se da por confirmado hasta la revisión del analista.

## Hipótesis ordenadas
### 1. Actividad compatible con Phishing (T1566, táctica Initial Access) en MAIL-GW-01, WKS-22. — confianza: media
- Base de confianza: 2 alertas coherentes, sin corroboración de otra fuente.
- Evidencia a favor: ecs-ph-001, ecs-ph-002
- Evidencia en contra: —
- Alternativas plausibles: Correo legítimo de proveedor clasificado como sospechoso por la regla.
- Información que falta: No se sabe si el usuario introdujo credenciales en el sitio.

## Mapeo MITRE ATT&CK
| Táctica | Técnica (ID y nombre) | Estado | Evidencia referenciada |
|---|---|---|---|
| Initial Access | T1566 Phishing | candidate | ecs-ph-001, ecs-ph-002 |

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
- Sospechosos: MAIL-GW-01 [ecs-ph-001]; WKS-22 [ecs-ph-002]
- Identidades afectadas (sospechosas): mlopez [ecs-ph-001, ecs-ph-002]
- Desconocidos / brechas de telemetría: Ningún activo se marca como confirmado: requiere validación del analista o telemetría adicional (EDR).

## IoC enriquecidos provistos
Estado: provided. Enriquecimiento tomado del caso tal como vino; no se hicieron consultas externas. Sin coincidencia exacta en alertas: 203.0.113.200.
- 198.51.100.23 (ip, malicious, fuente feed-simulado-n8n) → alertas: ecs-ph-002
- https://login-proveedor-pagos.example/o365 (url, phishing, fuente feed-simulado-n8n) → alertas: ecs-ph-001, ecs-ph-002
- 203.0.113.200 (ip, suspicious, fuente feed-simulado-n8n) → alertas: —

## Acciones recomendadas
1. [medium] Bloquear el vector de entrada identificado (IP, dominio o archivo) — Derivada de la hipótesis 1 (confianza media). Evidencia: ecs-ph-001, ecs-ph-002. Requiere aprobación humana.

## Limitaciones
- Motor determinista basado en reglas (core/logic.py); no usa un LLM y no cubre patrones fuera del catálogo.
- Los IDs ATT&CK provienen del catálogo local core/logic.RULES (sin versión ATT&CK fijada); se reportan como candidatos.
- El validador de la skill comprueba estructura y referencias, no la veracidad de las inferencias.
- Caso sintético: la confianza se limita a 'media' como máximo.
- Se detectó texto con forma de instrucción en ecs-ph-001.email.subject; se trató como dato no confiable y no se siguió.

## Revisión humana
- Estado: pending
- Analista: —
- Correcciones/notas: —
