import { useTranslation } from 'react-i18next'

import { languages } from '../i18n'

export function LanguageSwitch() {
  const { t, i18n } = useTranslation()

  return (
    <div role="group" aria-label={t('language.label')} className="flex rounded border border-aligo-gris">
      {languages.map((language) => {
        const active = i18n.resolvedLanguage === language
        return (
          <button
            key={language}
            type="button"
            lang={language}
            aria-pressed={active}
            onClick={() => void i18n.changeLanguage(language)}
            className={
              active
                ? 'bg-aligo-blanco px-3 py-1 text-sm font-medium text-aligo-negro'
                : 'px-3 py-1 text-sm text-aligo-gris-claro hover:text-aligo-blanco'
            }
          >
            {t(`language.${language}`)}
          </button>
        )
      })}
    </div>
  )
}
