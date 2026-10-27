import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Report } from '../../../api/types'
import { sampleInvestigation } from '../../../test/fixtures'
import {
  clearDraft,
  composeNotes,
  draftAnalyst,
  emptyDraft,
  findingsOf,
  findingsSignature,
  loadDraft,
  type ReviewDraft,
  saveDraft,
  suggestedStatus,
  toDecision,
} from './review'

const report = sampleInvestigation.report
const findings = findingsOf(report)
const [hypothesis, technique] = findings

function decided(...picked: ('validated' | 'corrected' | 'rejected')[]): ReviewDraft {
  const draft = emptyDraft()
  findings.forEach((finding, index) => {
    draft.findings[finding.key] = { decision: picked[index], note: `note ${index + 1}` }
  })
  return draft
}

afterEach(() => {
  vi.restoreAllMocks()
  clearDraft('case-a')
})

describe('Review findings', () => {
  it('takes each hypothesis and each MITRE technique as a finding', () => {
    expect(findings.map((finding) => finding.kind)).toEqual(['hypothesis', 'technique'])
    expect(technique.key).toBe('technique:T1110 Brute Force, Credential Access')
  })

  it('keeps keys apart when the agent repeats a conclusion', () => {
    const twice: Report = { ...report, attack_mapping: [report.attack_mapping[0], report.attack_mapping[0]] }

    expect(findingsOf(twice).map((finding) => finding.key)).toEqual([
      hypothesis.key,
      'technique:T1110 Brute Force, Credential Access',
      'technique:T1110 Brute Force, Credential Access#2',
    ])
  })
})

describe('Suggested outcome', () => {
  it('waits until every finding has a decision', () => {
    expect(suggestedStatus(findings, decided('validated'))).toBeUndefined()
  })

  it('keeps the word when every decision agrees and says corrected for a mix', () => {
    expect(suggestedStatus(findings, decided('validated', 'validated'))).toBe('validated')
    expect(suggestedStatus(findings, decided('rejected', 'rejected'))).toBe('rejected')
    expect(suggestedStatus(findings, decided('validated', 'rejected'))).toBe('corrected')
    expect(suggestedStatus(findings, decided('corrected', 'corrected'))).toBe('corrected')
  })

  it('sends the analyst choice over the suggestion', () => {
    const draft = { ...decided('validated', 'validated'), status: 'rejected' as const, statusFor: findingsSignature(findings) }

    expect(toDecision(findings, draft, '  Ana  ')).toMatchObject({ status: 'rejected', analyst: 'Ana' })
  })

  it('drops the analyst choice when a new run reached other findings', () => {
    const draft = { ...decided('validated', 'validated'), status: 'rejected' as const, statusFor: 'hypothesis:something else' }

    expect(toDecision(findings, draft, 'Ana').status).toBe('validated')
  })
})

describe('Review notes', () => {
  it('writes every finding with its decision and note', () => {
    const draft = { ...decided('validated', 'rejected'), generalNote: ' Escalated to the team lead. ' }

    expect(composeNotes(findings, draft)).toBe(
      [
        'Per finding decisions, sent as one review for the whole report.',
        `Hypothesis 1: ${report.hypotheses[0].statement}\nDecision: validated\nNote: note 1`,
        'MITRE technique: T1110 Brute Force, Credential Access\nDecision: rejected\nNote: note 2',
        'General note: Escalated to the team lead.',
      ].join('\n\n'),
    )
  })

  it('is just the general note when there is nothing to decide', () => {
    expect(composeNotes([], { ...emptyDraft(), generalNote: 'Nothing found.' })).toBe('General note: Nothing found.')
  })
})

describe('Analyst name', () => {
  it('keeps a typed name only for the session it was typed in', () => {
    const draft = { ...emptyDraft(), analyst: 'Night shift lead', analystFor: 'Ana' }

    expect(draftAnalyst(draft, 'Ana')).toBe('Night shift lead')
    expect(draftAnalyst(draft, 'Luis')).toBe('Luis')
  })
})

describe('Review draft', () => {
  it('comes back from storage for the same case only', () => {
    saveDraft('case-a', decided('validated', 'rejected'))

    expect(loadDraft('case-a')).toEqual(decided('validated', 'rejected'))
    expect(loadDraft('case-b')).toEqual(emptyDraft())
  })

  it('starts empty when the stored draft is broken', () => {
    localStorage.setItem('soc.review.case-a', '{not json')

    expect(loadDraft('case-a')).toEqual(emptyDraft())
  })

  it('keeps only the well formed parts of an older or edited draft', () => {
    localStorage.setItem(
      'soc.review.case-a',
      JSON.stringify({
        findings: { a: {}, b: { decision: 'maybe', note: 7 }, c: { decision: 'rejected', note: 'ok' }, d: 'x' },
        generalNote: null,
        status: 'validated',
        analyst: 'Ana',
      }),
    )

    expect(loadDraft('case-a')).toEqual({
      findings: { a: { note: '' }, b: { note: '' }, c: { decision: 'rejected', note: 'ok' } },
      generalNote: '',
    })
  })

  it('stays in memory for this tab when storage is blocked', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    saveDraft('case-a', decided('rejected', 'rejected'))

    expect(loadDraft('case-a')).toEqual(decided('rejected', 'rejected'))
  })
})


describe('Structured finding decisions', () => {
  it('sends each finding key, status and trimmed note separately', () => {
    const result = toDecision(findings, decided('validated', 'rejected'), 'Isabella')
    expect(result.findings).toEqual([
      { finding_key: hypothesis.key, status: 'validated', notes: 'note 1' },
      { finding_key: technique.key, status: 'rejected', notes: 'note 2' },
    ])
  })
})
