import { createI18n } from 'vue-i18n'
import frCA from '../../locales/fr-CA.json'
import enCA from '../../locales/en-CA.json'
import type { SupportedLocale } from './types'

export const i18n = createI18n({
  legacy: false,
  locale: (typeof localStorage !== 'undefined' && localStorage.getItem('cortex_locale') as SupportedLocale) || 'fr-CA',
  fallbackLocale: 'en-CA',
  messages: {
    'fr-CA': frCA,
    'en-CA': enCA
  }
})

export * from './types'
export * from './formatters'
