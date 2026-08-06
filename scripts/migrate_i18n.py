"""
数据库迁移脚本：将现有数据转换为国际化格式

此脚本将：
1. 备份现有数据库
2. 将单语言字段转换为多语言 JSON 格式
3. 验证迁移结果

使用方法：
    python scripts/migrate_i18n.py
"""

import asyncio
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.config import settings


async def backup_database():
    """备份数据库"""
    db_path = Path(settings.database_url.replace("sqlite+aiosqlite:///", ""))
    if not db_path.exists():
        print("数据库文件不存在，跳过备份")
        return None

    backup_path = db_path.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
    shutil.copy2(db_path, backup_path)
    print(f"数据库已备份到: {backup_path}")
    return backup_path


async def migrate_posts(session: AsyncSession):
    """迁移文章数据"""
    print("正在迁移文章数据...")

    result = await session.execute(
        text(
            "SELECT id, title, subtitle, content, excerpt, meta_title, meta_description, meta_keywords FROM posts"
        )
    )
    posts = result.fetchall()

    for post in posts:
        post_id = post[0]

        title_i18n = json.dumps({"zh": post[1] or ""}, ensure_ascii=False)
        subtitle_i18n = json.dumps({"zh": post[2] or ""}, ensure_ascii=False) if post[2] else None
        content_i18n = json.dumps({"zh": post[3] or ""}, ensure_ascii=False)
        excerpt_i18n = json.dumps({"zh": post[4] or ""}, ensure_ascii=False) if post[4] else None
        meta_title_i18n = json.dumps({"zh": post[5] or ""}, ensure_ascii=False) if post[5] else None
        meta_description_i18n = (
            json.dumps({"zh": post[6] or ""}, ensure_ascii=False) if post[6] else None
        )
        meta_keywords_i18n = (
            json.dumps({"zh": post[7] or ""}, ensure_ascii=False) if post[7] else None
        )

        await session.execute(
            text("""
                UPDATE posts
                SET title = :title,
                    subtitle = :subtitle,
                    content = :content,
                    excerpt = :excerpt,
                    meta_title = :meta_title,
                    meta_description = :meta_description,
                    meta_keywords = :meta_keywords
                WHERE id = :id
            """),
            {
                "id": post_id,
                "title": title_i18n,
                "subtitle": subtitle_i18n,
                "content": content_i18n,
                "excerpt": excerpt_i18n,
                "meta_title": meta_title_i18n,
                "meta_description": meta_description_i18n,
                "meta_keywords": meta_keywords_i18n,
            },
        )

    print(f"已迁移 {len(posts)} 篇文章")
    return len(posts)


async def migrate_categories(session: AsyncSession):
    """迁移分类数据"""
    print("正在迁移分类数据...")

    result = await session.execute(text("SELECT id, name, description FROM categories"))
    categories = result.fetchall()

    for cat in categories:
        cat_id = cat[0]

        name_i18n = json.dumps({"zh": cat[1] or ""}, ensure_ascii=False)
        description_i18n = json.dumps({"zh": cat[2] or ""}, ensure_ascii=False) if cat[2] else None

        await session.execute(
            text("""
                UPDATE categories
                SET name = :name,
                    description = :description
                WHERE id = :id
            """),
            {
                "id": cat_id,
                "name": name_i18n,
                "description": description_i18n,
            },
        )

    print(f"已迁移 {len(categories)} 个分类")
    return len(categories)


async def migrate_tags(session: AsyncSession):
    """迁移标签数据"""
    print("正在迁移标签数据...")

    result = await session.execute(text("SELECT id, name FROM tags"))
    tags = result.fetchall()

    for tag in tags:
        tag_id = tag[0]

        name_i18n = json.dumps({"zh": tag[1] or ""}, ensure_ascii=False)

        await session.execute(
            text("""
                UPDATE tags 
                SET name = :name
                WHERE id = :id
            """),
            {
                "id": tag_id,
                "name": name_i18n,
            },
        )

    print(f"已迁移 {len(tags)} 个标签")
    return len(tags)


async def migrate_pages(session: AsyncSession):
    """迁移页面数据"""
    print("正在迁移页面数据...")

    result = await session.execute(text("SELECT id, title, content FROM pages"))
    pages = result.fetchall()

    for page in pages:
        page_id = page[0]

        title_i18n = json.dumps({"zh": page[1] or ""}, ensure_ascii=False)
        content_i18n = json.dumps({"zh": page[2] or ""}, ensure_ascii=False)

        await session.execute(
            text("""
                UPDATE pages 
                SET title = :title, 
                    content = :content
                WHERE id = :id
            """),
            {
                "id": page_id,
                "title": title_i18n,
                "content": content_i18n,
            },
        )

    print(f"已迁移 {len(pages)} 个页面")
    return len(pages)


async def migrate_navigations(session: AsyncSession):
    """迁移导航数据"""
    print("正在迁移导航数据...")

    result = await session.execute(text("SELECT id, title FROM navigations"))
    navigations = result.fetchall()

    for nav in navigations:
        nav_id = nav[0]

        title_i18n = json.dumps({"zh": nav[1] or ""}, ensure_ascii=False)

        await session.execute(
            text("""
                UPDATE navigations 
                SET title = :title
                WHERE id = :id
            """),
            {
                "id": nav_id,
                "title": title_i18n,
            },
        )

    print(f"已迁移 {len(navigations)} 个导航")
    return len(navigations)


async def migrate_friend_links(session: AsyncSession):
    """迁移友链数据"""
    print("正在迁移友链数据...")

    result = await session.execute(text("SELECT id, name, description FROM friend_links"))
    links = result.fetchall()

    for link in links:
        link_id = link[0]

        name_i18n = json.dumps({"zh": link[1] or ""}, ensure_ascii=False)
        description_i18n = (
            json.dumps({"zh": link[2] or ""}, ensure_ascii=False) if link[2] else None
        )

        await session.execute(
            text("""
                UPDATE friend_links 
                SET name = :name, 
                    description = :description
                WHERE id = :id
            """),
            {
                "id": link_id,
                "name": name_i18n,
                "description": description_i18n,
            },
        )

    print(f"已迁移 {len(links)} 个友链")
    return len(links)


async def migrate_search_placeholders(session: AsyncSession):
    """迁移搜索占位符数据"""
    print("正在迁移搜索占位符数据...")

    result = await session.execute(text("SELECT id, text FROM search_placeholders"))
    placeholders = result.fetchall()

    for ph in placeholders:
        ph_id = ph[0]

        text_i18n = json.dumps({"zh": ph[1] or ""}, ensure_ascii=False)

        await session.execute(
            text("""
                UPDATE search_placeholders 
                SET text = :text
                WHERE id = :id
            """),
            {
                "id": ph_id,
                "text": text_i18n,
            },
        )

    print(f"已迁移 {len(placeholders)} 个搜索占位符")
    return len(placeholders)


async def migrate_notifications(session: AsyncSession):
    """迁移通知数据"""
    print("正在迁移通知数据...")

    result = await session.execute(text("SELECT id, title, message FROM notifications"))
    notifications = result.fetchall()

    for notif in notifications:
        notif_id = notif[0]

        title_i18n = json.dumps({"zh": notif[1] or ""}, ensure_ascii=False)
        message_i18n = json.dumps({"zh": notif[2] or ""}, ensure_ascii=False)

        await session.execute(
            text("""
                UPDATE notifications 
                SET title = :title, 
                    message = :message
                WHERE id = :id
            """),
            {
                "id": notif_id,
                "title": title_i18n,
                "message": message_i18n,
            },
        )

    print(f"已迁移 {len(notifications)} 个通知")
    return len(notifications)


async def verify_migration(session: AsyncSession):
    """验证迁移结果"""
    print("\n验证迁移结果...")

    tables = [
        ("posts", "title"),
        ("categories", "name"),
        ("tags", "name"),
        ("pages", "title"),
        ("navigations", "title"),
        ("friend_links", "name"),
        ("search_placeholders", "text"),
        ("notifications", "title"),
    ]

    all_valid = True
    for table, column in tables:
        try:
            result = await session.execute(text(f"SELECT id, {column} FROM {table} LIMIT 1"))
            row = result.fetchone()
            if row:
                try:
                    data = json.loads(row[1])
                    if "zh" in data:
                        print(f"  ✓ {table}.{column}: 格式正确")
                    else:
                        print(f"  ✗ {table}.{column}: 缺少 zh 字段")
                        all_valid = False
                except json.JSONDecodeError:
                    print(f"  ✗ {table}.{column}: JSON 解析失败")
                    all_valid = False
        except Exception as e:
            print(f"  - {table}.{column}: 表不存在或为空")

    return all_valid


async def main():
    """主迁移函数"""
    print("=" * 60)
    print("Rosetta 国际化数据迁移脚本")
    print("=" * 60)
    print(f"数据库: {settings.database_url}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        backup_path = await backup_database()

        async with async_session() as session:
            async with session.begin():
                print("\n开始数据迁移...\n")

                total = 0
                total += await migrate_posts(session)
                total += await migrate_categories(session)
                total += await migrate_tags(session)
                total += await migrate_pages(session)
                total += await migrate_navigations(session)
                total += await migrate_friend_links(session)
                total += await migrate_search_placeholders(session)
                total += await migrate_notifications(session)

                print(f"\n总计迁移 {total} 条记录")

                is_valid = await verify_migration(session)

                if is_valid:
                    print("\n✓ 迁移验证通过")
                else:
                    print("\n✗ 迁移验证失败，请检查数据")
                    if backup_path:
                        print(f"可以从备份恢复: {backup_path}")

        print("\n" + "=" * 60)
        print("迁移完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n迁移失败: {e}")
        import traceback

        traceback.print_exc()
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
