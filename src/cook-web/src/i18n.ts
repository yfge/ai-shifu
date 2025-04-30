import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import Backend from 'i18next-http-backend';
const browserLanguage = navigator.language || navigator.languages[0]

i18n
  .use(Backend)
  .use(initReactI18next)
  .init({
    fallbackLng: 'en-US',
    debug: true,
    lng: browserLanguage,
    backend: {
      loadPath: `/locales/{{lng}}.json`,
    },
    interpolation: {
      escapeValue: false,
    },
    returnNull: false,
  });

export default i18n;
