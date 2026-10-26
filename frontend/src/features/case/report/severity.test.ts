import { describe, expect, it } from 'vitest'

import { sampleCase } from '../../../test/fixtures'
import { originalSeverity } from './severity'

describe('originalSeverity', () => {
  it('takes the Wazuh rule level with its field', () => {
    expect(originalSeverity(sampleCase.alerts[1].raw_alert)).toEqual({ field: 'rule.level', value: 8 })
  })

  it('reads Elastic severities nested or as flat dotted keys', () => {
    expect(originalSeverity({ kibana: { alert: { severity: 'high' } } })).toEqual({ field: 'kibana.alert.severity', value: 'high' })
    expect(originalSeverity({ 'kibana.alert.severity': 'low' })).toEqual({ field: 'kibana.alert.severity', value: 'low' })
    expect(originalSeverity({ event: { severity: 47 } })).toEqual({ field: 'event.severity', value: 47 })
  })

  it('looks inside the _source of an Elastic search hit', () => {
    expect(originalSeverity({ _index: 'alerts', _source: { 'kibana.alert.severity': 'high' } })).toEqual({
      field: '_source.kibana.alert.severity',
      value: 'high',
    })
  })

  it('gives nothing when the alert carries no severity', () => {
    expect(originalSeverity(sampleCase.alerts[0].raw_alert)).toBeUndefined()
    expect(originalSeverity({ rule: { level: null } })).toBeUndefined()
  })
})
