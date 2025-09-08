#!/usr/bin/env node

/**
 * AI-Shifu 翻译验证脚本
 * 验证翻译文件的完整性、一致性和格式正确性
 */

const fs = require('fs');
const path = require('path');
const Ajv = require('ajv');

const I18N_ROOT = path.join(__dirname, '../');
const LOCALES_DIR = path.join(I18N_ROOT, 'locales');
const SCHEMA_PATH = path.join(I18N_ROOT, 'schemas/translation-schema.json');

/**
 * 加载JSON文件
 */
function loadJson(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    return JSON.parse(content);
  } catch (error) {
    throw new Error(`加载JSON文件失败 ${filePath}: ${error.message}`);
  }
}

/**
 * 获取所有翻译文件
 */
function getTranslationFiles() {
  const files = [];
  const items = fs.readdirSync(LOCALES_DIR);

  for (const item of items) {
    if (item.endsWith('.json') && item !== 'languages.json') {
      const filePath = path.join(LOCALES_DIR, item);
      const langCode = item.replace('.json', '');
      files.push({ langCode, filePath });
    }
  }

  return files;
}

/**
 * 使用JSON Schema验证翻译文件
 */
function validateSchema(translations, langCode) {
  const schema = loadJson(SCHEMA_PATH);
  const ajv = new Ajv({
    allErrors: true,
    strict: false,
    allowMatchingProperties: true
  });
  const validate = ajv.compile(schema);

  const valid = validate(translations);
  const errors = [];

  if (!valid) {
    for (const error of validate.errors || []) {
      const path = error.instancePath || 'root';
      errors.push({
        type: 'schema',
        path,
        message: `${error.message} (${error.keyword})`,
        value: error.data
      });
    }
  }

  return { valid, errors };
}

/**
 * 获取对象中所有的键路径
 */
function getKeyPaths(obj, prefix = '') {
  const paths = [];

  for (const [key, value] of Object.entries(obj)) {
    const currentPath = prefix ? `${prefix}.${key}` : key;

    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      paths.push(...getKeyPaths(value, currentPath));
    } else {
      paths.push(currentPath);
    }
  }

  return paths;
}

/**
 * 验证翻译键的一致性
 */
function validateConsistency(translationFiles) {
  if (translationFiles.length < 2) {
    return { consistent: true, errors: [] };
  }

  const errors = [];
  const baseFile = translationFiles[0];
  const baseTranslations = loadJson(baseFile.filePath);
  const basePaths = getKeyPaths(baseTranslations);

  for (let i = 1; i < translationFiles.length; i++) {
    const currentFile = translationFiles[i];
    const currentTranslations = loadJson(currentFile.filePath);
    const currentPaths = getKeyPaths(currentTranslations);

    // 检查缺失的键
    const missingPaths = basePaths.filter(path => !currentPaths.includes(path));
    for (const path of missingPaths) {
      errors.push({
        type: 'consistency',
        langCode: currentFile.langCode,
        path,
        message: `缺少翻译键: ${path}`,
        severity: 'error'
      });
    }

    // 检查多余的键
    const extraPaths = currentPaths.filter(path => !basePaths.includes(path));
    for (const path of extraPaths) {
      errors.push({
        type: 'consistency',
        langCode: currentFile.langCode,
        path,
        message: `多余的翻译键: ${path}`,
        severity: 'warning'
      });
    }
  }

  return {
    consistent: errors.filter(e => e.severity === 'error').length === 0,
    errors
  };
}

/**
 * 验证翻译值
 */
function validateValues(translations, langCode) {
  const errors = [];

  function validateObject(obj, prefix = '') {
    for (const [key, value] of Object.entries(obj)) {
      const currentPath = prefix ? `${prefix}.${key}` : key;

      if (typeof value === 'object' && value !== null) {
        validateObject(value, currentPath);
      } else if (typeof value === 'string') {
        // 检查空值
        if (value.trim() === '') {
          errors.push({
            type: 'value',
            path: currentPath,
            message: '翻译值不能为空',
            severity: 'error'
          });
        }

        // 检查变量插值格式
        const interpolationPattern = /\{\{[^}]*\}\}/g;
        const matches = value.match(interpolationPattern);
        if (matches) {
          for (const match of matches) {
            const varName = match.slice(2, -2).trim();
            if (!varName || !/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(varName)) {
              errors.push({
                type: 'value',
                path: currentPath,
                message: `无效的变量格式: ${match}`,
                severity: 'warning'
              });
            }
          }
        }

        // 检查换行符
        if (value.includes('\n') || value.includes('\r')) {
          errors.push({
            type: 'value',
            path: currentPath,
            message: '翻译值不应包含换行符',
            severity: 'warning'
          });
        }
      } else {
        errors.push({
          type: 'value',
          path: currentPath,
          message: `翻译值类型错误: ${typeof value}，应为字符串`,
          severity: 'error'
        });
      }
    }
  }

  validateObject(translations);
  return errors;
}

/**
 * 验证命名规范
 */
function validateNamingConvention(translations, langCode) {
  const errors = [];

  function validateNaming(obj, prefix = '') {
    for (const key of Object.keys(obj)) {
      const currentPath = prefix ? `${prefix}.${key}` : key;

      // 检查键名格式 (小驼峰命名，允许数字)
      if (!/^[a-z][a-zA-Z0-9]*$/.test(key)) {
        errors.push({
          type: 'naming',
          path: currentPath,
          message: `键名不符合命名规范: ${key}，应使用小驼峰命名`,
          severity: 'warning'
        });
      }

      const value = obj[key];
      if (typeof value === 'object' && value !== null) {
        validateNaming(value, currentPath);
      }
    }
  }

  validateNaming(translations);
  return errors;
}

/**
 * 生成验证报告
 */
function generateReport(results) {
  console.log('=== AI-Shifu 翻译验证报告 ===\n');

  let totalErrors = 0;
  let totalWarnings = 0;

  for (const result of results) {
    const { langCode, errors } = result;
    const errorCount = errors.filter(e => e.severity === 'error' || e.type === 'schema').length;
    const warningCount = errors.filter(e => e.severity === 'warning').length;

    totalErrors += errorCount;
    totalWarnings += warningCount;

    if (errors.length === 0) {
      console.log(`✅ ${langCode}: 验证通过`);
    } else {
      console.log(`❌ ${langCode}: ${errorCount} 个错误, ${warningCount} 个警告`);

      // 按类型分组显示错误
      const errorsByType = {};
      for (const error of errors) {
        if (!errorsByType[error.type]) {
          errorsByType[error.type] = [];
        }
        errorsByType[error.type].push(error);
      }

      for (const [type, typeErrors] of Object.entries(errorsByType)) {
        console.log(`\n  ${type.toUpperCase()} 问题:`);
        for (const error of typeErrors.slice(0, 5)) { // 只显示前5个
          const emoji = error.severity === 'error' ? '❌' : '⚠️';
          console.log(`    ${emoji} ${error.path}: ${error.message}`);
        }
        if (typeErrors.length > 5) {
          console.log(`    ... 还有 ${typeErrors.length - 5} 个 ${type} 问题`);
        }
      }
    }
    console.log('');
  }

  // 一致性检查报告
  const translationFiles = getTranslationFiles();
  const consistencyResult = validateConsistency(translationFiles);

  if (consistencyResult.consistent) {
    console.log('✅ 翻译键一致性检查通过');
  } else {
    const consistencyErrors = consistencyResult.errors.filter(e => e.severity === 'error').length;
    const consistencyWarnings = consistencyResult.errors.filter(e => e.severity === 'warning').length;

    console.log(`❌ 翻译键一致性检查: ${consistencyErrors} 个错误, ${consistencyWarnings} 个警告`);

    // 按语言分组显示一致性问题
    const errorsByLang = {};
    for (const error of consistencyResult.errors) {
      if (!errorsByLang[error.langCode]) {
        errorsByLang[error.langCode] = [];
      }
      errorsByLang[error.langCode].push(error);
    }

    for (const [langCode, langErrors] of Object.entries(errorsByLang)) {
      console.log(`\n  ${langCode}:`);
      for (const error of langErrors.slice(0, 5)) {
        const emoji = error.severity === 'error' ? '❌' : '⚠️';
        console.log(`    ${emoji} ${error.message}`);
      }
      if (langErrors.length > 5) {
        console.log(`    ... 还有 ${langErrors.length - 5} 个问题`);
      }
    }

    totalErrors += consistencyErrors;
    totalWarnings += consistencyWarnings;
  }

  console.log(`\n=== 总结 ===`);
  console.log(`总错误数: ${totalErrors}`);
  console.log(`总警告数: ${totalWarnings}`);

  if (totalErrors === 0) {
    console.log('✅ 验证通过！');
    return true;
  } else {
    console.log('❌ 验证失败，请修复错误后重试');
    return false;
  }
}

/**
 * 主验证函数
 */
function validateTranslations() {
  console.log('开始验证翻译文件...\n');

  const translationFiles = getTranslationFiles();
  const results = [];

  for (const { langCode, filePath } of translationFiles) {
    console.log(`验证 ${langCode}...`);

    try {
      const translations = loadJson(filePath);
      const errors = [];

      // JSON Schema 验证
      const schemaResult = validateSchema(translations, langCode);
      if (!schemaResult.valid) {
        errors.push(...schemaResult.errors);
      }

      // 值验证
      const valueErrors = validateValues(translations, langCode);
      errors.push(...valueErrors);

      // 命名规范验证
      const namingErrors = validateNamingConvention(translations, langCode);
      errors.push(...namingErrors);

      results.push({ langCode, filePath, errors });

    } catch (error) {
      results.push({
        langCode,
        filePath,
        errors: [{
          type: 'file',
          path: 'root',
          message: error.message,
          severity: 'error'
        }]
      });
    }
  }

  return generateReport(results);
}

// 主执行逻辑
if (require.main === module) {
  // 检查依赖
  try {
    require('ajv');
  } catch (error) {
    console.error('❌ 缺少依赖包 ajv，请运行: npm install ajv');
    process.exit(1);
  }

  const success = validateTranslations();
  process.exit(success ? 0 : 1);
}

module.exports = {
  validateTranslations,
  validateSchema,
  validateConsistency,
  validateValues,
  validateNamingConvention
};
