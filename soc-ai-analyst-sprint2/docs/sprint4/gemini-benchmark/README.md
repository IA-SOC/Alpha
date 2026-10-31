# Gemini comparison v1.0 — #68

**2026-10-31. Live comparison is inconclusive:** four bounded authenticated
generation attempts returned errors, without usable output or usage metadata.
No Gemini quality advantage, token count, actual charge or cost-per-case result
is claimed. The benchmark and offline comparison are implemented; #68 remains
open pending usable live results and assigned-owner review.

## What is compared

The current [adapter](../../../agent/llm.py) is a second-opinion reviewer, not an
independent investigation agent. [The harness](../../../benchmarks/gemini_compare.py)
times the complete deterministic graph, validates its report and source fields,
then separately times one reviewer call over the existing reduced/sanitized
`build_model_context`. It does not replace hypotheses, confidence, MITRE mappings,
actions or human review. Incremental reviewer latency is not full-agent latency;
adding the two is only a serial latency estimate, not a measured augmented run.

Only four registered synthetic fixtures can run: phishing, brute force with
lateral movement, exfiltration and pre-ransomware. The files are reused from
`data/synthetic/`, never copied from customer data. Results contain fixture/context
hashes, code revisions, metrics and accepted assessment vocabulary. They exclude
raw cases, provider prose, exception messages, request headers and credentials.

| Axis | Metric and interpretation |
| --- | --- |
| Schema validity | Existing full-report validator for baseline; strict reviewer schema and existing output guard for model responses |
| Evidence quality | Baseline cited values resolve into original synthetic fields; reviewer ranks and citations must be allowed **and actually sent**, with no duplicate/missing hypothesis assessments |
| Catalog regression | Baseline technique set equals the existing four-scenario expected catalog sets; this tests regression, not analyst-adjudicated accuracy |
| Timing | Wall-clock milliseconds for local full graph and separately for incremental reviewer/validation; one sample, sequential, no percentile or throughput claim |
| Tokens | SDK prompt, candidate, thinking, cached-input and total counts; missing required usage stays unknown rather than zero |
| Cost | Uncached input + discounted cached input + candidate **and thinking** output tokens, using a named/dated standard paid-tier snapshot; local compute, discounts and invoice/free-tier status excluded |

Field-check counts include repeated citations in canonical and audience views.
These metrics cannot prove narrative entailment, attack truth, calibration or
generalization. A structurally valid/cited explanation may still be wrong.
Reduced contexts omit non-supporting alerts and cap/truncate selected fields;
model quality outside that context is not evaluated. Four scenario families and
one run do not establish model superiority. No standalone Gemini report generator
or new provider/model default is introduced.

## Actual results

Environment: Windows/Python 3.12.2, MCP 2.3.0, LangGraph 1.2.16,
google-genai 2.33.0. The latter was already pinned in `requirements.txt` but missing
locally; it was installed for this task. `pip check` passed. No dependency file
changes. Baseline requests run with `LLM_PROVIDER=none` and no Gemini key in the
environment passed to local MCP startup.

### Offline run, code `f094235`

[offline.json](offline.json): four full deterministic reports valid, all four
catalog expectations matched, zero cited-field value errors. Local graph times
were 3901.782, 3825.905, 3908.059 and 3847.133 ms respectively. Offline mock schema
and citation/coverage checks passed for all cases. Mock latency and its zero API
usage/cost are **not Gemini measurements**. Baseline external API tokens/cost are
zero; machine/hosting costs are not estimated. This run overlapped the regression
suite, so its timings are smoke measurements rather than isolated benchmarks.

### Real authenticated attempts: four generations total, two metadata lookups

| Saved record | Model / synthetic case | Outcome | Reviewer latency | Tokens / cost |
| --- | --- | --- | --- | --- |
| [First attempt](live-first-attempt.json), `fec0957` | Gemini 3.8 Flash / phishing | SDK ServerError; HTTP status was not captured in this first version | 8670.359 ms | Not returned / unknown |
| [Second attempt](live-second-attempt.json), `1c55895` | Gemini 3.8 Flash / phishing | HTTP 504 | 30077.143 ms | Not returned / unknown |
| [Explicit fallback](live-fallback.json), `549c2d3` | Gemini 2.5 Flash / phishing | HTTP 404 | 1198.981 ms | Not returned / unknown |
| [Final attempt](live-final-attempt.json), `b1c2b87` | Gemini 2.5 Flash Lite / brute force | HTTP 404 | 1437.358 ms | Not returned / unknown |

Every invocation stopped after its first error; subsequent rows explicitly say
`not_executed_after_error`. Four is the **actual combined generation count**, not
the sum of each file's allowed maximum. No SDK retries: `attempts=1` includes the
initial request. The first two requests used low thinking; 2.5 fallbacks used a
zero thinking budget. Each had a 2048 output-token cap and 30-second timeout.

Two separate metadata-only official API checks succeeded: get-model for 2.5
Flash, then the first model-list page advertised 2.5 Flash and Flash Lite with
`generateContent`. Neither generated text. Metadata availability did not establish
generation availability; the 404 discrepancy remains unresolved. A mock HTTP
transport check confirmed the SDK route
`/v1beta/models/gemini-2.5-flash:generateContent` without making a real request.
No further remote attempts were made. Successful Gemini schema, evidence quality,
token usage and cost therefore remain **unmeasured**, not failed quality scores or
zero-cost results. Check service/model/account availability before a bounded rerun.

### Pricing snapshot and accounting

[Official Gemini Developer API pricing](https://ai.google.dev/gemini-api/docs/pricing),
checked 2026-10-31; standard text requests, USD per million tokens:

| Model | Input | Cached input | Output including thinking |
| --- | ---: | ---: | ---: |
| Gemini 3.8 Flash | 0.75 | 0.075 | 3.75 |
| Gemini 2.5 Flash | 0.30 | 0.03 | 2.50 |
| Gemini 2.5 Flash Lite | 0.10 | 0.01 | 0.40 |

The 3.8 introductory rates expire after 2026-12-31. Snapshots are explicit inputs
to accounting, not a promise of future pricing. Refresh rates before later runs.
No grounding, tools, explicit caching or batch API was used. Output estimates
include thinking even if it is not visible to the user. Actual billing/tier is
unknown; failed requests returned no usage, so **total incurred cost is unknown**.

## Reproduce securely

From `soc-ai-analyst-sprint2/` using the existing dev environment:

```powershell
# Offline default: does not read credentials or call Gemini.
.\.venv\Scripts\python.exe -m benchmarks.gemini_compare --output docs/sprint4/gemini-benchmark/offline.json
# Opt-in live example: one registered synthetic case, official API only.
.\.venv\Scripts\python.exe -m benchmarks.gemini_compare --live --key-file D:/Repositorios/gemini_key.txt --model gemini-2.5-flash --cases phishing_ecs --output docs/sprint4/gemini-benchmark/new-live-run.json
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m ruff check app tests demo/run_pipeline.py demo/verify_local.py --exclude tests/test_agent_graph.py
.\.venv\Scripts\python.exe -m ruff check benchmarks --select E,F,I
.\.venv\Scripts\python.exe -m ruff check agent/llm.py --select F
```

Use new result filenames to retain previous evidence. `--model` is explicit;
the harness does not silently switch models. No `--live` means `offline_mock`,
even if a key is present. Live mode requires a credential file outside the
repository; it reads the file directly and scopes `GEMINI_API_KEY` to the provider
call, then restores the environment. It refuses to overwrite that file or persist
a result containing the credential. The original key file was never written,
modified, deleted, displayed or committed. The SDK endpoint is pinned to the
official Developer API, with Vertex mode disabled. Exceptions retain only class
and integer HTTP status. Do not pass arbitrary input/customer files: the CLI
accepts registered synthetic case names only.

The four recorded live invocations used the case/model/output combinations in
the table; first attempt had all four names, second had phishing/brute force/
pre-ransomware, fallback had phishing/brute force, and final had brute force only.
Stops explain why only one generation occurred per invocation.

## Verification and acceptance

[test_gemini_benchmark.py](../../../tests/test_gemini_benchmark.py) adds offline
tests for schema/coverage/citation failures, usage/cached/thinking accounting,
model-specific rates, client cleanup, official endpoint/budgets, first-error stop,
key scoping/restoration, external-file requirement, overwrite prevention and
credential-output suppression. Existing LLM fallback and report-contract tests
are reused. Two initial fake reports lacked `hypotheses`; those test fixtures
were corrected. Focused LLM/report/benchmark run: **92 passed** before the final
three security/accounting tests. Final full suite at `f094235`:
**447 passed, 2 skipped in 231.62 seconds**. The skips require opt-in local customer
data; neither was run. Exact CI lint, benchmark E/F/I lint, provider F checks,
dependency consistency and local document links passed. A local exact-match
credential scan checked 327 project files and all new commit patches: no match.
The scan emitted booleans/counts only, never credential text or a fingerprint.

Recommendation: retain the deterministic default. Restore/confirm working
generation access and repeat a small, explicitly approved synthetic comparison
before choosing a model; these error latencies are not model speed/quality scores.

[#68](https://github.com/IA-SOC/Alpha/issues/68) / US17 depends on
[#75](https://github.com/IA-SOC/Alpha/issues/75)'s optional adapter. Existing default
report behavior remains deterministic. The harness supplies reproducible
comparison and honest failure evidence; successful live measurement and owner
review/demo remain outstanding, so this PR does not close #68. Codex assisted
implementation and execution; actual human effort/accepted edits remain for the
owner to record. No customer-data run or remote customer-data approval is implied.
