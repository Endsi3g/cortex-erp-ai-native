import { createI18n } from 'vue-i18n'
import frCA from '@locales/fr-CA.json'
import enCA from '@locales/en-CA.json'

export type LocaleType = 'fr-CA' | 'en-CA'

const savedLocale = (typeof localStorage !== 'undefined' && localStorage.getItem('cortex_locale')) as LocaleType | null
export const defaultLocale: LocaleType = savedLocale || 'fr-CA'

export const i18n = createI18n({
  legacy: false,
  locale: defaultLocale,
  fallbackLocale: 'fr-CA',
  messages: {
    'fr-CA': frCA,
    'en-CA': enCA
  }
})

export * from './formatters'

