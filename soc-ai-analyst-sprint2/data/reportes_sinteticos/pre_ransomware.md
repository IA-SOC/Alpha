# Reporte de investigación SOC — borrador

## Caso y alcance
- ID del caso: SYN-RANSOM-004
- Fuente/esquema y versión: unknown / no declarada
- Alertas recibidas / procesadas: 5 / 5
- Ventana temporal: 2026-09-17T01:00:00Z → 2026-09-17T01:13:00Z
- Limitaciones de entrada: ninguna detectada

## Resumen
Caso SYN-RANSOM-004: 5 alertas procesadas. Técnicas candidatas evaluadas por grupos de alertas; la correlación no demuestra causalidad ni una secuencia de ataque. Hipótesis principal: Actividad compatible con Remote Services (T1021, táctica Lateral Movement) en SRV-APP-02, SRV-FILE-01. Confianza media. Ningún compromiso se da por confirmado hasta la revisión del analista.

## Hipótesis ordenadas
### 1. Actividad compatible con Remote Services (T1021, táctica Lateral Movement) en SRV-APP-02, SRV-FILE-01. — confianza: media
- Base de confianza: 2 alertas coherentes, sin corroboración de otra fuente.
- Evidencia a favor: rw-1, rw-2
- Evidencia en contra: —
- Alternativas plausibles: Tarea administrativa o de respaldo legítima entre servidores.
- Información que falta: Falta confirmar si la sesión remota tenía un cambio aprobado.

### 2. Actividad compatible con Data Encrypted for Impact (T1486, táctica Impact) en SRV-FILE-01. — confianza: media
- Base de confianza: 2 alertas coherentes, sin corroboración de otra fuente.
- Evidencia a favor: rw-4, rw-5
- Evidencia en contra: —
- Alternativas plausibles: Cifrado o limpieza legítima por software de respaldo/DLP.
- Información que falta: Se desconoce el alcance total de archivos afectados y el estado de backups.

### 3. Actividad compatible con System Services: Service Execution (T1569.002, táctica Execution) en SRV-FILE-01. — confianza: baja
- Base de confianza: Una única alerta sostiene la hipótesis.
- Evidencia a favor: rw-2
- Evidencia en contra: —
- Alternativas plausibles: Herramienta de administración remota (PsExec) usada por soporte de TI.
- Información que falta: Se desconoce qué binario ejecutó el servicio y con qué privilegios.

### 4. Actividad compatible con Inhibit System Recovery (T1490, táctica Impact) en SRV-FILE-01. — confianza: baja
- Base de confianza: Una única alerta sostiene la hipótesis.
- Evidencia a favor: rw-3
- Evidencia en contra: —
- Alternativas plausibles: Cifrado o limpieza legítima por software de respaldo/DLP.
- Información que falta: Se desconoce el alcance total de archivos afectados y el estado de backups.


## Correlación de alertas
- rel-0001: rw-1, rw-2 — related (R1). At least two entity families match within the time window.
- rel-0002: rw-1, rw-3 — uncertain (R2). Shared attributes exist, but independent corroboration or reliable temporal proximity is insufficient.
- rel-0003: rw-1, rw-4 — uncertain (R2). Shared attributes exist, but independent corroboration or reliable temporal proximity is insufficient.
- rel-0004: rw-1, rw-5 — uncertain (R2). Shared attributes exist, but independent corroboration or reliable temporal proximity is insufficient.
- rel-0005: rw-2, rw-3 — related (R1). At least two entity families match within the time window.
- rel-0006: rw-2, rw-4 — uncertain (R2). Shared attributes exist, but independent corroboration or reliable temporal proximity is insufficient.
- rel-0007: rw-2, rw-5 — uncertain (R2). Shared attributes exist, but independent corroboration or reliable temporal proximity is insufficient.
- rel-0008: rw-3, rw-4 — related (R1). At least two entity families match within the time window.
- rel-0009: rw-3, rw-5 — related (R1). At least two entity families match within the time window.
- rel-0010: rw-4, rw-5 — related (R1). At least two entity families match within the time window.
## Mapeo MITRE ATT&CK
| Táctica | Técnica (ID y nombre) | Estado | Evidencia referenciada |
|---|---|---|---|
| Lateral Movement | T1021 Remote Services | candidate | rw-1, rw-2 |
| Impact | T1486 Data Encrypted for Impact | candidate | rw-4, rw-5 |
| Execution | T1569.002 System Services: Service Execution | candidate | rw-2 |
| Impact | T1490 Inhibit System Recovery | candidate | rw-3 |

## Línea de tiempo
| Hora original | Hora UTC / estado de zona | Evento observado o inferido | Alertas fuente |
|---|---|---|---|
| 2026-09-17T01:00:00Z | 2026-09-17T01:00:00Z | smb_admin_share_access en host SRV-APP-02 (usuario: adm_it) (observed) | rw-1 |
| 2026-09-17T01:04:00Z | 2026-09-17T01:04:00Z | remote_exec_psexec_service en host SRV-FILE-01 (usuario: adm_it) (observed) | rw-2 |
| 2026-09-17T01:09:00Z | 2026-09-17T01:09:00Z | shadow_copy_deleted en host SRV-FILE-01 (usuario: adm_it) (observed) | rw-3 |
| 2026-09-17T01:12:00Z | 2026-09-17T01:12:00Z | mass_file_encryption en host SRV-FILE-01 (usuario: adm_it) (observed) | rw-4 |
| 2026-09-17T01:13:00Z | 2026-09-17T01:13:00Z | ransom_note_created en host SRV-FILE-01 (usuario: adm_it) (observed) | rw-5 |

## Blast radius
- Activos observados (no equivale a compromiso): SRV-APP-02 [rw-1]; SRV-FILE-01 [rw-2, rw-3, rw-4, rw-5]
- Activos con impacto confirmado: ninguno
- Sospechosos: SRV-APP-02 [rw-1]; SRV-FILE-01 [rw-2, rw-4, rw-5]
- Identidades afectadas (sospechosas): adm_it [rw-1, rw-2, rw-4, rw-5]
- Desconocidos / brechas de telemetría: Ningún activo se marca como confirmado: requiere validación del analista o telemetría adicional (EDR).

## IoC enriquecidos provistos
Estado: no_disponible. El caso no trae enriquecimiento de IoC; no se hicieron consultas externas.

## Acciones recomendadas
1. [urgent] Aislar inmediatamente los hosts afectados — Derivada de la hipótesis 2 (confianza media). Evidencia: rw-4, rw-5. Requiere aprobación humana.
2. [urgent] Verificar integridad de backups antes de cualquier restauración — Derivada de la hipótesis 2 (confianza media). Evidencia: rw-4, rw-5. Requiere aprobación humana.
3. [high] Aislar los hosts involucrados de la red — Derivada de la hipótesis 1 (confianza media). Evidencia: rw-1, rw-2. Requiere aprobación humana.
4. [high] Revisar reglas de segmentación entre los hosts afectados — Derivada de la hipótesis 1 (confianza media). Evidencia: rw-1, rw-2. Requiere aprobación humana.
5. [medium] Revisar y deshabilitar los servicios creados recientemente en los hosts afectados — Derivada de la hipótesis 3 (confianza baja). Evidencia: rw-2. Requiere aprobación humana.

## Limitaciones
- Motor determinista basado en reglas (core/logic.py); no usa un LLM y no cubre patrones fuera del catálogo.
- Los IDs ATT&CK provienen del catálogo local core/logic.RULES (sin versión ATT&CK fijada); se reportan como candidatos.
- El validador de la skill comprueba estructura y referencias, no la veracidad de las inferencias.
- Caso sintético: la confianza se limita a 'media' como máximo.
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
