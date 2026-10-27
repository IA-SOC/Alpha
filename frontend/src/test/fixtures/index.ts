// Real outputs of `python demo/verify_local.py` in soc-ai-analyst-sprint2, frozen on 26 Oct 2026.
// Refresh them by running that demo again and copying demo/output/investigation.json and
// demo/output/submitted_case.json here.
import type { IncidentCase, Investigation } from '../../api/types'
import investigation from './investigation.sample.json'
import submittedCase from './submitted-case.sample.json'

export const sampleInvestigation = investigation as unknown as Investigation
export const sampleCase = submittedCase as unknown as IncidentCase
