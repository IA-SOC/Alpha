---
tags: [agentsoc, glossary]
aliases: [Glossary, Terms]
updated: 2026-10-11
---

# Glossary

## Security

### SOC
*Security Operations Center.* The team that monitors, investigates and responds to security incidents. **L1** analysts do first-pass alert triage; **L2** analysts investigate in depth.

### Alert
A notice raised by a detection rule (in Elastic, Wazuh, an EDR…) when something matches a suspicious pattern.

### Case
A group of alerts investigated together. It is the system's input. See [[04 Case format]].

### MITRE ATT&CK
A public catalog of attacker behaviors, organized in:
- **Tactics:** the goal, the "why". Example: *Credential Access*.
- **Techniques:** the method, the "how". Example: *T1110 Brute Force*.
- **Sub-techniques:** a more specific variant. Example: *T1558.003 Kerberoasting*.

### IoC
*Indicator of Compromise.* An observable linked to malicious activity: an IP, a domain, a hash, a URL.

### Enrichment
Adding context to an IoC, such as reputation, geolocation or threat lists. In this project the client's N8N flow does it; the system only consumes it.

### Blast radius
The scope of an incident: which hosts, accounts and data are or could be affected. The agent separates observed, suspected and confirmed (see [[07 Reading the report#Scope]]).

### Hypothesis
A candidate explanation of what happened, with evidence for and against. It is not a conclusion.

### Ordinal confidence
A four-level scale (`alta`, `media`, `baja`, `insuficiente`: high, medium, low, insufficient) with a written reason. It is not a probability or a percentage. See [[06 The six phases#Confidence rule]].

### False positive / false negative
- **False positive:** something benign is flagged as an attack.
- **False negative:** a real attack is not detected. The holdout case is a false negative of the current agent.

### Prompt injection
Text hidden in data (an email, a log) that tries to give orders to an AI system. The agent logs it and does not obey it.

## Correlation and evidence (Sprint 2)

### Correlation
Deciding whether two alerts observe the same activity. Here it is based on shared entities and time, never on technique or rule name. See [[16 Correlation engine]].

### Entity family
A group of comparable fields: network, user, host, process, session, artifact. Two IPs count as **one** family, so they cannot double-count.

### Related / uncertain / unrelated
The three pair classifications. `related` needs two shared families within the time window; `unrelated` needs two comparable families with nothing shared; everything else is `uncertain`.

### Noise candidate
An alert whose pairs are all `unrelated`. It is kept and still investigated; "noise" is relative to this case.

### Correlation group
A connected component of `related` pairs. Phase 2 analyses each group separately.

### JSON Pointer
A path into a JSON document, like `/alerts/1/raw_alert/data/srcip` (RFC 6901). Every new piece of evidence carries one into the original submitted case.

### Traceability check
The backend check that every evidence pointer resolves to the stated value in the original case. See [[17 IoC integration and traceability#Traceability check]].

### Explicit reference / observable match
The two ways an IoC is linked to an alert: declared by the submitter in `related_alert_ids`, or found by exact typed value in a security field.

## Formats

### Elastic ECS
*Elastic Common Schema.* Elastic's field schema: `@timestamp`, `event.*`, `host.*`, `user.*`, `source.*`…

### Wazuh
An open detection platform. Its alerts have `rule.*`, `agent.*` and `data.*`.

### Intake contract v1.0
*SOC AI Analyst – Incident Case Input Specification v1.0.* The envelope the API accepts: wrapped alerts with `alert_id`, `source_system` and `raw_alert`. See [[04 Case format]].

### TEST-NET
IP ranges reserved for documentation (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`). Synthetic cases use them so they never point at real IPs.

## Technical

### MCP
*Model Context Protocol.* A standard protocol for exposing tools an agent can call. Here each analysis stage is an MCP server. See [[05 Architecture#Why MCP]].

### LangGraph
A framework to build agents as stateful graphs of steps. Here it runs the six phases. See [[05 Architecture#Why LangGraph]].

### Node
One step of the graph. Each phase is a node.

### Checkpointer
The LangGraph component that stores graph state so it can be paused and resumed. Today it is in memory (`InMemorySaver`).

### `thread_id`
The identifier under which the checkpointer stores a run. In the API it is the `run_id`.

### `interrupt()`
A LangGraph function that stops the graph and waits for external input; here, the analyst decision.

### Skill
A package of instructions and resources (procedure, references, templates, scripts) that defines how an agent does a task. See [[08 The soc-case-investigator skill]].

### LLM
*Large Language Model*, such as Claude. The system does not use one at runtime. See [[11 Where the LLM fits]].

### Backend
The program that receives cases over HTTP, validates, stores, investigates and records the review. See [[15 The backend]].

### Adapter
The backend module that turns an accepted contract case into the agent input, adding correlation and IoC evidence (`app/services/agent_adapter.py`).

### FastAPI
The Python framework the backend is built with. It generates interactive docs at `/docs`.

### API and endpoint
The API is the "service window" other programs use to talk to the backend. Each concrete address, like `POST /api/v1/cases`, is an endpoint.

### UUID
A unique identifier the backend generates for each accepted case, for example `86c5c7bd-571e-42da-920f-8db903cf91d4`.

### Uvicorn worker
A server process. Only one is supported, because review checkpoints live in process memory.

### Rollback
Going back to the previous version of something because the new one failed. Here, reverting `agent/`, `core/` or `servers/` in Git.

### Holdout case
A case that is never used to tune the system and serves to measure it honestly. See [[09 Tests and synthetic cases]].

Back to [[00 Home]]
