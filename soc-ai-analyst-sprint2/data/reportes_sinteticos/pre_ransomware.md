# Reporte de investigación SOC — borrador

## Caso y alcance
- ID del caso: SYN-RANSOM-004
- Fuente/esquema y versión: unknown / no declarada
- Alertas recibidas / procesadas: 5 / 5
- Ventana temporal: 2026-09-17T01:00:00Z → 2026-09-17T01:13:00Z
- Limitaciones de entrada: ninguna detectada

## Resumen
Caso SYN-RANSOM-004: 5 alertas procesadas. Secuencia de ataque sugerida: Remote Services (T1021, táctica: Lateral Movement) → Data Encrypted for Impact (T1486, táctica: Impact). Hipótesis principal: Actividad compatible con Remote Services (T1021, táctica Lateral Movement) en SRV-APP-02, SRV-FILE-01. Confianza media. Ningún compromiso se da por confirmado hasta la revisión del analista.

## Hipótesis ordenadas
### 1. Actividad compatible con Remote Services (T1021, táctica Lateral Movement) en SRV-APP-02, SRV-FILE-01. — confianza: media
- Base de confianza: 2 alertas coherentes, sin corroboración de otra fuente.
- Evidencia a favor: rw-1, rw-2
- Evidencia en contra: —
- Alternativas plausibles: Tarea administrativa o de respaldo legítima entre servidores.
- Información que falta: Falta confirmar si la sesión remota tenía un cambio aprobado.

### 2. Actividad compatible con Data Encrypted for Impact (T1486, táctica Impact) en SRV-FILE-01. — confianza: media
- Base de confianza: 3 alertas con 3 reglas distintas coinciden. Se ajusta a la baja: el caso es sintético.
- Evidencia a favor: rw-3, rw-4, rw-5
- Evidencia en contra: —
- Alternativas plausibles: Cifrado o limpieza legítima por software de respaldo/DLP.
- Información que falta: Se desconoce el alcance total de archivos afectados y el estado de backups.

## Mapeo MITRE ATT&CK
| Táctica | Técnica (ID y nombre) | Estado | Evidencia referenciada |
|---|---|---|---|
| Impact | T1486 Data Encrypted for Impact | candidate | rw-3, rw-4, rw-5 |
| Lateral Movement | T1021 Remote Services | candidate | rw-1, rw-2 |

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
- Sospechosos: SRV-APP-02 [rw-1]; SRV-FILE-01 [rw-2, rw-3, rw-4, rw-5]
- Identidades afectadas (sospechosas): adm_it [rw-1, rw-2, rw-3, rw-4, rw-5]
- Desconocidos / brechas de telemetría: Ningún activo se marca como confirmado: requiere validación del analista o telemetría adicional (EDR).

## IoC enriquecidos provistos
Estado: no_disponible. El caso no trae enriquecimiento de IoC; no se hicieron consultas externas.

## Acciones recomendadas
1. [urgent] Aislar inmediatamente los hosts afectados — Derivada de la hipótesis 2 (confianza media). Evidencia: rw-3, rw-4, rw-5. Requiere aprobación humana.
2. [urgent] Verificar integridad de backups antes de cualquier restauración — Derivada de la hipótesis 2 (confianza media). Evidencia: rw-3, rw-4, rw-5. Requiere aprobación humana.
3. [high] Aislar los hosts involucrados de la red — Derivada de la hipótesis 1 (confianza media). Evidencia: rw-1, rw-2. Requiere aprobación humana.
4. [high] Revisar reglas de segmentación entre los hosts afectados — Derivada de la hipótesis 1 (confianza media). Evidencia: rw-1, rw-2. Requiere aprobación humana.

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
