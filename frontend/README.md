# SOC AI Analyst frontend

Web UI for the Alpha. An analyst submits a case, runs the investigation, reads the report and records a review. It talks to the backend in `../soc-ai-analyst-sprint2/` through the Vite dev proxy, so there is no CORS setup and no Docker.

Stack: React, TypeScript, Vite, TanStack Query, React Router, react-i18next and Tailwind. Colors, font and logo follow the Aligo brand kit.

## What you need

- Python 3.12 for the backend
- Node.js 22.22 or newer for the frontend. Node 24 LTS is what CI uses
- Git

Check with `python --version` and `node --version`.

## Run it on your laptop

You need two terminals, one for the backend and one for the frontend. Start from the root of the Alpha repo.

### 1. Backend

macOS or Linux:

```bash
cd soc-ai-analyst-sprint2
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Windows PowerShell:

```powershell
cd soc-ai-analyst-sprint2
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

If PowerShell refuses to run `Activate.ps1`, run `Set-ExecutionPolicy -Scope Process Bypass` in that terminal first.

The backend is up when http://127.0.0.1:8000/docs opens. You only need the venv and pip steps the first time.

### 2. Frontend

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. Requests to `/api` go to the backend on port 8000. If your backend runs somewhere else, set `SOC_API_URL` before `npm run dev`, for example `SOC_API_URL=http://127.0.0.1:9000 npm run dev`, or `$env:SOC_API_URL="http://127.0.0.1:9000"; npm run dev` on PowerShell.

`npm ci` is only needed the first time and whenever `package-lock.json` changes.

### 3. Try it

Paste or upload `soc-ai-analyst-sprint2/examples/sprint2_demo.json` on the New Case page. Each case ID can only be accepted once, so change `case_id` in the JSON to submit it again.

## Checks

These are the same checks CI runs on every pull request that touches `frontend/`.

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

`npm run test:watch` keeps Vitest running while you work.

## Troubleshooting

- **Port 5173 or 8000 is busy.** Stop the other process or start Vite with `npm run dev -- --port 5174`. For another backend port, see `SOC_API_URL` above.
- **The UI says it can't reach the server.** The backend terminal is probably stopped. Start it again with the uvicorn command.
- **`npm ci` fails on Node version.** Install Node 22.22 or newer, then run it again.
