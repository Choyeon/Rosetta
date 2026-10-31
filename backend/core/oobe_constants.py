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
# 这里只留「OOBE 真正写进数据库的 key 名映射」。
# 曾经还有一份 FEATURE_FLAGS / FEATURE_FLAG_DEFAULTS（十三个开关，含看板娘、追番、动漫、
# 侧边栏组件、公告栏……），全仓零引用，只有这张表在"声称这些能力存在"。它挡不住任何漂移，
# 反而让下一个照着清单接线的人去接一条后端根本没有的口子，所以随那几把无实现的假开关
# 一起退役（前因与边界写在 frontend/docs/API_COVERAGE.md 的「OOBE 幽灵开关」段，
# 守卫 tests/test_retired_oobe_ghost_flags_are_gone.py）。真正的能力开关清单是
# settings_groups._default_features()——每一把都有消费点。
FEATURE_FLAG_DB_KEY_MAP: dict[str, str] = {
    "enable_rss": "enable_rss_feed",
}

# OOBE 环境检测相关常量
OOBE_DISK_MIN_GB = 0.5
OOBE_MEM_MIN_MB = 512
