"""
Rosetta FastAPI 后端 - API 路由模块
"""

from backend.api.blog import router as blog_router
from backend.api.core import router as core_router
from backend.api.guestbook import router as guestbook_router
from backend.api.messages import router as messages_router
from backend.api.users import router as users_router
from backend.api.voting import router as voting_router

__all__ = [
    "users_router",
    "blog_router",
    "core_router",
    "voting_router",
    "guestbook_router",
    "messages_router",
]
