import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

import i18n from '../i18n'
import { signOut } from '../session/session'

afterEach(async () => {
  cleanup()
  signOut()
  localStorage.clear()
  await i18n.changeLanguage('en')
})
