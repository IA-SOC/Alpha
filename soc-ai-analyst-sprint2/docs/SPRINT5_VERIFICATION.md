# Verification — 6 November 2026

- Full backend regression: **510 passed, 2 skipped**, 177.81 seconds.
- Final targeted regression (automatic investigation, chat, explicit retry and benchmark): **44 passed**. This includes the additional large-case MCP context test added after full-suite collection.
- Final chat regression after evidence catalog adjustment: **15 passed**.
- Frontend: **113 passed**; TypeScript check and production build passed; lint passed.
- New backend modules, worker/storage changes, new tests and smoke script: Ruff checks passed. Python compilation and Git whitespace checks passed.
- Two existing opt-in tests were skipped because local prepared Aligo cases and the customer Wazuh ZIP were not supplied to the test environment.
- Gemini review/chat calls were simulated in automated tests. The investigation tests used the real LangGraph and MCP subprocesses. The real Google SDK request construction was also tested with a stubbed client.
- No live Gemini call was made: no credentials were supplied. `scripts/smoke_gemini.py` is the opt-in live connectivity check using synthetic data only.

Run from a Git checkout with the pinned development dependencies. See `SPRINT5_AUTOMATIC_INVESTIGATION_CHAT.md` for configuration and endpoint examples.
