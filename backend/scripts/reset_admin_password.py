"""
Force-reset (or bootstrap) the admin user's password without needing a valid login session.

If the users table is empty but OOBE already ran, we insert a super_admin row so the
frontend can log in. Use this as a recovery tool.

Usage (from project root):
    uv run python -m backend.scripts.reset_admin_password --username admin --password Choyeon@123
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime

from sqlalchemy import func, or_, select

from backend.core.auth import get_password_hash
from backend.core.database import async_session_maker
from backend.core.password_policy import validate_password
from backend.models.user import User
from backend.utils.compat import UTC

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("rosetta.reset_admin_password")


async def _do_reset(username: str, password: str, email: str) -> int:
    errors = validate_password(password)
    if errors:
        log.error("新密码不符合密码策略：%s", "; ".join(errors))
        return 2

    new_hash = get_password_hash(password)
    now = datetime.now(UTC)

    async with async_session_maker() as db:
        total = (await db.execute(select(func.count()).select_from(User))).scalar_one()
        row: User | None = (
            await db.execute(select(User).where(or_(User.username == username, User.email == username)))
        ).scalar_one_or_none()

        if row is None:
            row = (
                await db.execute(select(User).where(or_(User.role == "super_admin", User.is_staff.is_(True))))
            ).scalar_one_or_none()
            if row is None:
                if total == 0:
                    log.warning("users 表为空，OOBE 未写入管理员，正在插入 admin 超级管理员……")
                    row = User(
                        username=username,
                        email=email,
                        password_hash=new_hash,
                        nickname="Administrator",
                        role="super_admin",
                        is_staff=True,
                        is_superuser=True,
                        is_active=True,
                        is_banned=False,
                        token_version=1,
                        created_at=now,
                        updated_at=now,
                        site_id=1,
                    )
                    db.add(row)
                    await db.flush()
                    await db.commit()
                    await db.refresh(row)
                    log.info(
                        "已新建管理员账号：username=%s email=%s id=%s role=%s",
                        row.username,
                        row.email,
                        row.id,
                        row.role,
                    )
                    return 0
                log.error("未找到用户 %s，且系统中也不存在任何管理员账号。", username)
                return 3
            log.warning("未找到用户 %s，改为重置管理员账号: %s", username, row.username)

        row.password_hash = new_hash
        row.is_active = True
        row.is_banned = False
        row.updated_at = now
        # Ensure the user still has admin rights even if role was demoted.
        row.is_staff = True
        if row.role in {"subscriber", "contributor", "author", "editor"}:
            row.role = "admin"
        # Bump token version so any existing sessions are forced to re-login
        row.token_version = (getattr(row, "token_version", 0) or 0) + 1

        await db.flush()
        await db.commit()

    log.info(
        "已成功重置账号 %s (id=%s) 的密码，role=%s token_version=%s。",
        row.username,
        row.id,
        row.role,
        row.token_version,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="重置 Rosetta 管理员账号密码")
    parser.add_argument("--username", default="admin", help="用户名或邮箱，默认 admin")
    parser.add_argument("--password", default="Choyeon@123", help="新密码，默认 Choyeon@123")
    parser.add_argument("--email", default="admin@rosetta.local", help="若需要新建账号时使用的邮箱，默认 admin@rosetta.local")
    args = parser.parse_args()
    return asyncio.run(_do_reset(args.username, args.password, args.email))


if __name__ == "__main__":
    sys.exit(main())
