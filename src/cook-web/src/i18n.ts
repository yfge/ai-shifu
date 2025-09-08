'use client';

import i18n from 'i18next';
import Backend from 'i18next-http-backend';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

// 统一的 i18n 配置
const config = {
  supportedLngs: ['en-US', 'zh-CN'],
  fallbackLng: {
    en: ['en-US'],
    zh: ['zh-CN'],
    default: ['en-US'],
  },
  lng: 'en-US',
  debug: false,
  load: 'all',
  nonExplicitSupportedLngs: false,
  backend: {
    loadPath: '/locales/{{lng}}.json',
    requestOptions: {
      cache: 'default',
    },
  },
  interpolation: {
    escapeValue: false,
  },
  returnNull: false,
  returnEmptyString: false,
  react: {
    useSuspense: false,
    bindI18n: 'languageChanged loaded',
    bindI18nStore: 'added removed',
    transEmptyNodeValue: '',
    transSupportBasicHtmlNodes: true,
    transKeepBasicHtmlNodesFor: ['br', 'strong', 'i', 'em'],
  },
  detection: {
    order: ['localStorage', 'navigator', 'htmlTag'],
    caches: ['localStorage'],
    lookupLocalStorage: 'ai-shifu-language',
    checkWhitelist: true,
  },
  cache: {
    enabled: true,
    prefix: 'ai-shifu-i18n-',
    expirationTime: 604800000,
    versions: {},
  },
};

// 获取浏览器语言 (SSR 安全)
const browserLanguage =
  typeof window !== 'undefined' && navigator.language
    ? navigator.language
    : 'en-US';

// 确保在客户端环境下初始化
if (typeof window !== 'undefined') {
  i18n
    .use(Backend)
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
      ...config,
      lng: browserLanguage,
    });
}

export default i18n;
export { browserLanguage, config };
