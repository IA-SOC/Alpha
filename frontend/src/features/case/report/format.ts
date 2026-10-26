// Report times are ISO strings with an offset. They are shown in UTC, the way the report keeps them.
export function formatUtc(value?: string | null) {
  if (!value) return undefined
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.toISOString().slice(0, 19).replace('T', ' ')} UTC`
}

// A range inside one day drops the repeated date from its end: 2026-10-09 12:00:00 to 12:03:00 UTC.
export function formatUtcRange(start: string, end: string) {
  const from = formatUtc(start)!
  const to = formatUtc(end)!
  const sameDay = from.slice(0, 10) === to.slice(0, 10) && to.endsWith(' UTC')
  return { from: from.replace(/ UTC$/, ''), to: sameDay ? to.slice(11) : to }
}

// Strings print as they are; anything else as compact JSON, so a list reads as ["a","b"].
export function formatValue(value: unknown) {
  return typeof value === 'string' ? value : JSON.stringify(value)
}
