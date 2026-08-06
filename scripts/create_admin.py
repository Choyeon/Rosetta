#!/usr/bin/env python
"""
创建管理员账号脚本

用于创建超级管理员账号。支持交互式和命令行两种模式。

Usage:
    # 交互式创建
    python scripts/create_admin.py
    
    # 命令行参数创建
    python scripts/create_admin.py --username admin --email admin@example.com --password your_password
    
    # 从环境变量创建
    export ADMIN_USERNAME=admin
    export ADMIN_EMAIL=admin@example.com
    export ADMIN_PASSWORD=your_password
    python scripts/create_admin.py --from-env
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from getpass import getpass

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_password_hash
from backend.core.config import settings
from backend.core.database import async_session_maker, init_db
from backend.models.user import User, UserPreference


async def create_admin(
    username: str,
    email: str,
    password: str,
    nickname: str | None = None,
    superuser: bool = True,
) -> User:
    """
    创建管理员账号
    
    Args:
        username: 用户名
        email: 邮箱地址
        password: 密码
        nickname: 昵称（可选）
        superuser: 是否为超级管理员
    
    Returns:
        User: 创建的用户对象
    
    Raises:
        ValueError: 用户名或邮箱已存在
    """
    async with async_session_maker() as session:
        # 检查用户名是否已存在
        result = await session.execute(
            select(User).where(User.username == username)
        )
        if result.scalar_one_or_none():
            raise ValueError(f"用户名 '{username}' 已存在")

        # 检查邮箱是否已存在
        result = await session.execute(
            select(User).where(User.email == email)
        )
        if result.scalar_one_or_none():
            raise ValueError(f"邮箱 '{email}' 已存在")

        # 创建用户
        user = User(
            username=username,
            email=email,
            password_hash=get_password_hash(password),
            nickname=nickname or username,
            is_active=True,
            is_staff=True,
            is_superuser=superuser,
        )
        session.add(user)
        await session.flush()

        # 创建用户偏好设置
        preference = UserPreference(user_id=user.id)
        session.add(preference)

        await session.commit()
        await session.refresh(user)

        return user


def validate_password(password: str) -> bool:
    """
    验证密码强度
    
    密码要求：
    - 至少 8 个字符
    - 包含大小写字母
    - 包含数字
    
    Args:
        password: 密码
    
    Returns:
        bool: 密码是否符合要求
    """
    if len(password) < 8:
        print("❌ 密码长度必须至少 8 个字符")
        return False
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    
    if not (has_upper and has_lower and has_digit):
        print("❌ 密码必须包含大小写字母和数字")
        return False
    
    return True


def interactive_mode() -> tuple[str, str, str, str | None]:
    """
    交互式输入模式
    
    Returns:
        tuple: (username, email, password, nickname)
    """
    print("\n" + "=" * 50)
    print("  Rosetta 管理员账号创建")
    print("=" * 50 + "\n")

    # 用户名
    while True:
        username = input("请输入用户名: ").strip()
        if len(username) >= 3:
            break
        print("❌ 用户名长度必须至少 3 个字符")

    # 邮箱
    while True:
        email = input("请输入邮箱: ").strip()
        if "@" in email and "." in email:
            break
        print("❌ 请输入有效的邮箱地址")

    # 密码
    while True:
        password = getpass("请输入密码: ")
        if validate_password(password):
            confirm = getpass("请再次输入密码: ")
            if password == confirm:
                break
            print("❌ 两次输入的密码不一致")
    
    # 昵称（可选）
    nickname = input("请输入昵称（可选，直接回车跳过）: ").strip() or None

    return username, email, password, nickname


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="创建管理员账号",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 交互式创建
  python scripts/create_admin.py

  # 命令行参数创建
  python scripts/create_admin.py --username admin --email admin@example.com --password YourPassword123

  # 从环境变量创建
  python scripts/create_admin.py --from-env
        """,
    )
    parser.add_argument("--username", help="用户名")
    parser.add_argument("--email", help="邮箱地址")
    parser.add_argument("--password", help="密码")
    parser.add_argument("--nickname", help="昵称")
    parser.add_argument(
        "--from-env",
        action="store_true",
        help="从环境变量读取配置 (ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_PASSWORD)",
    )
    parser.add_argument(
        "--no-superuser",
        action="store_true",
        help="创建普通管理员而非超级管理员",
    )

    args = parser.parse_args()

    # 确定输入模式
    if args.from_env:
        username = os.environ.get("ADMIN_USERNAME")
        email = os.environ.get("ADMIN_EMAIL")
        password = os.environ.get("ADMIN_PASSWORD")
        nickname = os.environ.get("ADMIN_NICKNAME")

        if not all([username, email, password]):
            print("❌ 请设置环境变量: ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_PASSWORD")
            sys.exit(1)
    elif args.username and args.email and args.password:
        username = args.username
        email = args.email
        password = args.password
        nickname = args.nickname
    else:
        username, email, password, nickname = interactive_mode()

    # 初始化数据库
    print("\n正在初始化数据库...")
    await init_db()

    # 创建管理员
    print("正在创建管理员账号...")
    try:
        user = await create_admin(
            username=username,
            email=email,
            password=password,
            nickname=nickname,
            superuser=not args.no_superuser,
        )
        print("\n" + "=" * 50)
        print("✅ 管理员账号创建成功！")
        print("=" * 50)
        print(f"  用户名: {user.username}")
        print(f"  邮箱:   {user.email}")
        print(f"  昵称:   {user.display_name}")
        print(f"  权限:   {'超级管理员' if user.is_superuser else '管理员'}")
        print("=" * 50 + "\n")
    except ValueError as e:
        print(f"\n❌ 创建失败: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 创建失败: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
