---
tags: [agentsoc, ioc, architecture]
aliases: [IoC integration, Traceability, US3, Evidence pointers]
updated: 2026-10-11
---

# IoC integration and traceability

**User story US3.** Use the threat intelligence the case already carries, link it to the right alerts, and make sure every finding that cites it can be traced back to the original submission.
**Files:** `app/services/ioc_integration.py`, `app/services/traceability.py`, plus `consume_enrichment` and `attach_ioc_references` in `agent/investigation.py`.

## The input

The v1.0 enrichment wrapper is provider-independent. Only `provider` and `observable` are mandatory:

```json
{
  "provider": "synthetic_feed",
  "observable": { "type": "ip", "value": "192.0.2.50" },
  "related_alert_ids": ["ecs-auth-001"],
  "raw_result": { "reference": "https://example.test/synthetic-ioc" }
}
```

`raw_result` is opaque: it is kept exactly as sent, including custom fields.

## Two ways to link an IoC to an alert

| Method | What it means | How it is found |
| --- | --- | --- |
| `explicit_reference` | The submitter **declared** the link in `related_alert_ids` | The alert ID is in the list. This does not claim the value appears in the alert. |
| `observable_match` | The value **was found** in a typed security field of the alert | Exact comparison against the fields the evidence extractor reads, with the pointer and value |

An association can carry both methods. The two are never merged into one, so the analyst can tell "someone said so" from "it is in the data".

### Supported observable types

| `observable.type` | Compared against | Normalization |
| --- | --- | --- |
| `ip`, `ipv4`, `ipv6` | Network fields | Canonical IP form |
| `domain`, `hostname` | `dns.question.name`, `url.domain`, `source.domain`, `destination.domain` | Case-insensitive, trailing dot ignored |
| `url` | `url.full`, `url.original` | Exact |
| `email` | `email.from.address`, `email.to.address` | Exact |
| `md5`, `sha1`, `sha256` | File and process hashes | Case-insensitive |
| `hash` | Any of the three hashes | Case-insensitive |

Unknown types keep their data and explicit links but get no automatic match.

> [!warning] Deliberately no fuzzy matching
> Free-text messages, custom fields, alert IDs and substrings are **never** used to infer an association. This avoids linking an IP to every alert that happens to mention it in a log line. (The CLI path without the adapter still uses the original exact-value search over all text fields.)

## The output item

Each IoC becomes an item that keeps every supplied field and adds:

| Key | Content |
| --- | --- |
| `evidence_id` | Case-local ID: `ioc-0001`, `ioc-0002`… |
| `source_path` | Pointer to the original item, for example `/enrichments/0` |
| `indicator`, `type`, `source` | Value, type and provider, for the legacy report fields |
| `associations` | Per alert: methods, matched fields with pointers, and the `reference_path` of a declared link |
| `associated_alert_ids` | Alerts linked by either method |
| `matched_alert_ids` | Alerts linked by an actual field match |
| `matched_fields` | Alert and field path of each match |

Unmatched IoCs stay visible with empty lists. Different providers for the same value stay separate. A missing verdict is **not** invented, and provider scores are not reinterpreted.

## How findings cite IoC

In phase 4, every hypothesis whose supporting alerts are associated with an IoC gets an `ioc_evidence` entry:

```json
{ "evidence_id": "ioc-0001", "source_path": "/enrichments/0", "alert_id": "ecs-auth-001",
  "provider": "synthetic_feed", "observable": { "type": "ip", "value": "192.0.2.50" },
  "association_methods": ["explicit_reference", "observable_match"], "role": "context" }
```

The role is always `context`. **IoC evidence never raises confidence automatically.** This is tested (`test_findings_reference_real_ioc_evidence_without_increasing_confidence`). No URL in `raw_result` is ever fetched.

## Traceability check

After the graph pauses, `verify_traceability(context, report)` checks the report against the full original case kept in `investigation_context.original_case`:

- Every correlation pair cites known alerts, and every evidence pointer **resolves to exactly the stated value** in that alert's `raw_alert`.
- Every IoC item is identical to what the adapter produced; nothing was changed in between.
- Every supplied field of the original enrichment is preserved in the item.
- Every declared link's `reference_path` really points to that alert ID.
- Every `source_fields` pointer in hypothesis evidence resolves to its value.
- Every `ioc_evidence` entry matches an existing item, provider, observable and association.

Any failure raises an error, and the API answers `502` without losing the case. This is stronger than the skill validator, which only checks that cited alert IDs exist (see [[07 Reading the report#What the validators guarantee and what they do not]]).

## Example: the Sprint 2 demo

| IoC | Linked alerts | Method |
| --- | --- | --- |
| `ioc-0001` (IP 192.0.2.50) | ecs-auth-001, wazuh-auth-002 | ecs-auth-001: declared + field match; wazuh-auth-002: field match only |
| `ioc-0002` (domain unseen.example.test) | wazuh-auth-002 | Declared link only; the domain is not in the alert |
| `ioc-0003` (IP 203.0.113.200) | none | Unmatched, still listed |

## N8N status

The backlog task "structure based on N8N output" is **in progress**. The documented v1.0 wrapper is implemented and tested, but no real customer N8N output was supplied. To close it: get representative anonymized N8N outputs, verify how provider, observable, result and reference map into v1.0, and add fixture-based compatibility tests. Do not mark it done from synthetic wrappers alone. There is no N8N webhook and no provider lookup.

Next: [[18 Explanation for beginners]] · Back to [[00 Home]]
