#!/usr/bin/env node

/**
 * AI-Shifu 翻译提取和合并脚本
 * 从现有的三个系统中提取翻译内容并合并到统一的JSON格式中
 */

const fs = require('fs');
const path = require('path');

const PROJECT_ROOT = path.join(__dirname, '../../');
const I18N_ROOT = path.join(__dirname, '../');

// 配置路径
const PATHS = {
  backend: path.join(PROJECT_ROOT, 'src/api/flaskr/i18n'),
  web: path.join(PROJECT_ROOT, 'src/web/public/locales'),
  cookWeb: path.join(PROJECT_ROOT, 'src/cook-web/public/locales'),
  output: path.join(I18N_ROOT, 'locales')
};

/**
 * 从Python文件中提取翻译常量
 */
function extractPythonTranslations(filePath) {
  if (!fs.existsSync(filePath)) {
    return {};
  }

  const content = fs.readFileSync(filePath, 'utf-8');
  const translations = {};

  // 匹配形如 KEY = "value" 的行
  const regex = /^([A-Z_]+)\s*=\s*["'](.*?)["']/gm;
  let match;

  while ((match = regex.exec(content)) !== null) {
    const [, key, value] = match;
    translations[key] = value;
  }

  return translations;
}

/**
 * 递归遍历目录，提取Python翻译文件
 */
function extractFromPythonDir(dirPath, basePath = '') {
  const result = {};

  if (!fs.existsSync(dirPath)) {
    return result;
  }

  const items = fs.readdirSync(dirPath);

  for (const item of items) {
    const fullPath = path.join(dirPath, item);
    const stat = fs.statSync(fullPath);

    if (stat.isDirectory() && !item.startsWith('__pycache__')) {
      const subTranslations = extractFromPythonDir(fullPath, path.join(basePath, item));
      if (Object.keys(subTranslations).length > 0) {
        result[item] = subTranslations;
      }
    } else if (stat.isFile() && item.endsWith('.py')) {
      const translations = extractPythonTranslations(fullPath);
      if (Object.keys(translations).length > 0) {
        const fileName = item.replace('.py', '');
        result[fileName] = translations;
      }
    }
  }

  return result;
}

/**
 * 加载JSON翻译文件
 */
function loadJsonTranslations(filePath) {
  try {
    if (fs.existsSync(filePath)) {
      return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    }
  } catch (error) {
    console.error(`加载JSON文件失败: ${filePath}`, error);
  }
  return {};
}

/**
 * 深度合并对象
 */
function deepMerge(target, source) {
  const result = { ...target };

  for (const key in source) {
    if (source.hasOwnProperty(key)) {
      if (typeof source[key] === 'object' && source[key] !== null && !Array.isArray(source[key])) {
        result[key] = deepMerge(result[key] || {}, source[key]);
      } else {
        result[key] = source[key];
      }
    }
  }

  return result;
}

/**
 * 规范化后端翻译键名
 * 将 Python 的大写键名转换为小驼峰命名
 */
function normalizeBackendTranslations(translations, prefix = '') {
  const normalized = {};

  for (const [key, value] of Object.entries(translations)) {
    if (typeof value === 'object' && value !== null) {
      const subPrefix = prefix ? `${prefix}.${key.toLowerCase()}` : key.toLowerCase();
      Object.assign(normalized, normalizeBackendTranslations(value, subPrefix));
    } else {
      const normalizedKey = prefix ?
        `${prefix}.${key.toLowerCase().replace(/_/g, '')}` :
        key.toLowerCase().replace(/_/g, '');

      // 将键名映射到统一的结构中
      setNestedValue(normalized, normalizedKey, value);
    }
  }

  return normalized;
}

/**
 * 在嵌套对象中设置值
 */
function setNestedValue(obj, path, value) {
  const keys = path.split('.');
  let current = obj;

  for (let i = 0; i < keys.length - 1; i++) {
    const key = keys[i];
    if (!current[key]) {
      current[key] = {};
    }
    current = current[key];
  }

  current[keys[keys.length - 1]] = value;
}

/**
 * 主要提取函数
 */
function extractAllTranslations() {
  console.log('开始提取翻译内容...');

  const languages = ['en-US', 'zh-CN'];
  const extractedTranslations = {};

  for (const lang of languages) {
    console.log(`\n处理语言: ${lang}`);
    let mergedTranslations = {};

    // 1. 提取后端翻译
    console.log('  - 提取后端翻译...');
    const backendPath = path.join(PATHS.backend, lang);
    const backendTranslations = extractFromPythonDir(backendPath);
    const normalizedBackendTranslations = normalizeBackendTranslations(backendTranslations);
    mergedTranslations = deepMerge(mergedTranslations, normalizedBackendTranslations);

    // 2. 提取Web应用翻译
    console.log('  - 提取Web应用翻译...');
    const webTranslationsPath = path.join(PATHS.web, `${lang}.json`);
    const webTranslations = loadJsonTranslations(webTranslationsPath);
    mergedTranslations = deepMerge(mergedTranslations, webTranslations);

    // 3. 提取Cook Web翻译
    console.log('  - 提取Cook Web翻译...');
    const cookWebTranslationsPath = path.join(PATHS.cookWeb, `${lang}.json`);
    const cookWebTranslations = loadJsonTranslations(cookWebTranslationsPath);
    mergedTranslations = deepMerge(mergedTranslations, cookWebTranslations);

    extractedTranslations[lang] = mergedTranslations;
  }

  return extractedTranslations;
}

/**
 * 保存提取的翻译到文件
 */
function saveTranslations(translations) {
  console.log('\n保存翻译文件...');

  // 确保输出目录存在
  if (!fs.existsSync(PATHS.output)) {
    fs.mkdirSync(PATHS.output, { recursive: true });
  }

  for (const [lang, content] of Object.entries(translations)) {
    const outputPath = path.join(PATHS.output, `${lang}.json`);
    fs.writeFileSync(outputPath, JSON.stringify(content, null, 2), 'utf-8');
    console.log(`  ✓ 已保存: ${outputPath}`);
  }
}

/**
 * 生成统计报告
 */
function generateReport(translations) {
  console.log('\n=== 翻译提取报告 ===');

  for (const [lang, content] of Object.entries(translations)) {
    const keyCount = countKeys(content);
    console.log(`${lang}: ${keyCount} 个翻译键`);
  }

  // 检查键一致性
  const languages = Object.keys(translations);
  if (languages.length > 1) {
    const baseKeys = getKeys(translations[languages[0]]);
    let allConsistent = true;

    for (let i = 1; i < languages.length; i++) {
      const currentKeys = getKeys(translations[languages[i]]);
      const missing = baseKeys.filter(key => !currentKeys.includes(key));
      const extra = currentKeys.filter(key => !baseKeys.includes(key));

      if (missing.length > 0 || extra.length > 0) {
        allConsistent = false;
        console.log(`\n⚠️  语言 ${languages[i]} 键不一致:`);
        if (missing.length > 0) {
          console.log(`  缺少: ${missing.slice(0, 5).join(', ')}${missing.length > 5 ? ` ...等${missing.length}个` : ''}`);
        }
        if (extra.length > 0) {
          console.log(`  多余: ${extra.slice(0, 5).join(', ')}${extra.length > 5 ? ` ...等${extra.length}个` : ''}`);
        }
      }
    }

    if (allConsistent) {
      console.log('\n✓ 所有语言的翻译键都一致');
    }
  }
}

/**
 * 递归计算对象中的键数量
 */
function countKeys(obj) {
  let count = 0;
  for (const value of Object.values(obj)) {
    if (typeof value === 'object' && value !== null) {
      count += countKeys(value);
    } else {
      count++;
    }
  }
  return count;
}

/**
 * 获取所有嵌套键的路径
 */
function getKeys(obj, prefix = '') {
  const keys = [];
  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'object' && value !== null) {
      keys.push(...getKeys(value, fullKey));
    } else {
      keys.push(fullKey);
    }
  }
  return keys;
}

// 主执行逻辑
if (require.main === module) {
  try {
    const translations = extractAllTranslations();
    saveTranslations(translations);
    generateReport(translations);
    console.log('\n✅ 翻译提取完成!');
  } catch (error) {
    console.error('❌ 提取翻译时出错:', error);
    process.exit(1);
  }
}

module.exports = {
  extractAllTranslations,
  extractPythonTranslations,
  loadJsonTranslations,
  deepMerge
};
