#!/usr/bin/env node

/**
 * AI-Shifu 翻译同步脚本
 * 将中心化的翻译文件同步到各个组件中
 */

const fs = require('fs');
const path = require('path');

const PROJECT_ROOT = path.join(__dirname, '../../');
const I18N_ROOT = path.join(__dirname, '../');

// 同步目标配置
const SYNC_TARGETS = {
  // Web 应用
  web: {
    path: path.join(PROJECT_ROOT, 'src/web/public/locales'),
    type: 'json',
    description: 'Web 应用前端'
  },
  // Cook Web 应用
  cookWeb: {
    path: path.join(PROJECT_ROOT, 'src/cook-web/public/locales'),
    type: 'json',
    description: 'Cook Web 管理后台'
  },
  // 后端 API (现在支持JSON格式)
  backend: {
    path: path.join(PROJECT_ROOT, 'src/api/flaskr/i18n/locales'),
    type: 'json',
    description: '后端 API',
    enabled: true // 已启用，后端现在支持JSON格式
  }
};

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
 * 保存JSON文件
 */
function saveJson(filePath, data) {
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf-8');
}

/**
 * 获取所有语言文件
 */
function getLanguageFiles() {
  const localesDir = path.join(I18N_ROOT, 'locales');
  const files = [];
  const items = fs.readdirSync(localesDir);

  for (const item of items) {
    if (item.endsWith('.json') && item !== 'languages.json') {
      const langCode = item.replace('.json', '');
      const filePath = path.join(localesDir, item);
      files.push({ langCode, filePath });
    }
  }

  return files;
}

/**
 * 同步到前端应用 (JSON格式)
 */
function syncToFrontend(target, languageFiles, options = {}) {
  console.log(`  同步到: ${target.description}`);

  let syncCount = 0;

  for (const { langCode, filePath } of languageFiles) {
    try {
      const translations = loadJson(filePath);
      let processedTranslations = translations;

      // 如果有过滤或转换选项
      if (options.filter) {
        processedTranslations = options.filter(processedTranslations, langCode);
      }

      const targetPath = path.join(target.path, `${langCode}.json`);

      // 检查是否需要更新
      let needsUpdate = true;
      if (fs.existsSync(targetPath)) {
        const existingContent = loadJson(targetPath);
        needsUpdate = JSON.stringify(existingContent) !== JSON.stringify(processedTranslations);
      }

      if (needsUpdate || options.force) {
        saveJson(targetPath, processedTranslations);
        syncCount++;
        console.log(`    ✓ ${langCode}.json 已更新`);
      } else {
        console.log(`    - ${langCode}.json 无变化`);
      }

    } catch (error) {
      console.error(`    ❌ ${langCode}: ${error.message}`);
    }
  }

  return syncCount;
}

/**
 * 转换为Python格式 (预留给后端升级后使用)
 */
function convertToPythonFormat(translations) {
  const pythonFiles = {};

  function processObject(obj, prefix = '') {
    const result = {};

    for (const [key, value] of Object.entries(obj)) {
      if (typeof value === 'object' && value !== null) {
        const subResult = processObject(value, `${prefix}${key}.`);
        Object.assign(result, subResult);
      } else {
        // 转换为Python常量格式
        const constantName = `${prefix}${key}`.toUpperCase().replace(/\./g, '_');
        result[constantName] = value;
      }
    }

    return result;
  }

  const constants = processObject(translations);

  // 按模块分组
  const modules = {};
  for (const [key, value] of Object.entries(constants)) {
    const parts = key.split('_');
    const moduleName = parts[0];

    if (!modules[moduleName]) {
      modules[moduleName] = {};
    }
    modules[moduleName][key] = value;
  }

  return modules;
}

/**
 * 同步到后端 (Python格式) - 暂未启用
 */
function syncToBackend(target, languageFiles) {
  console.log(`  同步到: ${target.description} (暂未启用)`);

  // TODO: 等后端i18n系统升级完成后实现
  console.log(`    - 等待后端系统升级`);

  return 0;
}

/**
 * 生成同步摘要
 */
function generateSummary(results) {
  console.log('\n=== 同步摘要 ===');

  let totalFiles = 0;
  let totalTargets = 0;

  for (const [targetName, result] of Object.entries(results)) {
    if (result.enabled) {
      totalTargets++;
      totalFiles += result.syncCount;
      console.log(`${targetName}: ${result.syncCount} 个文件已更新`);
    } else {
      console.log(`${targetName}: 暂未启用`);
    }
  }

  console.log(`\n总计: ${totalFiles} 个文件已同步到 ${totalTargets} 个目标`);
}

/**
 * 检查目标是否存在
 */
function checkTargets() {
  const issues = [];

  for (const [name, target] of Object.entries(SYNC_TARGETS)) {
    if (target.enabled !== false && !fs.existsSync(target.path)) {
      issues.push(`目标路径不存在: ${name} -> ${target.path}`);
    }
  }

  if (issues.length > 0) {
    console.log('⚠️  发现以下问题:');
    for (const issue of issues) {
      console.log(`  - ${issue}`);
    }
    console.log('');
  }

  return issues;
}

/**
 * 主同步函数
 */
function syncTranslations(options = {}) {
  console.log('开始同步翻译文件...\n');

  // 检查目标路径
  const issues = checkTargets();
  if (issues.length > 0 && !options.ignoreIssues) {
    console.log('请修复上述问题后重试，或使用 --ignore-issues 忽略');
    return false;
  }

  const languageFiles = getLanguageFiles();
  console.log(`找到 ${languageFiles.length} 个语言文件\n`);

  const results = {};

  // 同步到各个目标
  for (const [targetName, target] of Object.entries(SYNC_TARGETS)) {
    if (target.enabled === false) {
      results[targetName] = { enabled: false, syncCount: 0 };
      continue;
    }

    let syncCount = 0;

    try {
      if (target.type === 'json') {
        syncCount = syncToFrontend(target, languageFiles, options);
      } else if (target.type === 'python') {
        syncCount = syncToBackend(target, languageFiles, options);
      }

      results[targetName] = { enabled: true, syncCount };

    } catch (error) {
      console.error(`  ❌ 同步到 ${target.description} 失败: ${error.message}`);
      results[targetName] = { enabled: true, syncCount: 0, error: error.message };
    }
  }

  generateSummary(results);

  // 如果启用了验证，运行验证脚本
  if (options.validate) {
    console.log('\n运行验证脚本...');
    try {
      const { validateTranslations } = require('./validate.js');
      validateTranslations();
    } catch (error) {
      console.error('验证脚本运行失败:', error.message);
    }
  }

  return true;
}

/**
 * 创建备份
 */
function createBackup(targetPath, langCode) {
  const backupDir = path.join(path.dirname(targetPath), 'backup');
  if (!fs.existsSync(backupDir)) {
    fs.mkdirSync(backupDir, { recursive: true });
  }

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const backupPath = path.join(backupDir, `${langCode}-${timestamp}.json`);

  if (fs.existsSync(targetPath)) {
    fs.copyFileSync(targetPath, backupPath);
  }
}

// 命令行参数解析
function parseArgs(args) {
  const options = {
    force: false,
    validate: false,
    ignoreIssues: false,
    backup: false
  };

  for (const arg of args) {
    if (arg === '--force') options.force = true;
    if (arg === '--validate') options.validate = true;
    if (arg === '--ignore-issues') options.ignoreIssues = true;
    if (arg === '--backup') options.backup = true;
    if (arg === '--help') {
      console.log(`
AI-Shifu 翻译同步脚本

用法: node sync.js [选项]

选项:
  --force          强制更新所有文件，即使没有变化
  --validate       同步后运行验证脚本
  --ignore-issues  忽略目标路径检查问题
  --backup         同步前创建备份
  --help           显示帮助信息

示例:
  node sync.js                    # 基本同步
  node sync.js --force            # 强制更新所有文件
  node sync.js --validate         # 同步后验证
  node sync.js --backup --force   # 创建备份并强制更新
      `);
      process.exit(0);
    }
  }

  return options;
}

// 主执行逻辑
if (require.main === module) {
  try {
    const options = parseArgs(process.argv.slice(2));
    const success = syncTranslations(options);

    if (success) {
      console.log('\n✅ 同步完成!');
      process.exit(0);
    } else {
      console.log('\n❌ 同步失败');
      process.exit(1);
    }
  } catch (error) {
    console.error('❌ 同步时出错:', error);
    process.exit(1);
  }
}

module.exports = {
  syncTranslations,
  syncToFrontend,
  syncToBackend,
  convertToPythonFormat
};
