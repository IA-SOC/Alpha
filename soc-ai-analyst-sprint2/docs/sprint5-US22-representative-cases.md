# S5-US22-T01 — Representative Wazuh cases (#148)

The local CLI scans a complete NDJSON, gzip or ZIP export and prepares a
reproducible coverage sample in the input v1.0 format. ZIP input uses the
existing `.json.gz` member reader. The existing `build_wazuh_case` adapter
preserves native IDs, raw alerts and supplied VT/MISP objects and produces
provider mapping warnings when necessary.

From the application root, using the existing environment:

```powershell
.\.venv\Scripts\python.exe -m app.services.wazuh_cases D:/Repositorios/wazuh-alerts-2026-08-10_16.zip --output D:/Repositorios/private-data/aligo-148-cases --submitted-at 2026-11-10T00:00:00Z
```

Choose a new output directory for each run. Keep client-derived outputs outside
the repository. The tool preserves the source's anonymization and values.

## Selection and grouping

The default selects up to two alerts per stratum. A stratum consists of the
timestamp's local date, decoder, rule ID and level, Windows channel and event ID,
integration, provider found/error status and file-integrity event type. This
retains rare event types even when frequent types dominate the input. Missing
or invalid timezone-aware timestamps use an explicit `undated` group.

Within each stratum, selection uses the smallest SHA-256 values of a canonical
JSON tuple containing the seed, source member/line and native alert ID. Memory
holds the selected records per stratum. All input records contribute to the
population counts. The algorithm scans through the end of the source.

Selected records are ordered by stratum and selection hash within each date,
then split into cases. `--max-alerts` defaults to 50 and permits 1–50, subject to
the configured intake limit. `--samples-per-stratum` controls coverage depth.
`--seed` defaults to `0`. Identical source bytes and options produce identical
cases and provenance. Changing the seed or selection policy changes case IDs.

These are coverage cases. Group membership does not establish a shared incident,
causal sequence or confirmed attack. Frequencies in the sample differ from the
source population. Source outcomes and analyst labels remain necessary for
accuracy evaluation. Some provider source alerts may fall outside the sample;
the existing adapter records these omissions as warnings.

## Outputs and recovery

- Each `wazuh-*.json` is an intake-compatible case with its original evidence.
- Each `.json.mapping.json` records source member, one-based line, native ID,
  selection hash, stratum ID and JSON Pointer into the case. It also retains
  the adapter's provider mappings and warnings.
- `manifest.json` records the source SHA-256, verified embedded checksums,
  policy, population and selected counts for every stratum, and case filenames.

An embedded `SHA256SUMS` is verified before sampling. A source without embedded
checksums still receives a computed fingerprint. Malformed records, missing
native IDs, repeated IDs in the selected sample and mapping errors fail the run.
Existing outputs are rejected. Cases are built in a temporary sibling directory
and published together after validation. Failed preparation can be retried with
the same destination after correcting the input.

For task #149, use the manifest's `cases[].file` list to load prepared inputs.
Expected investigation outcomes must be supplied separately by the evaluation
owner. The historical `scripts/prepare_client_data.py` and its `client-day-*`
fixtures retain their existing behavior.

## Verification on 2026-11-10

Windows, Python 3.12.2, existing project environment, branch
`feat/148-wazuh-representative-cases`, base `82ff5d9` plus task changes.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_wazuh_cases.py tests/test_wazuh_enrichment.py tests/test_wazuh_enrichment_pipeline.py -q --tb=short
.\.venv\Scripts\python.exe -m ruff check app tests demo/run_pipeline.py demo/verify_local.py --exclude tests/test_agent_graph.py
git diff --check
```

The focused suite passed with **33 passed, 1 skipped**. The existing optional
customer fixture requires separate opt-in. CI-scope Ruff and whitespace checks
passed. Initial sandbox tests could not rename temporary directories on Windows;
the completed test run used approved execution outside the sandbox.

The real CLI scanned all **1,615,054** records in the supplied Aligo archive,
verified **7** embedded checksums, covered **1,491** strata and selected **2,693**
alerts in **58** cases. Every case contains at most **50** alerts. The existing
adapter produced **33** provider enrichments. An independent full-source pass
confirmed every selected raw record and every provider pointer.

A local TestClient verification accepted all **58** cases through the API,
checked retrieval and correlation context, and reopened their stored inputs.
The real local agent processed **2** selected cases covering the 50-alert limit,
VirusTotal and MISP. Both reached pending human review and passed traceability
before and after reopening SQLite. `LLM_PROVIDER` was `none`. The local aggregate
verification is `D:/Repositorios/private-data/aligo-148-verification.json`.

The source archive SHA-256 is
`053a15f605544c4a1d7f3854b1e1d12dde1a4113c47fd357ae1d4dbc4876102c`.
Derived cases and detailed provenance remain in
`D:/Repositorios/private-data/aligo-148-cases/`.

The source README describes consistent pseudonymization and unlabelled alerts.
It also states that pseudonymous public IPs cannot support geolocation or IP
reputation analysis. This preparation preserves those limitations.
