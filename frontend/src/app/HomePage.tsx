import { useTranslation } from 'react-i18next'

export function HomePage() {
  const { t } = useTranslation()

  return (
    <section className="max-w-2xl">
      <h1 className="text-3xl">{t('home.title')}</h1>
      <p className="mt-4 text-aligo-gris-claro">{t('home.intro')}</p>
    </section>
  )
}
