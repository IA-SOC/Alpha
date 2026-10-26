import { useSyncExternalStore } from 'react'

// Fake login for the Alpha: the session is just the analyst's name, kept in this browser.
// Everything reads and writes it through this module, so a real login, local or LDAP, can
// replace the inside of these functions in Beta without touching the screens.
export interface Session {
  analyst: string
}

const storageKey = 'soc.session'
export const maxNameLength = 80
const listeners = new Set<() => void>()

let cached: { raw: string | null; session: Session | null } = { raw: null, session: null }

function read(): string | null {
  try {
    return localStorage.getItem(storageKey)
  } catch {
    return null
  }
}

export function currentSession(): Session | null {
  const raw = read()
  if (raw === cached.raw) return cached.session
  let session: Session | null = null
  try {
    const value = raw ? (JSON.parse(raw) as Partial<Session>) : null
    if (typeof value?.analyst === 'string' && value.analyst.trim()) session = { analyst: value.analyst }
  } catch {
    session = null
  }
  cached = { raw, session }
  return session
}

function notify() {
  listeners.forEach((listener) => listener())
}

export function signIn(name: string): Session {
  const analyst = name.trim().slice(0, maxNameLength)
  if (!analyst) throw new Error('An analyst name is required')
  try {
    localStorage.setItem(storageKey, JSON.stringify({ analyst }))
  } catch {
    // Storage can be blocked. Keep the session in memory for this tab.
    cached = { raw: null, session: { analyst } }
  }
  notify()
  return { analyst }
}

export function signOut() {
  try {
    localStorage.removeItem(storageKey)
  } catch {
    // Nothing stored, nothing to remove.
  }
  cached = { raw: null, session: null }
  notify()
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  // Signing in or out in another tab updates this one too.
  const onStorage = (event: StorageEvent) => event.key === storageKey && listener()
  window.addEventListener('storage', onStorage)
  return () => {
    listeners.delete(listener)
    window.removeEventListener('storage', onStorage)
  }
}

export function useSession(): Session | null {
  return useSyncExternalStore(subscribe, currentSession)
}
