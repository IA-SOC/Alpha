import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import en from './locales/en.json'
import es from './locales/es.json'

export const languages = ['en', 'es'] as const
export type Language = (typeof languages)[number]

const storageKey = 'soc.language'

function storedLanguage(): Language {
  try {
    const value = localStorage.getItem(storageKey)
    return languages.find((language) => language === value) ?? 'en'
  } catch {
    return 'en'
  }
}

i18n.on('languageChanged', (language) => {
  document.documentElement.lang = language
  try {
    localStorage.setItem(storageKey, language)
  } catch {
    // Private windows can block storage. The switch still works for this tab.
  }
})

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, es: { translation: es } },
  lng: storedLanguage(),
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

export default i18n
