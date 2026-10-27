import type { Correlation, TimelineEntry } from '../../../api/types'
import { parseUtc } from './format'

const dated = (entry: TimelineEntry) => !!entry.timestamp_utc && !Number.isNaN(parseUtc(entry.timestamp_utc))

// Noise is alerts the correlation found unrelated to everything else in the case. They stay on
// screen, just out of the chronology, so they do not read as steps of the same story.
export function splitTimeline(timeline: TimelineEntry[], correlation: Correlation) {
  const noise = new Set(correlation.noise_alert_ids)
  const isNoise = (entry: TimelineEntry) => entry.alert_ids.length > 0 && entry.alert_ids.every((id) => noise.has(id))
  const byTime = (a: TimelineEntry, b: TimelineEntry) => parseUtc(a.timestamp_utc!) - parseUtc(b.timestamp_utc!)
  return {
    story: timeline.filter((entry) => dated(entry) && !isNoise(entry)).sort(byTime),
    noise: timeline.filter((entry) => dated(entry) && isNoise(entry)).sort(byTime),
    undated: timeline.filter((entry) => !dated(entry)),
  }
}
