import { readFileSync } from 'node:fs'
import { join } from 'node:path'

import { expect, type Page, test } from '@playwright/test'

// The same demo case the README tells people to paste, with a fresh case_id on every run because
// the backend accepts each case_id only once.
const demoPath = join(import.meta.dirname, '../../soc-ai-analyst-sprint2/examples/sprint2_demo.json')

function demoCase() {
  const demo = JSON.parse(readFileSync(demoPath, 'utf8')) as Record<string, unknown>
  demo.case_id = `E2E-${Date.now()}`
  return demo
}

async function signIn(page: Page, name: string) {
  await page.goto('/')
  await page.getByLabel('Your name').fill(name)
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'New case' })).toBeVisible()
}

async function paste(page: Page, json: unknown) {
  await page.getByLabel('Case JSON').fill(JSON.stringify(json, null, 2))
  await page.getByRole('button', { name: 'Submit case' }).click()
}

test('submit, investigate, read and review a case', async ({ page }) => {
  const demo = demoCase()
  await signIn(page, 'E2E Analyst')

  await paste(page, demo)
  await expect(page.getByRole('heading', { name: 'Case accepted' })).toBeVisible()
  await page.getByRole('button', { name: 'Investigate' }).click()

  // The agent runs synchronously, up to the backend's 5 minute limit.
  const tabs = page.getByRole('tablist', { name: 'Report sections' })
  await expect(tabs).toBeVisible({ timeout: 5 * 60_000 })
  await expect(page.getByRole('heading', { level: 1, name: demo.case_id as string })).toBeVisible()

  const panel = page.getByRole('tabpanel')
  await expect(panel.getByRole('heading', { name: /hypothes[ie]s/ })).toBeVisible()
  for (const [tab, heading] of [
    ['Timeline', /event/i],
    ['Evidence', /alert/i],
    ['MITRE ATT&CK', /T\d{4}/],
    ['Affected assets', /asset/i],
  ] as const) {
    await tabs.getByRole('tab', { name: tab }).click()
    await expect(panel.getByRole('heading', { name: heading }).first()).toBeVisible()
  }

  await tabs.getByRole('tab', { name: 'Review' }).click()
  const findings = panel.locator('article:has(fieldset)')
  const count = await findings.count()
  expect(count).toBeGreaterThan(0)
  for (let index = 0; index < count; index++) {
    const finding = findings.nth(index)
    await finding.getByText('Validate', { exact: true }).click()
    await finding.getByRole('textbox', { name: 'Note' }).fill(`Checked finding ${index + 1} against the raw alerts.`)
  }
  await expect(panel.getByText('Suggested from your decisions: Validated.')).toBeVisible()
  await expect(panel.getByRole('textbox', { name: 'Analyst' })).toHaveValue('E2E Analyst')
  await panel.getByRole('button', { name: 'Save review' }).click()

  await expect(panel.getByRole('heading', { name: 'Analyst review' })).toBeVisible()
  await expect(panel.getByText('E2E Analyst')).toBeVisible()
  await expect(panel.getByText(/Checked finding 1 against the raw alerts\./)).toBeVisible()
  // The header strip of report facts, whose last fact is the review status.
  await expect(page.locator('dl').first()).toContainText('Validated')
})

test('recover from a rejected case and from a duplicate', async ({ page }) => {
  const demo = demoCase()
  await signIn(page, 'E2E Analyst')

  const broken = { ...demo }
  delete broken.submitted_at
  await paste(page, broken)
  await expect(page.getByRole('heading', { name: /problems? to fix/ })).toBeVisible()
  await expect(page.getByText('Nothing was stored. Fix these and submit again.')).toBeVisible()

  await paste(page, demo)
  await expect(page.getByRole('heading', { name: 'Case accepted' })).toBeVisible()

  await paste(page, demo)
  await expect(page.getByRole('heading', { name: 'This case was already submitted' })).toBeVisible()
})
