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

Since Sprint 5 the backend investigates every accepted case on its own and asks Gemini for a second opinion, so it needs a Gemini API key. The key goes in a `.env` file that git ignores. Never commit it.

The app doesn't read `.env` by itself. You load it into the terminal before starting uvicorn, every time you open a new terminal. If you skip that, the backend still starts and the report still shows up, but Gemini's second opinion shows an error and the Chat tab can't answer.

macOS or Linux, the first time:

```bash
cd soc-ai-analyst-sprint2
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
```

Open `.env` and paste your key after `GEMINI_API_KEY=`. Then, every time:

```bash
cd soc-ai-analyst-sprint2
source .venv/bin/activate
set -a; source .env; set +a
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Windows PowerShell, the first time:

```powershell
cd soc-ai-analyst-sprint2
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Open `.env` and paste your key after `GEMINI_API_KEY=`. Then, every time:

```powershell
cd soc-ai-analyst-sprint2
.venv\Scripts\Activate.ps1
Get-Content .env | Where-Object { $_ -match '^\s*[^#\s][^=]*=' } | ForEach-Object { $name, $value = $_ -split '=', 2; Set-Item "env:$($name.Trim())" $value.Trim() }
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

If PowerShell refuses to run `Activate.ps1`, run `Set-ExecutionPolicy -Scope Process Bypass` in that terminal first.

The backend is up when http://127.0.0.1:8000/docs opens. Cases are stored in `data/`, so they are still there after a restart.

No key at hand? Start it with `SOC_AUTO_INVESTIGATE=false`, or `$env:SOC_AUTO_INVESTIGATE="false"` on PowerShell. Cases then wait until you press Investigate and the report comes out without Gemini.

### 2. Frontend

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. Requests to `/api` go to the backend on port 8000. If your backend runs somewhere else, set `SOC_API_URL` before `npm run dev`, for example `SOC_API_URL=http://127.0.0.1:9000 npm run dev`, or `$env:SOC_API_URL="http://127.0.0.1:9000"; npm run dev` on PowerShell.

`npm ci` is only needed the first time and whenever `package-lock.json` changes.

### 3. Try it

The first screen asks for your name. That's a fake login for the Alpha: no password, and the name only lives in your browser so it can go on your reviews. `src/session/session.ts` is the one place a real login plugs in later.

Paste or upload `soc-ai-analyst-sprint2/examples/sprint2_demo.json` on the New Case page. Each case ID can only be accepted once, so change `case_id` in the JSON to submit it again.

The backend starts investigating as soon as the case is accepted. Press Investigate to open the report: it waits for that run to finish, which can take a few minutes. The report opens on the Agent analysis tab with Gemini's second opinion, and the Chat tab lets you ask Gemini about the case.

## Checks

These are the same checks CI runs on every pull request that touches `frontend/`.

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

`npm run test:watch` keeps Vitest running while you work.

## End to end check

`npm run e2e` runs the whole flow in Chrome against the real backend: sign in, submit the demo case, investigate, open every report tab and save a review. A second test checks that a rejected case and a duplicate are explained. It's also the check to run before a demo.

It uses the Chrome installed on your laptop, so there's no browser to download. If the backend and `npm run dev` are already running it uses them. If not, it starts both, with the backend on a throwaway database so test cases never end up in `data/`. Set up the backend venv first, as in step 1. `SOC_PYTHON` works here too. A backend started this way only gets your Gemini key if you loaded `.env` in that terminal first, otherwise Gemini shows an error there. The test accepts that, it only checks that the screens work.

It runs locally only. CI keeps to lint, typecheck, Vitest and the build.

## Types from the backend

Everything in `src/api/generated/` comes from the backend: the OpenAPI document of the intake API, the investigation report schema in `skills/soc-case-investigator/references/report-schema.json` and the correlation models. Don't edit those files by hand. When any of that changes in the backend, regenerate them and commit the result:

```bash
npm run gen:types
```

The script runs Python inside `../soc-ai-analyst-sprint2/.venv`, so set up the backend first. Point `SOC_PYTHON` at another interpreter if you keep the venv elsewhere.

`src/test/fixtures/` holds a real investigation from `python demo/verify_local.py`, frozen so tests and screens have a stable sample. The comment in `src/test/fixtures/index.ts` says how to refresh it.

## Troubleshooting

- **Port 5173 or 8000 is busy.** Often it's an old Vite or uvicorn left running, for example by an interrupted `npm run e2e`. Stop it, or just open the address `npm run dev` prints, since Vite moves to 5174 on its own. For another backend port, see `SOC_API_URL` above.
- **The UI says it can't reach the backend.** The backend terminal is probably stopped. Start it again with the uvicorn command and press Try again.
- **Gemini's second opinion shows an error or the chat says Gemini failed.** If the error mentions `GEMINI_API_KEY`, the `.env` wasn't loaded in that terminal. Load it as in step 1 and restart uvicorn. If it says `504 DEADLINE_EXCEEDED`, Gemini took too long on Google's side. Try again later or set another model in `GEMINI_MODEL`. Then press Investigate again on the Review tab to ask Gemini again.
- **`npm ci` fails on Node version.** Install Node 22.22 or newer, then run it again.
- **`npm ci` fails with `EPERM` on Windows.** A running `npm run dev` keeps files in `node_modules` open. Stop it first.
