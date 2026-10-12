---
tags: [agentsoc, index]
aliases: [AgentSOC, AgentSOC Index, Home]
updated: 2026-10-11
---

# AgentSOC — SOC investigation agent documentation (Sprint 2)

This folder explains what the integrated Sprint 2 system is, how to run it, how it works inside and how to improve it.

> [!info] Where the code is
> `soc-ai-analyst-sprint2/` (the folder next to this one). Every command in these notes runs from there, with the virtual environment active.

> [!warning] Read this first
> The agent **does not call a language model** at runtime: it reasons with keyword rules. The same case always gives the same report, and an attack described with other words goes undetected. See [[10 Limitations]] and [[11 Where the LLM fits]].

> [!tip] What is new in Sprint 2
> Backend and agent now live in **one project and one process**, and two new stages run before the agent: **alert correlation** and **IoC integration**. Every new piece of evidence points back to the original JSON. Summary in [[19 Changes from the previous version]].

## Reading paths

**If you know nothing about the topic (5 minutes)**
1. [[18 Explanation for beginners]]

**To understand it (15 minutes)**
1. [[01 What the agent is]]: purpose and scope.
2. [[05 Architecture]]: the pieces and how they connect.
3. [[06 The six phases]]: what happens at each step.

**To use it**
1. [[02 Installation]]
2. [[03 Daily use]]: commands and API calls.
3. [[04 Case format]]: how to prepare the input.
4. [[07 Reading the report]]: how to interpret the output.

**Sprint 2 additions**
1. [[15 The backend]]: the API that receives, validates, investigates and records the review.
2. [[16 Correlation engine]]: related, uncertain and unrelated alerts.
3. [[17 IoC integration and traceability]]: supplied intelligence and evidence pointers.

**To improve it**
1. [[10 Limitations]]: what fails today and why.
2. [[12 Improving the agent]]: step-by-step guides.
3. [[09 Tests and synthetic cases]]: how to check you broke nothing.

## All notes

| Note | What it covers |
| --- | --- |
| [[01 What the agent is]] | Purpose, scope and limits |
| [[02 Installation]] | Virtual environment, dependencies, VS Code |
| [[03 Daily use]] | Commands, API calls, demo, tests |
| [[04 Case format]] | Intake contract v1.0 and the legacy direct format |
| [[05 Architecture]] | FastAPI, adapter, LangGraph, MCP servers, validators |
| [[06 The six phases]] | Each graph node in detail |
| [[07 Reading the report]] | Report fields and what they mean |
| [[08 The soc-case-investigator skill]] | The procedure that governs the agent |
| [[09 Tests and synthetic cases]] | 184 tests, synthetic cases, real HTTP demo |
| [[10 Limitations]] | What it does not detect and why |
| [[11 Where the LLM fits]] | Current and future role of a language model |
| [[12 Improving the agent]] | Index of improvement guides |
| [[13 Troubleshooting]] | Common errors |
| [[14 Glossary]] | SOC and technical terms |
| [[15 The backend]] | Endpoints, persistence, failures, configuration |
| [[16 Correlation engine]] | Pairwise correlation rules R1–R4 |
| [[17 IoC integration and traceability]] | IoC associations and evidence verification |
| [[18 Explanation for beginners]] | The whole system without jargon |
| [[19 Changes from the previous version]] | What Sprint 2 optimized, added and dropped |
