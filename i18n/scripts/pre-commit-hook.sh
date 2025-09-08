#!/bin/bash

# AI-Shifu 翻译文件预提交钩子
# 在提交前验证翻译文件的完整性和一致性

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
I18N_DIR="$PROJECT_ROOT/i18n"

echo -e "${BLUE}🌍 AI-Shifu 翻译文件预提交检查${NC}"
echo "================================"

# 检查是否有翻译相关文件被修改
translation_files_changed() {
    local changed_files=$(git diff --cached --name-only)
    echo "$changed_files" | grep -E "(i18n/|locales/|\.json$|i18n\.ts$)" > /dev/null
}

# 如果没有翻译文件被修改，跳过检查
if ! translation_files_changed; then
    echo -e "${GREEN}✅ 没有翻译文件被修改，跳过i18n检查${NC}"
    exit 0
fi

echo -e "${BLUE}📁 检测到翻译文件变更，开始验证...${NC}"

# 检查必要的目录和文件
check_structure() {
    echo -e "\n${BLUE}🔍 检查项目结构...${NC}"

    if [ ! -d "$I18N_DIR" ]; then
        echo -e "${RED}❌ 中心化i18n目录不存在: $I18N_DIR${NC}"
        return 1
    fi

    if [ ! -d "$I18N_DIR/locales" ]; then
        echo -e "${RED}❌ 翻译文件目录不存在: $I18N_DIR/locales${NC}"
        return 1
    fi

    if [ ! -f "$I18N_DIR/scripts/validate.js" ]; then
        echo -e "${RED}❌ 验证脚本不存在: $I18N_DIR/scripts/validate.js${NC}"
        return 1
    fi

    echo -e "${GREEN}✅ 项目结构检查通过${NC}"
    return 0
}

# 验证翻译文件
validate_translations() {
    echo -e "\n${BLUE}🔍 验证翻译文件...${NC}"

    cd "$I18N_DIR"

    if [ ! -f "package.json" ]; then
        echo -e "${YELLOW}⚠️ 未找到package.json，尝试初始化...${NC}"
        npm init -y > /dev/null 2>&1
    fi

    # 检查依赖
    if [ ! -d "node_modules" ] || [ ! -f "node_modules/ajv/package.json" ]; then
        echo -e "${YELLOW}⚠️ 安装验证依赖...${NC}"
        npm install ajv > /dev/null 2>&1
    fi

    # 运行验证脚本
    if node scripts/validate.js; then
        echo -e "${GREEN}✅ 翻译文件验证通过${NC}"
        return 0
    else
        echo -e "${RED}❌ 翻译文件验证失败${NC}"
        return 1
    fi
}

# 检查同步状态
check_sync_status() {
    echo -e "\n${BLUE}🔄 检查同步状态...${NC}"

    cd "$I18N_DIR"

    # 创建临时备份
    local temp_dir=$(mktemp -d)
    cp -r locales "$temp_dir/locales.backup" 2>/dev/null || true

    # 重新提取和同步
    if node scripts/extract.js > /dev/null 2>&1 && node scripts/sync.js --force > /dev/null 2>&1; then
        # 检查是否有变化
        if diff -r locales "$temp_dir/locales.backup" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ 翻译文件已同步${NC}"
            rm -rf "$temp_dir"
            return 0
        else
            echo -e "${YELLOW}⚠️ 翻译文件需要同步${NC}"
            echo -e "${BLUE}建议运行以下命令：${NC}"
            echo "  cd i18n"
            echo "  node scripts/extract.js"
            echo "  node scripts/sync.js"

            # 恢复原始文件
            cp -r "$temp_dir/locales.backup/"* locales/ 2>/dev/null || true
            rm -rf "$temp_dir"
            return 1
        fi
    else
        echo -e "${RED}❌ 同步检查失败${NC}"
        rm -rf "$temp_dir"
        return 1
    fi
}

# 检查代码中的硬编码字符串
check_hardcoded_strings() {
    echo -e "\n${BLUE}🔍 检查硬编码字符串...${NC}"

    local warning_count=0

    # 检查React组件中的中文字符
    local chinese_files=$(git diff --cached --name-only | grep -E "\.(tsx|jsx)$" | xargs grep -l "[\u4e00-\u9fff]" 2>/dev/null || true)

    if [ -n "$chinese_files" ]; then
        echo -e "${YELLOW}⚠️ 发现可能的中文硬编码字符串：${NC}"
        echo "$chinese_files" | head -5
        if [ $(echo "$chinese_files" | wc -l) -gt 5 ]; then
            echo "  ... 还有$(( $(echo "$chinese_files" | wc -l) - 5 ))个文件"
        fi
        warning_count=$((warning_count + 1))
    fi

    # 检查是否使用了翻译函数
    local changed_files=$(git diff --cached --name-only | grep -E "\.(tsx|jsx)$")
    if [ -n "$changed_files" ]; then
        local files_without_t_function=""
        for file in $changed_files; do
            if [ -f "$file" ] && grep -q "[\u4e00-\u9fff]" "$file" && ! grep -q "useTranslation\|t(" "$file"; then
                files_without_t_function="$files_without_t_function\n  $file"
            fi
        done

        if [ -n "$files_without_t_function" ]; then
            echo -e "${YELLOW}⚠️ 以下文件包含中文但未使用翻译函数：${NC}"
            echo -e "$files_without_t_function"
            warning_count=$((warning_count + 1))
        fi
    fi

    if [ $warning_count -eq 0 ]; then
        echo -e "${GREEN}✅ 未发现明显的硬编码字符串${NC}"
    else
        echo -e "${YELLOW}⚠️ 发现 $warning_count 个潜在问题，建议检查${NC}"
    fi

    return 0  # 不阻止提交，只是警告
}

# 主执行流程
main() {
    local exit_code=0

    # 执行所有检查
    check_structure || exit_code=1
    validate_translations || exit_code=1
    check_sync_status || exit_code=1
    check_hardcoded_strings || true  # 不影响退出代码

    echo ""
    echo "================================"

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ 所有i18n检查通过，可以提交${NC}"
    else
        echo -e "${RED}❌ i18n检查失败，请修复后再提交${NC}"
        echo ""
        echo -e "${BLUE}💡 提示：${NC}"
        echo "1. 运行 'node i18n/scripts/validate.js' 查看详细错误"
        echo "2. 运行 'node i18n/scripts/sync.js' 同步翻译文件"
        echo "3. 确保所有用户可见文本使用翻译键而非硬编码"
    fi

    return $exit_code
}

# 如果是被直接调用（不是source），则执行主函数
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi
