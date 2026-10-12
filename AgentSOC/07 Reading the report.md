---
tags: [agentsoc, usage, report]
aliases: [Report, Read the report]
updated: 2026-10-11
---

# Reading the report

The system delivers the same report in two forms:

- **JSON:** follows the skill schema `urn:soc-investigation-report:schema:1.1`. It is what gets validated and what another system (a case manager, for example) would read.
- **Markdown:** the readable draft for the analyst, from the `templates/reporte.md` template.

> [!note] The report text is in Spanish
> The agent's generated sentences (summaries, explanations, actions) and enum values like `alta` or `no_disponible` are in Spanish, as in the original agent. The new correlation and IoC explanations from the backend are in English.

Real examples: `demo/output/investigation.json` and `demo/output/report.md` (API run), and `data/reportes_sinteticos/` (CLI runs).

## The API response

`POST /investigate` and `GET /investigation` return an envelope around the report:

| Key | Content |
| --- | --- |
| `case_id` | Application UUID |
| `run_id` | UUID of this investigation run (also the graph `thread_id`) |
| `status` | `pending_review`, then `validated`, `corrected` or `rejected` |
| `correlation` | The correlation result (also inside the report) |
| `investigation_context` | Everything the adapter built, including the full `original_case` |
| `report` | The JSON report (below) |
| `report_markdown` | The Markdown draft |
| `validation` | Skill validator result plus `traceability_ok: true` |
| `audit_log` | All phase entries |

## Report sections

| Key | What it contains | How to read it |
| --- | --- | --- |
| `case_id` | Application UUID (API) or submitted ID (CLI) | — |
| `submitted_case_id` | **New.** The ID the client sent | Links the report to the client's ticket |
| `generated_at` | Generation date (UTC) | — |
| `methodology` | Skill, schema, engine and catalog used | Which version produced the analysis |
| `input` | Format, alerts received and processed, time window, missing fields, warnings | Check it first: it says how complete the data was |
| `executive_summary` | 2 or 3 sentences | Never claims confirmed compromise |
| `attack_mapping` | Candidate MITRE techniques with evidence | `status` is always `candidate`: mapping is not confirming |
| `hypotheses` | Ranked hypotheses | See below |
| `correlation` | **New.** Pairs, alert dispositions, groups, noise candidates | See [[16 Correlation engine]] |
| `timeline` | Sorted events | `certainty: observed` = comes straight from an alert |
| `blast_radius` | Assets and identities | See below |
| `enrichment` | IoC items and their associations | See [[17 IoC integration and traceability]] |
| `recommended_actions` | Proposed actions | All need human approval |
| `limitations` | What the analysis could not do or does not know | Read them before trusting a hypothesis |
| `audit_trail` | Phases 1 to 4 with duration | Proof of execution order |
| `review` | Review status | `pending` until the analyst decides |

## A hypothesis

```json
{
  "rank": 1,
  "statement": "Actividad compatible con Brute Force (T1110, táctica Credential Access) en web-01.",
  "confidence": "media",
  "confidence_basis": "Dos alertas sostienen la hipótesis...",
  "correlation_group_alert_ids": ["ecs-auth-001", "wazuh-auth-002"],
  "evidence_for": [
    { "alert_id": "ecs-auth-001", "role": "supporting", "observation": "...",
      "source_fields": [ { "alert_id": "ecs-auth-001",
                           "path": "/alerts/0/raw_alert/tags", "value": ["brute_force"] } ] }
  ],
  "evidence_against": [],
  "ioc_evidence": [
    { "evidence_id": "ioc-0001", "source_path": "/enrichments/0", "alert_id": "ecs-auth-001",
      "provider": "synthetic_feed", "observable": { "type": "ip", "value": "192.0.2.50" },
      "association_methods": ["explicit_reference", "observable_match"], "role": "context" }
  ],
  "alternatives": ["..."],
  "unknowns": ["..."]
}
```

- **`confidence`** is ordinal: `alta` > `media` > `baja` > `insuficiente`. How it is computed: [[06 The six phases#Confidence rule]].
- **`confidence_basis`** explains the level in one sentence. Read it first.
- **`correlation_group_alert_ids`** (new): the group this hypothesis was built from. A singleton means the alert was analysed alone.
- **`source_fields`** (new): the exact path and value in the original case. Open the original JSON and check it.
- **`ioc_evidence`** (new): supplied IoC linked to the supporting alerts. Context only; it does not raise confidence.
- **`evidence_against`** does not cancel the hypothesis: it makes it ambiguous and the analyst decides.

## Scope

| List | Means | Does not mean |
| --- | --- | --- |
| `observed_assets` | The host appears in some alert | That it is compromised |
| `suspected_assets` | The host supports a medium- or high-confidence hypothesis | That it is compromised |
| `confirmed_assets` | Always empty | — |
| `suspected_identities` | Users of medium- or high-confidence hypotheses | That the account is stolen |
| `unknowns` | Ambiguous activity, alerts without a host, gaps | — |

## The analyst review

| `review.status` | API `status` | When |
| --- | --- | --- |
| `pending` | `pending_review` | The agent finished and is waiting |
| `validated` | `validated` | The analyst accepts the findings |
| `corrected` | `corrected` | The analyst accepts them with changes (in `notes`) |
| `rejected` | `rejected` | The analyst discards them |

## What the validators guarantee and what they do not

| Guaranteed | Not guaranteed |
| --- | --- |
| All mandatory sections exist | That the hypotheses are right |
| Every cited alert exists in the case | That a technique was not missed (false negatives) |
| Every **new** evidence pointer resolves to the stated value in the original case (traceability check) | That the legacy `observation` text matches a field |
| IoC items were not altered after adaptation | That the provider result is correct |
| Confidence uses the four valid levels | That `related` alerts are one attack |
| Every action needs human approval | That the action is the right one |

> [!example] A report that passes validation can be empty
> In the holdout case (`data/holdout/`), the report is valid and has no hypotheses, although the case describes an attack. See [[10 Limitations]].

Next: [[08 The soc-case-investigator skill]] · Back to [[00 Home]]
