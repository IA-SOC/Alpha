import { parseUtc } from '../case/report/format'

// 2026-11-10 14:03, in UTC like every other time on screen. The unit sits in the column header.
export function formatCreated(value: string) {
  const time = parseUtc(value)
  if (Number.isNaN(time)) return value
  return new Date(time).toISOString().slice(0, 16).replace('T', ' ')
}
