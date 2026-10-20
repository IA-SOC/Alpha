# Reporte de investigación SOC — borrador

## Caso y alcance
- ID del caso: SYN-BF-WAZUH-002
- Fuente/esquema y versión: wazuh / no declarada
- Alertas recibidas / procesadas: 8 / 8
- Ventana temporal: 2026-09-15T08:02:11Z → 2026-09-15T08:16:00Z
- Limitaciones de entrada: ninguna detectada

## Resumen
Caso SYN-BF-WAZUH-002: 8 alertas procesadas. Técnicas candidatas evaluadas por grupos de alertas; la correlación no demuestra causalidad ni una secuencia de ataque. Hipótesis principal: Actividad compatible con Brute Force (T1110, táctica Credential Access) en web-01. Confianza media. Ningún compromiso se da por confirmado hasta la revisión del analista.

## Hipótesis ordenadas
### 1. Actividad compatible con Brute Force (T1110, táctica Credential Access) en web-01. — confianza: media
- Base de confianza: 3 alertas con 3 reglas distintas coinciden. Se ajusta a la baja: el caso es sintético.
- Evidencia a favor: 1726387331.1001, 1726387335.1002, 1726387340.1003
- Evidencia en contra: —
- Alternativas plausibles: Usuario legítimo que olvidó su contraseña o script con credenciales vencidas.
- Información que falta: No hay telemetría de EDR que confirme ejecución posterior al acceso.

### 2. Actividad compatible con Remote Services (T1021, táctica Lateral Movement) en db-02. — confianza: insuficiente
- Base de confianza: Una única alerta sostiene la hipótesis. Se ajusta a la baja: 2 alerta(s) sugieren actividad legítima.
- Evidencia a favor: 1726388100.1006
- Evidencia en contra: 1726388101.1007, 1726388160.1008
- Alternativas plausibles: Tarea administrativa o de respaldo legítima entre servidores.
- Información que falta: Falta confirmar si la sesión remota tenía un cambio aprobado.


## Correlación de alertas
- rel-0001: 1726387331.1001, 1726387335.1002 — related (R1). At least two entity families match within the time window.
- rel-0002: 1726387331.1001, 1726387340.1003 — related (R1). At least two entity families match within the time window.
- rel-0003: 1726387331.1001, 1726387402.1004 — related (R1). At least two entity families match within the time window.
- rel-0004: 1726387331.1001, 1726387500.1005 — related (R1). At least two entity families match within the time window.
- rel-0005: 1726387331.1001, 1726388100.1006 — unrelated (R3). No shared values across at least two comparable entity families; unrelated under this rule profile, not proof of benign activity.
- rel-0006: 1726387331.1001, 1726388101.1007 — unrelated (R3). No shared values across at least two comparable entity families; unrelated under this rule profile, not proof of benign activity.
- rel-0007: 1726387331.1001, 1726388160.1008 — unrelated (R3). No shared values across at least two comparable entity families; unrelated under this rule profile, not proof of benign activity.
- rel-0008: 1726387335.1002, 1726387340.1003 — related (R1). At least two entity families match within the time window.
- rel-0009: 1726387335.1002, 1726387402.1004 — related (R1). At least two entity families match within the time window.
- rel-0010: 1726387335.1002, 1726387500.1005 — related (R1). At least two entity families match within the time window.
- rel-0011: 1726387335.1002, 1726388100.1006 — unrelated (R3). No shared values across at least two comparable entity families; unrelated under this rule profile, not proof of benign activity.
- rel-0012: 1726387335.1002, 1726388101.1007 — unrelated (R3). No shared values across at least two comparable entity families; unrelated under this rule profile, not proof of benign activity.
- rel-0013: 1726387335.1002, 1726388160.1008 — unrelated (R3). No shared values across at least two comparable entity families; unrelated under this rule profile, not proof of benign activity.
- rel-0014: 1726387340.1003, 1726387402.1004 — related (R1). At least two entity families match within the time window.
- rel-0015: 1726387340.1003, 1726387500.1005 — related (R1). At least two entity families match within the time window.
- rel-0016: 1726387340.1003, 1726388100.1006 — unrelated (R3). No shared values across at least two comparable entity families; unrelated under this rule profile, not proof of benign activity.
- rel-0017: 1726387340.1003, 1726388101.1007 — unrelated (R3). No shared values across at least two comparable entity families; unrelated under this rule profile, not proof of benign activity.
- rel-0018: 1726387340.1003, 1726388160.1008 — unrelated (R3). No shared values across at least two comparable entity families; unrelated under this rule profile, not proof of benign activity.
- rel-0019: 1726387402.1004, 1726387500.1005 — related (R1). At least two entity families match within the time window.
- rel-0020: 1726387402.1004, 1726388100.1006 — unrelated (R3). No shared values across at least two comparable entity families; unrelated under this rule profile, not proof of benign activity.
- rel-0021: 1726387402.1004, 1726388101.1007 — unrelated (R3). No shared values across at least two comparable entity families; unrelated under this rule profile, not proof of benign activity.
- rel-0022: 1726387402.1004, 1726388160.1008 — unrelated (R3). No shared values across at least two comparable entity families; unrelated under this rule profile, not proof of benign activity.
- rel-0023: 1726387500.1005, 1726388100.1006 — unrelated (R3). No shared values across at least two comparable entity families; unrelated under this rule profile, not proof of benign activity.
- rel-0024: 1726387500.1005, 1726388101.1007 — unrelated (R3). No shared values across at least two comparable entity families; unrelated under this rule profile, not proof of benign activity.
- rel-0025: 1726387500.1005, 1726388160.1008 — unrelated (R3). No shared values across at least two comparable entity families; unrelated under this rule profile, not proof of benign activity.
- rel-0026: 1726388100.1006, 1726388101.1007 — related (R1). At least two entity families match within the time window.
- rel-0027: 1726388100.1006, 1726388160.1008 — related (R1). At least two entity families match within the time window.
- rel-0028: 1726388101.1007, 1726388160.1008 — related (R1). At least two entity families match within the time window.
## Mapeo MITRE ATT&CK
| Táctica | Técnica (ID y nombre) | Estado | Evidencia referenciada |
|---|---|---|---|
| Credential Access | T1110 Brute Force | candidate | 1726387331.1001, 1726387335.1002, 1726387340.1003 |
| Lateral Movement | T1021 Remote Services | candidate | 1726388100.1006 |

## Línea de tiempo
| Hora original | Hora UTC / estado de zona | Evento observado o inferido | Alertas fuente |
|---|---|---|---|
| 2026-09-15T03:02:11.000-0500 | 2026-09-15T08:02:11Z | sshd: attempt to login using a non-existent user en host web-01 (usuario: deploy) (observed) | 1726387331.1001 |
| 2026-09-15T03:02:15.000-0500 | 2026-09-15T08:02:15Z | sshd: authentication failed en host web-01 (usuario: deploy) (observed) | 1726387335.1002 |
| 2026-09-15T03:02:20.000-0500 | 2026-09-15T08:02:20Z | sshd: brute force trying to get access to the system en host web-01 (usuario: deploy) (observed) | 1726387340.1003 |
| 2026-09-15T03:03:22.000-0500 | 2026-09-15T08:03:22Z | sshd: authentication success en host web-01 (usuario: deploy) (observed) | 1726387402.1004 |
| 2026-09-15T03:05:00.000-0500 | 2026-09-15T08:05:00Z | Successful sudo to ROOT executed en host web-01 (usuario: deploy) (observed) | 1726387500.1005 |
| 2026-09-15T03:15:00.000-0500 | 2026-09-15T08:15:00Z | Internal SSH login from web tier to database tier en host db-02 (usuario: svc_backup) (observed) | 1726388100.1006 |
| 2026-09-15T03:15:01.000-0500 | 2026-09-15T08:15:01Z | Scheduled backup timer started (backup-nightly.timer) en host db-02 (usuario: svc_backup) (observed) | 1726388101.1007 |
| 2026-09-15T03:16:00.000-0500 | 2026-09-15T08:16:00Z | tar archive created under /var/backups en host db-02 (usuario: svc_backup) (observed) | 1726388160.1008 |

## Blast radius
- Activos observados (no equivale a compromiso): web-01 [1726387331.1001, 1726387335.1002, 1726387340.1003, 1726387402.1004, 1726387500.1005]; db-02 [1726388100.1006, 1726388101.1007, 1726388160.1008]
- Activos con impacto confirmado: ninguno
- Sospechosos: web-01 [1726387331.1001, 1726387335.1002, 1726387340.1003]
- Identidades afectadas (sospechosas): deploy [1726387331.1001, 1726387335.1002, 1726387340.1003]
- Desconocidos / brechas de telemetría: Ningún activo se marca como confirmado: requiere validación del analista o telemetría adicional (EDR).; Actividad ambigua en db-02 (alertas 1726388100.1006): hipótesis de confianza baja o insuficiente.

## IoC enriquecidos provistos
Estado: provided. Enriquecimiento tomado del caso tal como vino; no se hicieron consultas externas.
- 203.0.113.88 (ip, veredicto malicious, fuente feed-simulado-n8n) → alertas: 1726387331.1001, 1726387335.1002, 1726387340.1003, 1726387402.1004

## Acciones recomendadas
1. [high] Forzar rotación de credenciales de las cuentas involucradas — Derivada de la hipótesis 1 (confianza media). Evidencia: 1726387331.1001, 1726387335.1002, 1726387340.1003. Requiere aprobación humana.
2. [high] Habilitar/reforzar MFA en los hosts afectados — Derivada de la hipótesis 1 (confianza media). Evidencia: 1726387331.1001, 1726387335.1002, 1726387340.1003. Requiere aprobación humana.

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
