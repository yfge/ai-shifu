#!/usr/bin/env python3
"""
migrate_oss_url.py
------------------
将 ai-shifu 代码库中所有 resource.ai-shifu.{cn,com} 替换为 res.ai-shifu.{cn,com}

用法：
  # 预览变更（dry-run，默认）
  python3 scripts/migrate_oss_url.py

  # 实际写入
  python3 scripts/migrate_oss_url.py --apply

  # 指定目录（默认 src/）
  python3 scripts/migrate_oss_url.py --apply --root src/
"""

import argparse
import re
import sys
from pathlib import Path

# ── 替换规则 ───────────────────────────────────────────────────────────────
REPLACEMENTS = [
    # cn
    (r"https?://resource\.ai-shifu\.cn", "https://res.ai-shifu.cn"),
    # com
    (r"https?://resource\.ai-shifu\.com", "https://res.ai-shifu.com"),
]

# ── 目标文件扩展名 ─────────────────────────────────────────────────────────
TARGET_EXTS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".env",
    ".env.example",
    ".env.local",
    ".yaml",
    ".yml",
    ".json",
    ".md",
    ".txt",
    ".html",
}

# ── 排除目录 ──────────────────────────────────────────────────────────────
EXCLUDE_DIRS = {
    "__pycache__",
    "node_modules",
    ".git",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
}


def should_process(path: Path) -> bool:
    """判断文件是否需要处理"""
    # 排除目录
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return False
    # 无后缀的 .env 文件（精确匹配文件名）
    if path.name.startswith(".env"):
        return True
    return path.suffix in TARGET_EXTS


def migrate_content(content: str) -> tuple[str, list[tuple[int, str, str]]]:
    """执行替换，返回 (新内容, [(行号, 旧行, 新行), ...])"""
    lines = content.splitlines(keepends=True)
    changes = []
    new_lines = []
    for i, line in enumerate(lines, start=1):
        new_line = line
        for pattern, replacement in REPLACEMENTS:
            new_line = re.sub(pattern, replacement, new_line)
        if new_line != line:
            changes.append((i, line.rstrip("\n"), new_line.rstrip("\n")))
        new_lines.append(new_line)
    return "".join(new_lines), changes


def main():
    parser = argparse.ArgumentParser(
        description="Migrate OSS base URLs in ai-shifu repo"
    )
    parser.add_argument(
        "--apply", action="store_true", help="实际写入文件（默认 dry-run）"
    )
    parser.add_argument(
        "--root", default="src", help="扫描根目录（相对于脚本所在 repo 根）"
    )
    args = parser.parse_args()

    # repo 根目录 = 脚本的父目录
    repo_root = Path(__file__).parent.parent
    scan_root = repo_root / args.root

    if not scan_root.exists():
        print(f"[ERROR] 目录不存在: {scan_root}", file=sys.stderr)
        sys.exit(1)

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== OSS URL 迁移工具 [{mode}] ===")
    print(f"扫描目录: {scan_root}\n")

    total_files = 0
    total_changes = 0

    for path in sorted(scan_root.rglob("*")):
        if not path.is_file():
            continue
        if not should_process(path):
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        new_content, changes = migrate_content(content)
        if not changes:
            continue

        total_files += 1
        total_changes += len(changes)
        rel = path.relative_to(repo_root)
        print(f"📄 {rel}  ({len(changes)} 处)")
        for lineno, old, new in changes:
            print(f"   L{lineno:4d} - {old[:120]}")
            print(f"        + {new[:120]}")
        print()

        if args.apply:
            path.write_text(new_content, encoding="utf-8")

    print("─" * 60)
    print(f"共 {total_files} 个文件，{total_changes} 处变更", end="")
    if args.apply:
        print("  ✅ 已写入")
    else:
        print("  （dry-run，加 --apply 实际写入）")


if __name__ == "__main__":
    main()
