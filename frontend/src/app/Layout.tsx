import { useTranslation } from 'react-i18next'
import { Link, Outlet, useNavigate } from 'react-router'

import logo from '../assets/logo-aligo-blanco.png'
import { signOut, useSession } from '../session/session'
import { LanguageSwitch } from './LanguageSwitch'

export function Layout() {
  const { t } = useTranslation()
  const session = useSession()
  const navigate = useNavigate()

  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:bg-aligo-rojo-oscuro focus:px-4 focus:py-2 focus:font-bold"
      >
        {t('app.skipToContent')}
      </a>
      <header className="border-b border-rule">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <Link to="/" className="flex items-center gap-4 sm:gap-5">
            <img src={logo} alt="ALIGO Defensores Informáticos" className="h-12 w-auto" />
            <span className="border-l border-rule pl-4 text-lg font-bold sm:pl-5">{t('app.name')}</span>
          </Link>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
            {session && (
              <div className="flex items-center gap-3 text-sm">
                <span>
                  <span className="sr-only">{t('session.signedInAs')} </span>
                  <span className="font-medium">{session.analyst}</span>
                </span>
                <button
                  type="button"
                  onClick={() => {
                    signOut()
                    navigate('/', { replace: true })
                  }}
                  className="text-muted underline decoration-control underline-offset-4 hover:text-aligo-blanco hover:decoration-aligo-blanco"
                >
                  {t('session.signOut')}
                </button>
              </div>
            )}
            <LanguageSwitch />
          </div>
        </div>
      </header>
      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6">
        <Outlet />
      </main>
    </div>
  )
}
