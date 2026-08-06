"""
OOBE 共享常量 — 校验规则、功能开关、路径供前后端对齐

所有 OOBE 相关的常量定义集中于此，避免散落在多个文件中。
"""

# ============ 校验规则 ============
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 20
USERNAME_PATTERN = r"^[A-Za-z0-9_-]{3,20}$"
USERNAME_DESCRIPTION = "3-20 位字母、数字、下划线或短横线"

PASSWORD_MIN_LENGTH = 8
PASSWORD_DESCRIPTION = f"密码至少 {PASSWORD_MIN_LENGTH} 位"

EMAIL_PATTERN = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"

# ============ 功能开关字段名 ============
# 单源真理：所有 feature flag 的 key 在此定义，前后端共用
FEATURE_FLAGS = {
    "enable_comments": "启用评论系统",
    "enable_registration": "启用用户注册",
    "enable_rss": "启用 RSS 订阅",
    "enable_bing_wallpaper": "启用 Bing 每日壁纸",
    "enable_pagefind_search": "启用 Pagefind 站内搜索",
    "enable_encrypted_posts": "启用加密文章",
    "enable_music_player": "启用音乐播放器",
    "enable_pio": "启用看板娘 (Live2D)",
    "enable_hero": "启用首页 Hero 区",
    "enable_announcement": "启用公告栏",
    "enable_friend_links": "启用友链页面",
    "enable_sidebar_widgets": "启用侧边栏组件",
    "enable_gallery": "启用相册",
    "enable_bangumi": "启用追番页面",
    "enable_anime": "启用动漫页面",
}

# 功能开关的默认值
FEATURE_FLAG_DEFAULTS: dict[str, bool] = {
    "enable_comments": True,
    "enable_registration": True,
    "enable_rss": True,
    "enable_bing_wallpaper": True,
    "enable_pagefind_search": True,
    "enable_encrypted_posts": False,
    "enable_music_player": False,
    "enable_pio": False,
    "enable_hero": False,
    "enable_announcement": False,
    "enable_friend_links": False,
    "enable_sidebar_widgets": False,
    "enable_gallery": False,
    "enable_bangumi": False,
    "enable_anime": False,
}

# 功能开关 → 数据库 key 映射（部分 key 在 DB 中名称不同）
FEATURE_FLAG_DB_KEY_MAP: dict[str, str] = {
    "enable_rss": "enable_rss_feed",
}

# OOBE 环境检测相关常量
OOBE_DISK_MIN_GB = 0.5
OOBE_MEM_MIN_MB = 512