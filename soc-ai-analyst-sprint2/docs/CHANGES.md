# Source change inventory

Paths are relative to the integrated project root. The originals were supplied as
ZIP snapshots; no remote repository was modified. Source ownership follows the
original projects; their test functions and MITRE catalog were retained.

## Modified source/configuration/documentation

- `.github/workflows/tests.yml`
- `.gitignore`
- `README.md`
- `agent/graph.py`
- `agent/investigation.py`
- `agent/normalize.py`
- `agent/render.py`
- `app/main.py`
- `app/storage/case_store.py`
- `docs/SPRINT2_IMPLEMENTATION.md`
- `docs/VERIFICATION.md`
- `requirements.txt`

## Added integration, tests and documentation

- `app/api/routes/investigations.py`
- `app/schemas/investigation.py`
- `app/services/agent_adapter.py`
- `app/services/correlation.py`
- `app/services/evidence.py`
- `app/services/investigation_service.py`
- `app/services/ioc_integration.py`
- `app/services/traceability.py`
- `demo/run_pipeline.py`
- `demo/verify_local.py`
- `docs/AGENT_ORIGINAL.md`
- `docs/BACKLOG_VERIFICATION.md`
- `docs/INTAKE_ORIGINAL.md`
- `examples/sprint2_demo.json`
- `tests/test_correlation_engine.py`
- `tests/test_ioc_integration.py`
- `tests/test_pipeline.py`

## Preserved components

The original intake models, semantic rules, submission route, parser and tests
are unchanged. The original MITRE core, MCP servers/client, report schema, skill
validator and agent tests are unchanged. Agent normalization, graph integration,
IoC consumption and Markdown rendering received focused changes.

`.gitignore` now retains synthetic `data/` for source control and excludes
local database/cache/credential files. The inherited CI installs merged dev
dependencies; its remote Python 3.12/3.14 matrix was not executed here.

Original agent PDF/DOCX/skill-package assets are retained in `docs/legacy/`.
Original READMEs are historical reference copies. Actual execution logs and the
installed environment are under `docs/verification/`; real demo outputs are in
`demo/output/`. The workbook is in `planning/Sprint_Backlog.xlsx` and is also
delivered separately. There is no duplicate runtime backend or agent tree.
