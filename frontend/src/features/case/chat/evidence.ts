import type { TFunction } from 'i18next'

import type { ChatEvidenceItem } from '../../../api/types'

export type RefGroup = 'alert' | 'hypotheses' | 'timeline' | 'attack_mapping' | 'ioc'

export const refGroups: RefGroup[] = ['alert', 'hypotheses', 'timeline', 'attack_mapping', 'ioc']

export interface RefInfo {
  key: string
  group?: RefGroup
  label: string
  alertId?: string
  // A key from an earlier run, or one the backend no longer lists. Gemini saw it, but it is gone.
  stale: boolean
  item?: ChatEvidenceItem
}

const text = (value: unknown) => (typeof value === 'string' && value.trim() ? value : undefined)

// "alert:<id>" or "mcp:<run_id>:<section>:<index>", as app/services/chat_service.py builds them.
export function parseRef(key: string): { group?: RefGroup; alertId?: string; runId?: string; index?: number } {
  if (key.startsWith('alert:')) return { group: 'alert', alertId: key.slice('alert:'.length) }
  const match = /^mcp:([^:]+):(hypotheses|timeline|attack_mapping|ioc):(\d+)$/.exec(key)
  if (!match) return {}
  return { group: match[2] as RefGroup, runId: match[1], index: Number(match[3]) }
}

// A short name an analyst can recognise, taken from the item itself where it has one.
export function describeRef(
  key: string,
  catalog: Record<string, ChatEvidenceItem> | undefined,
  runId: string,
  t: TFunction,
): RefInfo {
  const parsed = parseRef(key)
  const item = catalog?.[key]
  const data = (item?.data ?? {}) as Record<string, unknown>
  const stale = (parsed.runId !== undefined && parsed.runId !== runId) || (catalog !== undefined && !item)
  const number = (parsed.index ?? 0) + 1
  let label: string

  switch (parsed.group) {
    case 'alert':
      label = t('chat.ref.alert', { id: parsed.alertId })
      break
    case 'hypotheses': {
      const statement = text(data.statement)
      label = t('chat.ref.hypothesis', { rank: typeof data.rank === 'number' ? data.rank : number })
      if (statement) label = `${label}: ${statement}`
      break
    }
    case 'timeline': {
      const description = text(data.description)
      label = t('chat.ref.event', { number })
      if (description) label = `${label}: ${description}`
      break
    }
    case 'attack_mapping': {
      const name = [text(data.technique_id), text(data.technique_name)].filter(Boolean).join(' ')
      label = name ? t('chat.ref.technique', { name }) : t('chat.ref.techniqueNumber', { number })
      break
    }
    case 'ioc': {
      const observable = data.observable as { value?: unknown } | undefined
      const value = text(observable?.value)
      label = value ? t('chat.ref.ioc', { value }) : t('chat.ref.iocNumber', { number })
      break
    }
    default:
      label = key
  }

  return { key, group: parsed.group, label, alertId: parsed.alertId, stale, item }
}
