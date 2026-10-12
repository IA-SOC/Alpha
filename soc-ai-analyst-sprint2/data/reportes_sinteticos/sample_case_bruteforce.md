# Reporte de investigación SOC — borrador

## Caso y alcance
- ID del caso: CASE-0001
- Fuente/esquema y versión: unknown / no declarada
- Alertas recibidas / procesadas: 4 / 4
- Ventana temporal: 2026-09-10T02:14:00Z → 2026-09-10T03:10:00Z
- Limitaciones de entrada: ninguna detectada

## Resumen
Caso CASE-0001: 4 alertas procesadas. Secuencia de ataque sugerida: Brute Force (T1110, táctica: Credential Access) → Remote Services (T1021, táctica: Lateral Movement). Hipótesis principal: Actividad compatible con Remote Services (T1021, táctica Lateral Movement) en SRV-DB-01, WKS-15. Confianza media. Ningún compromiso se da por confirmado hasta la revisión del analista.

## Hipótesis ordenadas
### 1. Actividad compatible con Remote Services (T1021, táctica Lateral Movement) en SRV-DB-01, WKS-15. — confianza: media
- Base de confianza: 2 alertas coherentes, sin corroboración de otra fuente.
- Evidencia a favor: a3, a4
- Evidencia en contra: —
- Alternativas plausibles: Tarea administrativa o de respaldo legítima entre servidores.
- Información que falta: Falta confirmar si la sesión remota tenía un cambio aprobado.

### 2. Actividad compatible con Brute Force (T1110, táctica Credential Access) en WKS-15. — confianza: baja
- Base de confianza: Una única alerta sostiene la hipótesis.
- Evidencia a favor: a1
- Evidencia en contra: —
- Alternativas plausibles: Usuario legítimo que olvidó su contraseña o script con credenciales vencidas.
- Información que falta: No hay telemetría de EDR que confirme ejecución posterior al acceso.

## Mapeo MITRE ATT&CK
| Táctica | Técnica (ID y nombre) | Estado | Evidencia referenciada |
|---|---|---|---|
| Lateral Movement | T1021 Remote Services | candidate | a3, a4 |
| Credential Access | T1110 Brute Force | candidate | a1 |

## Línea de tiempo
| Hora original | Hora UTC / estado de zona | Evento observado o inferido | Alertas fuente |
|---|---|---|---|
| 2026-09-10T02:14:00Z | 2026-09-10T02:14:00Z | multiple_auth_failures en host WKS-15 (usuario: jgomez) (observed) | a1 |
| 2026-09-10T02:20:00Z | 2026-09-10T02:20:00Z | successful_login_after_failures en host WKS-15 (usuario: jgomez) (observed) | a2 |
| 2026-09-10T02:45:00Z | 2026-09-10T02:45:00Z | smb_admin_share_access en host WKS-15 (usuario: jgomez) (observed) | a3 |
| 2026-09-10T03:10:00Z | 2026-09-10T03:10:00Z | remote_exec_detected en host SRV-DB-01 (usuario: jgomez) (observed) | a4 |

## Blast radius
- Activos observados (no equivale a compromiso): WKS-15 [a1, a2, a3]; SRV-DB-01 [a4]
- Activos con impacto confirmado: ninguno
- Sospechosos: WKS-15 [a3]; SRV-DB-01 [a4]
- Identidades afectadas (sospechosas): jgomez [a3, a4]
- Desconocidos / brechas de telemetría: Ningún activo se marca como confirmado: requiere validación del analista o telemetría adicional (EDR).

## IoC enriquecidos provistos
Estado: no_disponible. El caso no trae enriquecimiento de IoC; no se hicieron consultas externas.

## Acciones recomendadas
1. [high] Aislar los hosts involucrados de la red — Derivada de la hipótesis 1 (confianza media). Evidencia: a3, a4. Requiere aprobación humana.
2. [high] Revisar reglas de segmentación entre los hosts afectados — Derivada de la hipótesis 1 (confianza media). Evidencia: a3, a4. Requiere aprobación humana.
3. [medium] Forzar rotación de credenciales de las cuentas involucradas — Derivada de la hipótesis 2 (confianza baja). Evidencia: a1. Requiere aprobación humana.
4. [medium] Habilitar/reforzar MFA en los hosts afectados — Derivada de la hipótesis 2 (confianza baja). Evidencia: a1. Requiere aprobación humana.

## Limitaciones
- Motor determinista basado en reglas (core/logic.py); no usa un LLM y no cubre patrones fuera del catálogo.
- Los IDs ATT&CK provienen del catálogo local core/logic.RULES (sin versión ATT&CK fijada); se reportan como candidatos.
- El validador de la skill comprueba estructura y referencias, no la veracidad de las inferencias.
- Formato interno simplificado del scaffold (no es ECS ni Wazuh nativo).

## Revisión humana
- Estado: pending
- Analista: —
- Correcciones/notas: —
