import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

export function NotFoundPage() {
  const { t } = useTranslation()

  return (
    <section>
      <h1 className="text-3xl">{t('notFound.title')}</h1>
      <Link to="/" className="mt-4 inline-block text-aligo-rojo underline">
        {t('notFound.back')}
      </Link>
    </section>
  )
}
