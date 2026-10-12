---
tags: [agentsoc, concepts, beginners]
aliases: [Simple explanation, For beginners, No jargon]
updated: 2026-10-11
---

# Explanation for someone who knows nothing about the topic

This note assumes no security or programming knowledge.

## The problem

Companies run programs that watch their computers and networks, like a camera system. Whenever they see something odd, they raise a **notice** (an *alert*). That could be someone trying many passwords, a strange file, or a connection to a suspicious site.

Those notices go to a team of people called the **SOC** (security operations center). The problem: there are **a lot** of them, most are false alarms, and checking each one by hand takes a long time.

## The solution we built

A system with three roles, like a hospital:

| Role | Analogy | What it does |
| --- | --- | --- |
| **Backend** | The hospital **front desk** | Receives the patient (the case) and checks that the paperwork is complete. It gives the case a file number, stores the record and prepares the file for the specialist. |
| **Agent** | The **specialist doctor** | Examines the case, works out what may have happened and writes a report with a diagnosis. |
| **Analyst** | The **head doctor** | Reads the report and decides: it is right, it needs correcting, or it is wrong. The last word always belongs to a person. |

## What happens to a case, step by step

1. Someone sends a group of related notices (a **case**).
2. **The front desk (backend)** checks that it is complete and well written. If something is missing, it rejects the case and says what is missing. If it is fine, it gives it a unique number and stores it.
3. When asked to investigate, the front desk first **sorts the papers**:
   - It checks which notices are about the same thing: the same computer, the same person and the same address, a few minutes apart. Those go together in one pile. A notice that matches nothing is marked "probably unrelated", but it is **not thrown away**.
   - It attaches any lab results the case already brought (known bad addresses or files), noting for each one whether the sender said "this belongs to notice X" or whether the value was actually found in the notice.
4. **The specialist (agent)** investigates each pile in six steps. It compares the notices with a worldwide catalog of attack techniques (**MITRE ATT&CK**), builds a timeline, sees which computers and people are involved, and writes a report.
5. Two **automatic reviewers** check the report. One checks that it is well formed. The other checks that every piece of evidence really says what the report claims, by going back to the original papers. If either fails, nobody sees the report as valid.
6. The report is stored in the file. The **analyst** reads it and records a decision.

## Why sort into piles first?

Imagine two patients who each have a cough. Before Sprint 2, the specialist could see "two coughs" and conclude "an epidemic, medium certainty". Now the front desk first checks whether the two coughs are even from the same household. If they are not, the specialist looks at each one separately: "one cough, low certainty" twice. **Unrelated notices can no longer make each other look more serious.**

## What changed in this version

Before, the front desk and the specialist worked in **two separate buildings**: the front desk sent each case over by courier and waited. Now they work **in the same building**. That means one installation instead of two and no courier trip, plus the new sorting step. The cost: if the specialist has a serious problem, the whole building feels it. There are more details in [[19 Changes from the previous version]].

## What the system does NOT do

- **It does not make final decisions.** It only proposes; a person decides.
- **It does not block or shut down anything** on its own.
- **It is not an AI that "thinks"** like ChatGPT. Today it reasons with fixed rules, like a checklist. That makes it predictable, but it can miss an attack described with other words. See [[10 Limitations]].
- **"Related" does not mean "attack".** It only means the notices share the same computer, person or address.
- **It works with test data**, not real customer data.

## Words you will see

| Word | Simple meaning |
| --- | --- |
| Alert | A notice that something odd happened |
| Case | A group of alerts sent together |
| SOC | The team of people who review alerts |
| Backend | The program that receives, checks, sorts and stores (the front desk) |
| Agent | The program that investigates (the specialist) |
| Correlation | Checking which alerts are about the same thing (sorting into piles) |
| Noise | Alerts that do not seem connected to the rest |
| API | The "service window" other programs use to talk to the backend |
| MITRE ATT&CK | A public catalog of the techniques attackers use |
| IoC | A concrete clue: an IP address, a website, a suspicious file |

More terms in [[14 Glossary]].

## To go further

- The agent in more detail: [[01 What the agent is]]
- The front desk inside: [[15 The backend]]
- How the piles are made: [[16 Correlation engine]]

Back to [[00 Home]]
