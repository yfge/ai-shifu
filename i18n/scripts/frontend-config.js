/**
 * 统一的前端国际化配置
 * 用于生成标准的 i18n 配置，确保两个前端应用使用一致的设置
 */

/**
 * 获取标准的 i18n 配置
 * @param {Object} options - 配置选项
 * @param {boolean} options.isSSR - 是否为服务端渲染环境 (如 Next.js)
 * @param {boolean} options.debug - 是否开启调试模式
 * @param {string} options.basePath - 资源基础路径 (默认为 '/')
 * @returns {Object} i18n 配置对象
 */
function getStandardI18nConfig(options = {}) {
  const {
    isSSR = false,
    debug = false,
    basePath = '/'
  } = options;

  const config = {
    // 支持的语言列表 (从 languages.json 获取)
    supportedLngs: ['en-US', 'zh-CN'],

    // 语言回退配置
    fallbackLng: {
      'en': ['en-US'],
      'zh': ['zh-CN'],
      'default': ['en-US']
    },

    // 默认语言
    lng: typeof window !== 'undefined' && navigator.language ?
      navigator.language : 'en-US',

    // 调试模式
    debug,

    // 加载策略
    load: 'all',
    nonExplicitSupportedLngs: false,

    // 后端配置
    backend: {
      loadPath: `${basePath}locales/{{lng}}.json`,
      requestOptions: {
        cache: 'default'
      }
    },

    // 插值配置
    interpolation: {
      escapeValue: false, // React 已经处理了 XSS 防护
    },

    // 其他配置
    returnNull: false,
    returnEmptyString: false,

    // React 特定配置
    react: {
      useSuspense: false, // 禁用 Suspense，避免 SSR 问题
      bindI18n: 'languageChanged loaded',
      bindI18nStore: 'added removed',
      transEmptyNodeValue: '',
      transSupportBasicHtmlNodes: true,
      transKeepBasicHtmlNodesFor: ['br', 'strong', 'i', 'em']
    },

    // 检测配置
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
      lookupLocalStorage: 'ai-shifu-language',
      checkWhitelist: true
    },

    // 缓存配置
    cache: {
      enabled: true,
      prefix: 'ai-shifu-i18n-',
      expirationTime: 7 * 24 * 60 * 60 * 1000, // 7 天
      versions: {}
    }
  };

  return config;
}

/**
 * 生成 Web 应用的 i18n 配置文件内容
 */
function generateWebConfig() {
  return `import i18n from 'i18next';
import Backend from 'i18next-http-backend';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

// 统一的 i18n 配置
const config = ${JSON.stringify(getStandardI18nConfig({ isSSR: false }), null, 2)};

// 获取浏览器语言
const browserLanguage = typeof window !== 'undefined' && navigator.language ?
  navigator.language : 'en-US';

// 初始化 i18n
i18n
  .use(Backend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    ...config,
    lng: browserLanguage
  });

export default i18n;
export { browserLanguage, config };
`;
}

/**
 * 生成 Cook Web 应用的 i18n 配置文件内容
 */
function generateCookWebConfig() {
  return `'use client';

import i18n from 'i18next';
import Backend from 'i18next-http-backend';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

// 统一的 i18n 配置
const config = ${JSON.stringify(getStandardI18nConfig({ isSSR: true }), null, 2)};

// 获取浏览器语言 (SSR 安全)
const browserLanguage = typeof window !== 'undefined' && navigator.language ?
  navigator.language : 'en-US';

// 确保在客户端环境下初始化
if (typeof window !== 'undefined') {
  i18n
    .use(Backend)
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
      ...config,
      lng: browserLanguage
    });
}

export default i18n;
export { browserLanguage, config };
`;
}

module.exports = {
  getStandardI18nConfig,
  generateWebConfig,
  generateCookWebConfig
};
