#!/usr/bin/env node

/**
 * AI-Shifu Git Hooks 安装脚本
 * 安装翻译验证相关的Git钩子
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const PROJECT_ROOT = path.join(__dirname, '../../');
const GIT_HOOKS_DIR = path.join(PROJECT_ROOT, '.git/hooks');
const I18N_DIR = path.join(__dirname, '../');

/**
 * 检查Git仓库是否存在
 */
function checkGitRepo() {
  const gitDir = path.join(PROJECT_ROOT, '.git');
  if (!fs.existsSync(gitDir)) {
    console.log('❌ 不是Git仓库，无法安装Git钩子');
    return false;
  }
  return true;
}

/**
 * 创建或更新pre-commit钩子
 */
function installPreCommitHook() {
  console.log('🔧 安装pre-commit钩子...');

  const hookPath = path.join(GIT_HOOKS_DIR, 'pre-commit');
  const hookScript = path.join(I18N_DIR, 'scripts/pre-commit-hook.sh');

  // 检查源脚本是否存在
  if (!fs.existsSync(hookScript)) {
    console.log('❌ pre-commit钩子脚本不存在');
    return false;
  }

  // 创建钩子内容
  const hookContent = `#!/bin/bash
# AI-Shifu Git Pre-commit Hook
# Auto-generated - DO NOT EDIT MANUALLY

# 运行i18n验证
if [ -f "${hookScript}" ]; then
    bash "${hookScript}"
    i18n_exit_code=$?

    if [ $i18n_exit_code -ne 0 ]; then
        echo "❌ i18n验证失败，提交被阻止"
        exit $i18n_exit_code
    fi
else
    echo "⚠️ i18n验证脚本未找到，跳过检查"
fi

# 如果存在其他pre-commit脚本，在这里调用
# 例如：运行linting、测试等

echo "✅ pre-commit检查通过"
exit 0
`;

  try {
    // 备份现有钩子
    if (fs.existsSync(hookPath)) {
      const backupPath = `${hookPath}.backup.${Date.now()}`;
      fs.copyFileSync(hookPath, backupPath);
      console.log(`📁 已备份现有钩子: ${path.basename(backupPath)}`);
    }

    // 写入新钩子
    fs.writeFileSync(hookPath, hookContent);

    // 设置可执行权限
    fs.chmodSync(hookPath, 0o755);

    console.log('✅ pre-commit钩子安装成功');
    return true;

  } catch (error) {
    console.error('❌ pre-commit钩子安装失败:', error.message);
    return false;
  }
}

/**
 * 安装commit-msg钩子（用于验证提交信息格式）
 */
function installCommitMsgHook() {
  console.log('🔧 安装commit-msg钩子...');

  const hookPath = path.join(GIT_HOOKS_DIR, 'commit-msg');
  const hookContent = `#!/bin/bash
# AI-Shifu Commit Message Hook
# Validates commit message format

commit_file="$1"
commit_msg=$(cat "$commit_file")

# 检查是否符合Conventional Commits格式
conventional_pattern="^(feat|fix|docs|style|refactor|test|chore|build|ci|perf|revert)(\\(.+\\))?: .+"

if [[ ! "$commit_msg" =~ $conventional_pattern ]]; then
    echo ""
    echo "❌ 提交信息格式不正确"
    echo ""
    echo "请使用Conventional Commits格式："
    echo "  <type>: <description>"
    echo ""
    echo "类型 (type):"
    echo "  feat     - 新功能"
    echo "  fix      - Bug修复"
    echo "  docs     - 文档变更"
    echo "  style    - 格式调整（不影响代码逻辑）"
    echo "  refactor - 重构"
    echo "  test     - 测试相关"
    echo "  chore    - 构建或辅助工具变更"
    echo "  build    - 构建系统变更"
    echo "  ci       - CI配置变更"
    echo "  perf     - 性能优化"
    echo "  revert   - 回退提交"
    echo ""
    echo "示例："
    echo "  feat: add unified i18n system"
    echo "  fix: resolve translation key conflicts"
    echo "  docs: update i18n documentation"
    echo ""
    echo "当前提交信息:"
    echo "  $commit_msg"
    echo ""
    exit 1
fi

echo "✅ 提交信息格式正确"
exit 0
`;

  try {
    // 备份现有钩子
    if (fs.existsSync(hookPath)) {
      const backupPath = `${hookPath}.backup.${Date.now()}`;
      fs.copyFileSync(hookPath, backupPath);
      console.log(`📁 已备份现有钩子: ${path.basename(backupPath)}`);
    }

    // 写入新钩子
    fs.writeFileSync(hookPath, hookContent);

    // 设置可执行权限
    fs.chmodSync(hookPath, 0o755);

    console.log('✅ commit-msg钩子安装成功');
    return true;

  } catch (error) {
    console.error('❌ commit-msg钩子安装失败:', error.message);
    return false;
  }
}

/**
 * 检查依赖
 */
function checkDependencies() {
  console.log('🔍 检查依赖...');

  const i18nPackageJson = path.join(I18N_DIR, 'package.json');

  if (!fs.existsSync(i18nPackageJson)) {
    console.log('📦 初始化i18n依赖...');
    try {
      execSync('npm init -y', { cwd: I18N_DIR, stdio: 'ignore' });
    } catch (error) {
      console.log('❌ npm初始化失败');
      return false;
    }
  }

  // 检查ajv依赖
  const nodeModulesDir = path.join(I18N_DIR, 'node_modules');
  if (!fs.existsSync(path.join(nodeModulesDir, 'ajv'))) {
    console.log('📦 安装验证依赖...');
    try {
      execSync('npm install ajv', { cwd: I18N_DIR, stdio: 'ignore' });
    } catch (error) {
      console.log('❌ 依赖安装失败');
      return false;
    }
  }

  console.log('✅ 依赖检查完成');
  return true;
}

/**
 * 显示使用说明
 */
function showUsage() {
  console.log(`
🌍 AI-Shifu Git Hooks 安装工具

用法: node install-hooks.js [选项]

选项:
  --help, -h           显示帮助信息
  --pre-commit-only    只安装pre-commit钩子
  --commit-msg-only    只安装commit-msg钩子
  --skip-dependencies  跳过依赖检查

功能:
  - pre-commit: 提交前验证翻译文件的完整性和一致性
  - commit-msg: 验证提交信息格式（Conventional Commits）

安装后，每次提交代码时会自动运行相关检查。
如果检查失败，提交会被阻止，需要修复问题后重试。
  `);
}

/**
 * 主函数
 */
function main() {
  console.log('🌍 AI-Shifu Git Hooks 安装工具\n');

  const args = process.argv.slice(2);

  if (args.includes('--help') || args.includes('-h')) {
    showUsage();
    return;
  }

  // 检查Git仓库
  if (!checkGitRepo()) {
    process.exit(1);
  }

  // 检查依赖
  if (!args.includes('--skip-dependencies')) {
    if (!checkDependencies()) {
      process.exit(1);
    }
  }

  let success = true;

  // 安装钩子
  if (!args.includes('--commit-msg-only')) {
    if (!installPreCommitHook()) {
      success = false;
    }
  }

  if (!args.includes('--pre-commit-only')) {
    if (!installCommitMsgHook()) {
      success = false;
    }
  }

  console.log('\n================================');

  if (success) {
    console.log('✅ Git钩子安装完成！');
    console.log('\n📋 接下来：');
    console.log('1. 现在每次提交时会自动验证翻译文件');
    console.log('2. 提交信息需要遵循Conventional Commits格式');
    console.log('3. 如遇问题，可运行 node i18n/scripts/validate.js 手动检查');
    console.log('4. 运行 git commit --no-verify 可跳过钩子检查（不推荐）');
  } else {
    console.log('❌ 部分钩子安装失败，请检查错误信息');
    process.exit(1);
  }
}

if (require.main === module) {
  try {
    main();
  } catch (error) {
    console.error('❌ 安装失败:', error);
    process.exit(1);
  }
}

module.exports = {
  installPreCommitHook,
  installCommitMsgHook,
  checkDependencies
};
