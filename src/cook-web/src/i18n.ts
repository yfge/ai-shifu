import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import Backend from 'i18next-http-backend';
const browserLanguage =
  typeof window !== 'undefined' && navigator.language
    ? navigator.language
    : 'en-US'
i18n
  .use(Backend)
  .use(initReactI18next)
  .init({
    fallbackLng: {
      'en': ['en-US'],
      'zh': ['zh-CN'],
      'default': ['en-US']
    },
    debug: true,
    lng: browserLanguage,
    backend: {
      loadPath: `/locales/{{lng}}.json`,
    },
    interpolation: {
      escapeValue: false,
    },
    returnNull: false,
    // load: 'languageOnly',
    supportedLngs: ['en-US', 'zh-CN', 'en', 'zh'],
    nonExplicitSupportedLngs: true
  });

export default i18n;
