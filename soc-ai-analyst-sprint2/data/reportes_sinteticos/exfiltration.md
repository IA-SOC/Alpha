# Reporte de investigación SOC — borrador

## Caso y alcance
- ID del caso: SYN-EXFIL-003
- Fuente/esquema y versión: unknown / no declarada
- Alertas recibidas / procesadas: 4 / 4
- Ventana temporal: 2026-09-16T22:10:00Z → 2026-09-16T22:50:00Z
- Limitaciones de entrada: ninguna detectada

## Resumen
Caso SYN-EXFIL-003: 4 alertas procesadas. Secuencia de ataque sugerida: Exfiltration Over C2 Channel (T1041, táctica: Exfiltration). Hipótesis principal: Actividad compatible con Exfiltration Over C2 Channel (T1041, táctica Exfiltration) en FS-01. Confianza media. Ningún compromiso se da por confirmado hasta la revisión del analista.

## Hipótesis ordenadas
### 1. Actividad compatible con Exfiltration Over C2 Channel (T1041, táctica Exfiltration) en FS-01. — confianza: media
- Base de confianza: 3 alertas con 2 reglas distintas coinciden. Se ajusta a la baja: el caso es sintético.
- Evidencia a favor: ex-2, ex-3, ex-4
- Evidencia en contra: —
- Alternativas plausibles: Replicación o respaldo externo autorizado.
- Información que falta: Se desconoce el contenido y el volumen exacto transferido.

## Mapeo MITRE ATT&CK
| Táctica | Técnica (ID y nombre) | Estado | Evidencia referenciada |
|---|---|---|---|
| Exfiltration | T1041 Exfiltration Over C2 Channel | candidate | ex-2, ex-3, ex-4 |

## Línea de tiempo
| Hora original | Hora UTC / estado de zona | Evento observado o inferido | Alertas fuente |
|---|---|---|---|
| 2026-09-16T22:10:00Z | 2026-09-16T22:10:00Z | archive_of_sensitive_share en host FS-01 (usuario: backup_ops) (observed) | ex-1 |
| 2026-09-16T22:31:00Z | 2026-09-16T22:31:00Z | large_outbound_transfer en host FS-01 (usuario: backup_ops) (observed) | ex-2 |
| 2026-09-16T22:33:00Z | 2026-09-16T22:33:00Z | dns_tunneling_suspected en host FS-01 (usuario: backup_ops) (observed) | ex-3 |
| 2026-09-16T22:50:00Z | 2026-09-16T22:50:00Z | large_outbound_transfer en host FS-01 (usuario: backup_ops) (observed) | ex-4 |

## Blast radius
- Activos observados (no equivale a compromiso): FS-01 [ex-1, ex-2, ex-3, ex-4]
- Activos con impacto confirmado: ninguno
- Sospechosos: FS-01 [ex-2, ex-3, ex-4]
- Identidades afectadas (sospechosas): backup_ops [ex-2, ex-3, ex-4]
- Desconocidos / brechas de telemetría: Ningún activo se marca como confirmado: requiere validación del analista o telemetría adicional (EDR).

## IoC enriquecidos provistos
Estado: no_disponible. El caso no trae enriquecimiento de IoC; no se hicieron consultas externas.

## Acciones recomendadas
1. [urgent] Bloquear las conexiones salientes hacia los destinos identificados — Derivada de la hipótesis 1 (confianza media). Evidencia: ex-2, ex-3, ex-4. Requiere aprobación humana.
2. [urgent] Notificar al equipo de respuesta a incidentes de exfiltración — Derivada de la hipótesis 1 (confianza media). Evidencia: ex-2, ex-3, ex-4. Requiere aprobación humana.

## Limitaciones
- Motor determinista basado en reglas (core/logic.py); no usa un LLM y no cubre patrones fuera del catálogo.
- Los IDs ATT&CK provienen del catálogo local core/logic.RULES (sin versión ATT&CK fijada); se reportan como candidatos.
- El validador de la skill comprueba estructura y referencias, no la veracidad de las inferencias.
- Caso sintético: la confianza se limita a 'media' como máximo.
- Formato interno simplificado del scaffold (no es ECS ni Wazuh nativo).

## Revisión humana
- Estado: pending
- Analista: —
- Correcciones/notas: —
