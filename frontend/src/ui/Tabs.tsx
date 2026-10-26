import { type KeyboardEvent, type ReactNode, useRef } from 'react'

export interface Tab {
  id: string
  label: string
  content: ReactNode
}

interface TabsProps {
  label: string
  tabs: Tab[]
  selected: string
  onSelect: (id: string) => void
}

// WAI-ARIA tabs with automatic activation: arrows, Home and End move and select at once.
// On a phone the tab row scrolls sideways inside itself, never the page.
export function Tabs({ label, tabs, selected, onSelect }: TabsProps) {
  const buttons = useRef<(HTMLButtonElement | null)[]>([])
  const current = Math.max(
    0,
    tabs.findIndex((tab) => tab.id === selected),
  )

  function onKeyDown(event: KeyboardEvent) {
    const last = tabs.length - 1
    const next = { ArrowRight: current + 1, ArrowLeft: current - 1, Home: 0, End: last }[event.key]
    if (next === undefined) return
    event.preventDefault()
    const index = next < 0 ? last : next > last ? 0 : next
    onSelect(tabs[index].id)
    buttons.current[index]?.focus()
  }

  return (
    <div>
      <div role="tablist" aria-label={label} onKeyDown={onKeyDown} className="flex gap-6 overflow-x-auto border-b border-rule">
        {tabs.map((tab, index) => {
          const active = index === current
          return (
            <button
              key={tab.id}
              ref={(element) => {
                buttons.current[index] = element
              }}
              type="button"
              role="tab"
              id={`tab-${tab.id}`}
              aria-selected={active}
              aria-controls={`panel-${tab.id}`}
              tabIndex={active ? 0 : -1}
              onClick={() => onSelect(tab.id)}
              className={`-mb-px flex-none whitespace-nowrap border-b-2 py-3 text-sm font-medium ${
                active ? 'border-aligo-blanco text-aligo-blanco' : 'border-transparent text-muted hover:text-aligo-blanco'
              }`}
            >
              {tab.label}
            </button>
          )
        })}
      </div>
      <div role="tabpanel" id={`panel-${tabs[current].id}`} aria-labelledby={`tab-${tabs[current].id}`} tabIndex={0} className="pt-6 focus-visible:outline-offset-4">
        {tabs[current].content}
      </div>
    </div>
  )
}
