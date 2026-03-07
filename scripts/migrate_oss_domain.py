#!/usr/bin/env python3
"""
Migrate OSS domain names in the database.

Replaces occurrences of the old OSS base URLs with new ones across all
relevant tables and columns.

Default mapping (override via --old / --new for custom domains):
    https://resource.ai-shifu.cn  ->  ALIBABA_CLOUD_OSS_BASE_URL  (or --new-cn)
    https://resource.ai-shifu.com ->  ALIBABA_CLOUD_OSS_COURSES_URL (or --new-com)

Usage:
    # Dry run (show what would change, no writes)
    python scripts/migrate_oss_domain.py

    # Apply changes
    python scripts/migrate_oss_domain.py --apply

    # Custom domain mapping
    python scripts/migrate_oss_domain.py --apply \\
        --old-cn https://resource.ai-shifu.cn \\
        --new-cn https://res.ai-shifu.cn \\
        --old-com https://resource.ai-shifu.com \\
        --new-com https://res.ai-shifu.com

Environment variables (used when --new-cn / --new-com are not specified):
    ALIBABA_CLOUD_OSS_BASE_URL     -> replacement for .cn domain
    ALIBABA_CLOUD_OSS_COURSES_URL  -> replacement for .com domain
    DATABASE_URL                   -> SQLAlchemy connection string
                                      (falls back to individual DB_* vars)
    DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME
"""

import argparse
import os
import sys
from typing import Optional


def get_db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "3306")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    name = os.getenv("DB_NAME", "agiclass")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"


# ---------------------------------------------------------------------------
# Tables / columns that may contain OSS URLs
# Each entry: (table, column, is_like_content)
#   is_like_content=True  -> column may contain embedded URLs in larger text
#   is_like_content=False -> column stores a plain URL
# ---------------------------------------------------------------------------
TARGETS = [
    # course outline content (MarkdownFlow, may embed images)
    ("shifu_draft_outline_items",     "content",     True),
    ("shifu_published_outline_items", "content",     True),
    # course resource references
    ("scenario_resource",             "url",         False),
    # generic resource table
    ("resource",                      "url",         False),
    # TTS audio
    ("learn_generated_audios",        "oss_url",     False),
    # user avatar
    ("user_users",                    "avatar",      False),
]


def build_replacements(args: argparse.Namespace) -> list[tuple[str, str]]:
    """Return a list of (old, new) string pairs to replace."""
    pairs = []

    old_cn  = args.old_cn
    new_cn  = args.new_cn or os.getenv("ALIBABA_CLOUD_OSS_BASE_URL", "").rstrip("/")
    old_com = args.old_com
    new_com = args.new_com or os.getenv("ALIBABA_CLOUD_OSS_COURSES_URL", "").rstrip("/")

    if new_cn and new_cn != old_cn:
        pairs.append((old_cn.rstrip("/"), new_cn))
    if new_com and new_com != old_com:
        pairs.append((old_com.rstrip("/"), new_com))

    return pairs


def migrate(apply: bool, replacements: list[tuple[str, str]], db_url: str) -> None:
    try:
        import sqlalchemy as sa
    except ImportError:
        sys.exit("sqlalchemy is required: pip install sqlalchemy pymysql")

    engine = sa.create_engine(db_url, echo=False)
    total_rows = 0

    with engine.connect() as conn:
        for table, column, is_content in TARGETS:
            # Check table exists
            try:
                exists = conn.execute(
                    sa.text(f"SHOW TABLES LIKE :t"), {"t": table}
                ).fetchone()
            except Exception as e:
                print(f"  [skip] {table}: {e}")
                continue

            if not exists:
                print(f"  [skip] {table}.{column} — table not found")
                continue

            for old_url, new_url in replacements:
                # Count affected rows
                count_sql = sa.text(
                    f"SELECT COUNT(*) FROM `{table}` WHERE `{column}` LIKE :pat"
                )
                count = conn.execute(count_sql, {"pat": f"%{old_url}%"}).scalar()

                if count == 0:
                    continue

                print(
                    f"  {'[apply]' if apply else '[dry-run]'} "
                    f"{table}.{column}: {count} row(s)  "
                    f"{old_url!r} -> {new_url!r}"
                )

                if apply:
                    update_sql = sa.text(
                        f"UPDATE `{table}` SET `{column}` = "
                        f"REPLACE(`{column}`, :old, :new) "
                        f"WHERE `{column}` LIKE :pat"
                    )
                    conn.execute(update_sql, {
                        "old": old_url,
                        "new": new_url,
                        "pat": f"%{old_url}%",
                    })
                    conn.commit()

                total_rows += count

    if total_rows == 0:
        print("Nothing to migrate — no matching rows found.")
    else:
        action = "Updated" if apply else "Would update"
        print(f"\n{action} {total_rows} row(s) total.")
        if not apply:
            print("Run with --apply to commit changes.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="Write changes to the database (default: dry run)")
    parser.add_argument("--old-cn",  default="https://resource.ai-shifu.cn",  help="Old .cn OSS base URL")
    parser.add_argument("--new-cn",  default="",                               help="New .cn OSS base URL (overrides env)")
    parser.add_argument("--old-com", default="https://resource.ai-shifu.com", help="Old .com OSS base URL")
    parser.add_argument("--new-com", default="",                               help="New .com OSS base URL (overrides env)")
    parser.add_argument("--db-url",  default="",                               help="SQLAlchemy DB URL (overrides DATABASE_URL env)")
    args = parser.parse_args()

    db_url = args.db_url or get_db_url()
    replacements = build_replacements(args)

    if not replacements:
        sys.exit(
            "No replacement targets defined.\n"
            "Set ALIBABA_CLOUD_OSS_BASE_URL / ALIBABA_CLOUD_OSS_COURSES_URL "
            "or pass --new-cn / --new-com."
        )

    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"DB:   {db_url}")
    print(f"Replacements:")
    for old, new in replacements:
        print(f"  {old!r} -> {new!r}")
    print()

    migrate(args.apply, replacements, db_url)


if __name__ == "__main__":
    main()
