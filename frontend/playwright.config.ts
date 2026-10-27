import { existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import { defineConfig } from '@playwright/test'

// End to end check of the whole Alpha flow against the real backend. It runs on a laptop, not in CI,
// and doubles as the demo check. Servers that are already up get reused, otherwise both start here.
const backend = join(import.meta.dirname, '../soc-ai-analyst-sprint2')

function backendPython() {
  if (process.env.SOC_PYTHON) return process.env.SOC_PYTHON
  const venv = ['.venv/Scripts/python.exe', '.venv/bin/python'].map((path) => join(backend, path))
  return venv.find((path) => existsSync(path)) ?? 'python'
}

export default defineConfig({
  testDir: './e2e',
  // One agent run at a time, like the backend's single worker.
  workers: 1,
  timeout: 6 * 60_000,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    // The Chrome already installed on the laptop, so nothing extra to download.
    channel: 'chrome',
    viewport: { width: 1440, height: 1000 },
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: `"${backendPython()}" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1`,
      cwd: backend,
      url: 'http://127.0.0.1:8000/docs',
      reuseExistingServer: true,
      // A throwaway database, so test cases never land in data/.
      env: { CASE_DATABASE_PATH: join(tmpdir(), `soc-e2e-${Date.now()}.sqlite3`) },
    },
    {
      command: 'npm run dev -- --port 5173 --strictPort',
      url: 'http://localhost:5173',
      reuseExistingServer: true,
    },
  ],
})
