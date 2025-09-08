#!/usr/bin/env node

/**
 * 更新前端应用的 i18n 配置文件
 * 基于统一的配置标准生成标准化的 i18n 配置
 */

const fs = require('fs');
const path = require('path');
const { generateWebConfig, generateCookWebConfig } = require('./frontend-config.js');

const PROJECT_ROOT = path.join(__dirname, '../../');

// 目标文件路径
const TARGETS = {
  web: {
    path: path.join(PROJECT_ROOT, 'src/web/src/i18n.ts'),
    generator: generateWebConfig,
    description: 'Web 应用 i18n 配置'
  },
  cookWeb: {
    path: path.join(PROJECT_ROOT, 'src/cook-web/src/i18n.ts'),
    generator: generateCookWebConfig,
    description: 'Cook Web 应用 i18n 配置'
  }
};

/**
 * 创建配置文件备份
 */
function createBackup(filePath) {
  if (fs.existsSync(filePath)) {
    const backupPath = `${filePath}.backup.${Date.now()}`;
    fs.copyFileSync(filePath, backupPath);
    console.log(`  📁 已创建备份: ${path.basename(backupPath)}`);
    return backupPath;
  }
  return null;
}

/**
 * 更新配置文件
 */
function updateConfig(name, target) {
  console.log(`\n🔧 更新 ${target.description}...`);

  try {
    // 创建备份
    const backupPath = createBackup(target.path);

    // 生成新配置
    const newConfig = target.generator();

    // 确保目录存在
    const dir = path.dirname(target.path);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    // 写入新配置
    fs.writeFileSync(target.path, newConfig, 'utf-8');

    console.log(`  ✅ 配置已更新: ${target.path}`);

    return { success: true, backupPath };
  } catch (error) {
    console.error(`  ❌ 更新失败: ${error.message}`);
    return { success: false, error: error.message };
  }
}

/**
 * 验证配置文件
 */
function validateConfig(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf-8');

    // 基本语法检查
    const hasImports = content.includes('import i18n');
    const hasExports = content.includes('export default i18n');
    const hasConfig = content.includes('config');

    return {
      valid: hasImports && hasExports && hasConfig,
      details: {
        hasImports,
        hasExports,
        hasConfig
      }
    };
  } catch (error) {
    return {
      valid: false,
      error: error.message
    };
  }
}

/**
 * 检查依赖包
 */
function checkDependencies() {
  console.log('🔍 检查依赖包...\n');

  const webPackageJsonPath = path.join(PROJECT_ROOT, 'src/web/package.json');
  const cookWebPackageJsonPath = path.join(PROJECT_ROOT, 'src/cook-web/package.json');

  const requiredPackages = [
    'i18next',
    'react-i18next',
    'i18next-http-backend',
    'i18next-browser-languagedetector'
  ];

  for (const [appName, packagePath] of [
    ['Web App', webPackageJsonPath],
    ['Cook Web', cookWebPackageJsonPath]
  ]) {
    if (!fs.existsSync(packagePath)) {
      console.log(`⚠️  ${appName}: package.json 不存在: ${packagePath}`);
      continue;
    }

    try {
      const packageJson = JSON.parse(fs.readFileSync(packagePath, 'utf-8'));
      const allDeps = {
        ...packageJson.dependencies || {},
        ...packageJson.devDependencies || {}
      };

      console.log(`📦 ${appName} 依赖检查:`);

      let missingPackages = [];
      for (const pkg of requiredPackages) {
        if (allDeps[pkg]) {
          console.log(`  ✅ ${pkg}: ${allDeps[pkg]}`);
        } else {
          console.log(`  ❌ ${pkg}: 未安装`);
          missingPackages.push(pkg);
        }
      }

      if (missingPackages.length > 0) {
        console.log(`  💡 需要安装: npm install ${missingPackages.join(' ')}`);
      }

    } catch (error) {
      console.log(`  ❌ 读取 package.json 失败: ${error.message}`);
    }

    console.log('');
  }
}

/**
 * 主函数
 */
function main() {
  console.log('🌍 AI-Shifu 前端国际化配置标准化工具\n');

  // 检查依赖
  checkDependencies();

  console.log('🚀 开始更新配置文件...');

  const results = {};

  // 更新各个应用的配置
  for (const [name, target] of Object.entries(TARGETS)) {
    results[name] = updateConfig(name, target);
  }

  console.log('\n📋 验证配置文件...');

  // 验证更新后的配置
  for (const [name, target] of Object.entries(TARGETS)) {
    if (results[name].success) {
      const validation = validateConfig(target.path);
      if (validation.valid) {
        console.log(`  ✅ ${name}: 配置文件格式正确`);
      } else {
        console.log(`  ❌ ${name}: 配置文件可能有问题`);
        console.log(`    详情: ${JSON.stringify(validation.details || validation.error)}`);
      }
    }
  }

  // 总结报告
  console.log('\n📊 更新总结:');
  let successCount = 0;
  let totalCount = 0;

  for (const [name, result] of Object.entries(results)) {
    totalCount++;
    if (result.success) {
      successCount++;
      console.log(`  ✅ ${name}: 成功`);
    } else {
      console.log(`  ❌ ${name}: 失败 - ${result.error}`);
    }
  }

  console.log(`\n🎯 完成情况: ${successCount}/${totalCount} 个配置文件已更新`);

  if (successCount === totalCount) {
    console.log('\n✅ 所有前端应用的 i18n 配置已标准化!');
    console.log('\n💡 下一步操作:');
    console.log('1. 重启开发服务器以应用新配置');
    console.log('2. 运行翻译验证脚本: node i18n/scripts/validate.js');
    console.log('3. 测试应用的多语言功能');
  } else {
    console.log('\n⚠️  部分配置更新失败，请检查错误信息并手动修复');
  }
}

// 命令行参数处理
if (require.main === module) {
  const args = process.argv.slice(2);

  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
AI-Shifu 前端 i18n 配置标准化工具

用法: node update-frontend-configs.js [选项]

选项:
  --help, -h     显示帮助信息

说明:
  此脚本会将两个前端应用的 i18n 配置更新为统一的标准格式，
  包括语言支持、回退机制、缓存策略等设置。

  更新前会自动创建备份文件。
    `);
    process.exit(0);
  }

  try {
    main();
  } catch (error) {
    console.error('❌ 脚本执行失败:', error);
    process.exit(1);
  }
}

module.exports = {
  updateConfig,
  validateConfig,
  checkDependencies
};
