import { type FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useLocation, useNavigate } from 'react-router'

import { maxNameLength, signIn, useSession } from './session'

export function EntryPage() {
  const { t } = useTranslation()
  const session = useSession()
  const navigate = useNavigate()
  const location = useLocation()
  const [name, setName] = useState('')
  const [missing, setMissing] = useState(false)
  const next = (location.state as { from?: string } | null)?.from ?? '/cases/new'

  if (session) return <Navigate to={next} replace />

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (!name.trim()) return setMissing(true)
    signIn(name)
    navigate(next, { replace: true })
  }

  return (
    // Centred in the free height: the entry screen is the app's one deliberate rest.
    <section className="mx-auto flex min-h-[calc(100dvh-12rem)] max-w-md flex-col justify-center pb-10">
      <h1 className="text-2xl">{t('entry.title')}</h1>
      <p className="mt-1 text-[15px] text-muted">{t('entry.body')}</p>
      <form onSubmit={onSubmit} noValidate className="mt-6 rounded-2xl bg-surface p-5">
        <label htmlFor="analyst-name" className="text-sm font-medium">
          {t('entry.nameLabel')}
        </label>
        <input
          id="analyst-name"
          value={name}
          onChange={(event) => {
            setName(event.target.value)
            setMissing(false)
          }}
          autoComplete="name"
          autoFocus
          maxLength={maxNameLength}
          aria-invalid={missing || undefined}
          aria-describedby="analyst-name-help"
          className="mt-2 block h-10 w-full rounded-xl bg-ground px-4 text-[15px] text-aligo-blanco focus:outline-2 focus:outline-aligo-rojo"
        />
        <p id="analyst-name-help" className="mt-2 text-sm text-muted" aria-live="polite">
          {missing ? (
            <span className="border-l-4 border-state-error pl-2 text-aligo-blanco">{t('entry.missing')}</span>
          ) : (
            t('entry.help')
          )}
        </p>
        <button
          type="submit"
          className="mt-5 inline-flex h-9 items-center rounded-full bg-aligo-rojo-oscuro px-5 text-sm font-bold text-aligo-blanco hover:bg-aligo-rojo-medio"
        >
          {t('entry.submit')}
        </button>
      </form>
    </section>
  )
}
