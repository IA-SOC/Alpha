---
tags: [agentsoc, usage, data]
aliases: [Input format, Case JSON, Intake contract]
updated: 2026-10-11
---

# Case format

The system accepts two formats:

| Format | Who reads it | Where it is defined |
| --- | --- | --- |
| **Intake contract v1.0** | The API (`POST /api/v1/cases`) | `docs/Incident_Case_Input_Specification_v1.0.docx` and `docs/incident-case-input-v1.0.schema.json` (both unchanged) |
| **Legacy direct format** | The agent CLI and `investigate()` from Python | The original agent scaffold |

## Intake contract v1.0 (the API)

Each alert comes wrapped, with its raw payload untouched:

```json
{
  "schema_version": "1.0",
  "case_id": "SPRINT2-DEMO-001",
  "submitted_at": "2026-10-09T12:10:00Z",
  "title": "Synthetic mixed-source correlation demo",
  "alerts": [
    { "alert_id": "ecs-auth-001", "source_system": "elastic",
      "source_version": "8.19", "ecs_version": "8.x",
      "raw_alert": { "event": { "id": "ecs-auth-001", "action": "failed_login" },
                     "@timestamp": "2026-10-09T12:00:00Z",
                     "source": { "ip": "192.0.2.50" }, "host": { "name": "web-01" },
                     "user": { "name": "demo-user" }, "tags": ["brute_force"] } }
  ],
  "enrichments": [
    { "provider": "synthetic_feed",
      "observable": { "type": "ip", "value": "192.0.2.50" },
      "related_alert_ids": ["ecs-auth-001"],
      "raw_result": { "reference": "https://example.test/synthetic-ioc" } }
  ]
}
```

| Field | Use |
| --- | --- |
| `alerts[].alert_id` | The alert ID. Intake checks it matches the native ID inside `raw_alert` (rule VR-10). |
| `alerts[].source_system` | `elastic` or `wazuh`. Sets the detected format. |
| `alerts[].raw_alert` | The original alert. Custom nested fields are **kept**; the standard `_source` export envelope is supported. |
| `enrichments[]` | Optional. Only `provider` and `observable` are mandatory. See [[17 IoC integration and traceability]]. |

The envelope is strict: **unknown top-level fields are rejected**, but custom fields inside `raw_alert` and `raw_result` are preserved. Full example: `examples/sprint2_demo.json`. More samples in `examples/` and `examples/test_cases/`.

### Where the native ID is read

| Source | Default pointer | Variable to change it |
| --- | --- | --- |
| Elastic | `/event/id` | `ELASTIC_ALERT_ID_POINTER` |
| Wazuh | `/id` | `WAZUH_ALERT_ID_POINTER` |

Set real export paths (for example `/_id` or `/_source/id`) before starting the server. No native ID field is guessed.

## Legacy direct format (CLI)

An object with the alert list and, optionally, IoC enrichment:

```json
{
  "case_id": "SYN-PHISH-001",
  "synthetic": true,
  "description": "Free text describing the case",
  "alerts": [ { "...": "one alert per item" } ],
  "enrichment": [
    { "indicator": "198.51.100.23", "type": "ip", "verdict": "malicious",
      "source": "simulated-n8n-feed", "retrieved_at": "2026-09-14T13:10:00Z" }
  ]
}
```

| Field | Required | Use |
| --- | --- | --- |
| `case_id` | Yes | Case identifier in the report. |
| `alerts` | Yes | Alert list. Formats can be mixed. |
| `synthetic` | No | If `true`, no hypothesis goes above "medium" confidence. |
| `description` | No | Informational only. |
| `enrichment` | No | Already-enriched IoC. If missing, the report says `no_disponible`. |

> [!warning] The CLI does not read the wrapped contract
> In Sprint 2, translation from the contract to the agent is done by the backend adapter (`app/services/agent_adapter.py`), not by the agent. Passing a v1.0 file directly to `agent/graph.py` does not unwrap `raw_alert`. Use the API for contract cases.

## Alert formats the agent recognizes

Detected per alert by shape (`detect_format` in `agent/normalize.py`). With the API, `source_system` decides instead.

| Format | How it is recognized |
| --- | --- |
| **Wazuh** | Has `agent` as an object and `rule.level`. |
| **Elastic Security** | Has `kibana.alert.uuid` or `kibana.alert.rule.name`. |
| **Elastic ECS** | Has `@timestamp` or `event` as an object. |
| **Internal** (`unknown`) | None of the above: the simple scaffold format. |

If the case mixes formats, the report declares it `mixed`.

## Which fields are read from each alert

| Normalized value | Taken from, in order |
| --- | --- |
| ID | `alert_id`, `id`, `_id`, `event.id`, `kibana.alert.uuid`. With the API, always the wrapper `alert_id`. |
| Time | `timestamp` or `@timestamp` |
| Rule name | `rule_name`, `kibana.alert.rule.name`, `rule.name`, `rule.description`, `event.action` |
| Tags | `tags` + `rule.groups` (Wazuh) + `event.category` (ECS) |
| Host | `host` (text) or `host.name`, `host.hostname`, `agent.name` |
| User | `user` (text) or `user.name`, `data.srcuser`, `data.dstuser` |
| Source / destination IP | `source_ip` / `source.ip` / `data.srcip` · `dest_ip` / `destination.ip` / `data.dstip` |

Nested (`{"event": {"id": "x"}}`) and flat (`{"event.id": "x"}`) fields are both accepted. **New in Sprint 2:** a host or user that is not a string (for example a custom object) is ignored instead of crashing the agent.

The correlation engine reads a wider field set (process, session, hashes, IDs). See [[16 Correlation engine#Fields it compares]].

## Times and time zones

- Accepts ISO-8601 with a zone: `2026-09-15T03:02:11Z`, `2026-09-15T03:02:11-05:00` and also `-0500`.
- Converts to UTC and **keeps the original time** in the report.
- A time without a zone (`2026-09-18 09:30:00`) is **not assumed to be UTC**: it is marked `timezone_unknown` and logged as a limitation.
- A missing time does not stop processing; the alert is listed in `missing_fields`.
- **New in Sprint 2:** extreme dates that overflow when converted are marked `invalid` instead of raising an error.
- With the API, `submitted_at` is **never** used in place of a missing event time.

> [!note] Wazuh synonyms
> Some Wazuh groups are translated to catalog signals (`TAG_SYNONYMS` in `agent/normalize.py`): `authentication_failed` and `invalid_login` become `failed_login`, and `authentication_failures` becomes `multiple_auth_failures`.

## Limits

- Up to **50 alerts** per case (`MAX_ALERTS_PER_CASE`). The API rejects more; higher configured limits are not performance-certified.
- Duplicate IDs are rejected at intake and flagged by the agent.
- All alert text is **untrusted data**. A field like "ignore previous instructions" or "close the case" is logged in limitations and changes nothing.

Next: [[05 Architecture]] · Back to [[00 Home]]
