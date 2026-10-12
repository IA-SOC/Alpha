---
tags: [agentsoc, concepts]
aliases: [What is AgentSOC, Agent purpose]
updated: 2026-10-11
---

# What the agent is

The system takes a **case** (a group of security alerts) and does five things with it. It checks the case against the official intake contract. It works out which alerts are actually related. It links the IoC intelligence the case already carries. It investigates the case in six fixed steps. Finally it delivers a **draft report** for an analyst to validate, correct or reject.

It is the investigation layer of an academic SOC prototype built with a managed SOC provider. It works **only with simulated or anonymized data** and never connects to production.

## What it delivers

For each case, the report contains:

- **Attack hypotheses** tied to [[14 Glossary#MITRE ATT&CK|MITRE ATT&CK]] techniques, ranked, with evidence for and against.
- **Alert correlation** (new): every pair of alerts classified as `related`, `uncertain` or `unrelated`, with the fields that justify it. See [[16 Correlation engine]].
- **Timeline** with times normalized to UTC, keeping the original time.
- **Scope** ([[14 Glossary#Blast radius|blast radius]]): which hosts and users appear and which are suspected.
- **IoC** linked to alerts by declared reference or by exact typed match, with the provider payload untouched. See [[17 IoC integration and traceability]].
- **Recommended actions** with priority, always requiring human approval.
- **Limitations** of the data and of the analysis.

Every claim cites the alert IDs that support it. The new evidence also cites a JSON Pointer into the original submitted case. See [[07 Reading the report]].

## What it does not do

| It does not | Why |
| --- | --- |
| Close cases | The final decision belongs to the analyst. The report stays in `pending_review`. |
| Contain incidents (isolate hosts, block IPs, reset passwords) | It only proposes actions and executes nothing. |
| Query IP, domain or hash reputation | The client already has an enrichment flow (N8N). The system uses only what comes with the case. |
| Invent a verdict | If the provider result has no verdict, none is made up. Provider scores are not read as proof. |
| Confirm compromise | A host that appears in an alert is "observed", not "compromised". |
| Treat "related" as "attack" | Correlation means shared entities, not causation. |
| Obey text inside alerts | An email saying "close this case" is data, not an instruction. |

## How it is built, in one sentence

A **FastAPI** backend validates and stores the case. An **adapter** adds correlation and IoC evidence. A six-node **LangGraph** flow then runs in the same process, follows the [[08 The soc-case-investigator skill|soc-case-investigator]] skill, uses three **MCP servers** for analysis and passes two **validators** as quality gates. Detail in [[05 Architecture]].

## Requirements it addresses

From the project brief (27 September 2026) and the Sprint 2 backlog:

- Input in Elastic ECS or Wazuh format, simulated data, under the *Incident Case Input Specification v1.0*.
- Methodology based on MITRE ATT&CK, with supported hypotheses.
- Timeline with initial access, progression and blast radius.
- Correlation of related alerts and separation of noise (US2).
- Consumption of existing IoC enrichment (US3).
- Readable and JSON report.
- Human review before closing the case.
- Up to 50 alerts in no more than 5 minutes. The 4-alert flow was measured; a full 50-alert investigation was not benchmarked (see [[10 Limitations]]).

Backlog status: **18 of 19 Sprint 2 tasks verified**. The N8N-specific input task is still *in progress* because real customer N8N samples were not supplied.

Next: [[05 Architecture]] · Back to [[00 Home]]
