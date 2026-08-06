"""
国际化核心模块

提供多语言支持，包括：
- 语言检测和解析
- 多语言内容处理
- 语言偏好管理
"""

from dataclasses import dataclass

SUPPORTED_LANGUAGES: dict[str, str] = {
    "zh": "简体中文",
    "en": "English",
    "ja": "日本語",
    "zh_Hant": "繁體中文",
}

LANGUAGE_CODES: list[str] = list(SUPPORTED_LANGUAGES.keys())

DEFAULT_LANGUAGE: str = "zh"

LANGUAGE_ALIASES: dict[str, str] = {
    "zh-cn": "zh",
    "zh-CN": "zh",
    "zh_cn": "zh",
    "zh_CN": "zh",
    "zh-tw": "zh_Hant",
    "zh-TW": "zh_Hant",
    "zh_tw": "zh_Hant",
    "zh_TW": "zh_Hant",
    "zh-hant": "zh_Hant",
    "zh-Hant": "zh_Hant",
    "zh_hant": "zh_Hant",
    "zh_Hant": "zh_Hant",
    "zh-hans": "zh",
    "zh-Hans": "zh",
    "zh_hans": "zh",
    "zh_Hans": "zh",
    "ja": "ja",
    "jp": "ja",
    "en": "en",
    "en-us": "en",
    "en-US": "en",
    "en_us": "en",
    "en_US": "en",
    "en-gb": "en",
    "en-GB": "en",
    "en_gb": "en",
    "en_GB": "en",
}


@dataclass
class I18nField:
    """
    国际化字段数据结构

    用于存储和访问多语言内容
    """

    zh: str = ""
    en: str = ""
    ja: str = ""
    zh_Hant: str = ""

    def get(self, lang: str, fallback: bool = True) -> str:
        """
        获取指定语言的内容

        Args:
            lang: 语言代码
            fallback: 是否回退到默认语言

        Returns:
            对应语言的内容
        """
        normalized_lang = normalize_language(lang)
        value = getattr(self, normalized_lang, "")

        if value:
            return value

        if fallback:
            if self.zh:
                return self.zh
            for code in LANGUAGE_CODES:
                val = getattr(self, code, "")
                if val:
                    return val

        return ""

    def set(self, lang: str, value: str) -> None:
        """
        设置指定语言的内容

        Args:
            lang: 语言代码
            value: 内容值
        """
        normalized_lang = normalize_language(lang)
        if hasattr(self, normalized_lang):
            setattr(self, normalized_lang, value)

    def to_dict(self) -> dict[str, str]:
        """转换为字典格式"""
        return {
            "zh": self.zh,
            "en": self.en,
            "ja": self.ja,
            "zh_Hant": self.zh_Hant,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str] | None) -> "I18nField":
        """从字典创建实例"""
        if not data:
            return cls()
        return cls(
            zh=data.get("zh", ""),
            en=data.get("en", ""),
            ja=data.get("ja", ""),
            zh_Hant=data.get("zh_Hant", ""),
        )

    def is_empty(self) -> bool:
        """检查是否所有语言都为空"""
        return not any([self.zh, self.en, self.ja, self.zh_Hant])

    def available_languages(self) -> list[str]:
        """获取有内容的语言列表"""
        return [lang for lang in LANGUAGE_CODES if getattr(self, lang, "")]


def normalize_language(lang: str | None) -> str:
    """
    标准化语言代码

    将各种形式的语言代码转换为标准格式

    Args:
        lang: 原始语言代码

    Returns:
        标准化的语言代码
    """
    if not lang:
        return DEFAULT_LANGUAGE

    if lang in LANGUAGE_CODES:
        return lang

    if lang in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[lang]

    lang_lower = lang.lower()
    if lang_lower in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[lang_lower]

    # 规范化分隔符：把下划线统一成连字符再尝试匹配
    lang_norm_sep = lang.replace("_", "-")
    if lang_norm_sep in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[lang_norm_sep]
    lang_norm_sep_lower = lang_norm_sep.lower()
    if lang_norm_sep_lower in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[lang_norm_sep_lower]

    # 对于 zh-* 或 zh_* 系列，根据后缀判断简繁
    base_first = lang.split("-")[0].split("_")[0]
    if base_first == "zh":
        # 检查是否包含繁体标识（tw / hk / mo / hant）
        lang_sub = (lang.lower() + "_")
        if "tw" in lang_sub or "hk" in lang_sub or "mo" in lang_sub or "hant" in lang_sub:
            return "zh_Hant"
        return "zh"

    if base_first in LANGUAGE_CODES:
        return base_first

    return DEFAULT_LANGUAGE


def parse_accept_language(accept_language: str | None) -> str:
    """
    解析 HTTP Accept-Language 头

    Args:
        accept_language: Accept-Language 头的值

    Returns:
        最匹配的语言代码
    """
    if not accept_language:
        return DEFAULT_LANGUAGE

    languages: list[tuple] = []

    for part in accept_language.split(","):
        part = part.strip()
        if not part:
            continue

        if ";" in part:
            lang, q_str = part.split(";", 1)
            try:
                q = float(q_str.strip().split("=")[1])
            except (IndexError, ValueError):
                q = 1.0
        else:
            lang = part
            q = 1.0

        languages.append((lang.strip(), q))

    languages.sort(key=lambda x: x[1], reverse=True)

    for lang, _ in languages:
        normalized = normalize_language(lang)
        if normalized in LANGUAGE_CODES:
            return normalized

    return DEFAULT_LANGUAGE


def get_language_from_request(
    request: "Request | None" = None,
    lang_param: str | None = None,
) -> str:
    """
    统一从请求中获取语言偏好

    优先级:
    1. 显式传入的 lang 查询参数
    2. rosetta_lang Cookie（前端切换语言后写入，持久化）
    3. Accept-Language 请求头
    4. 默认语言 DEFAULT_LANGUAGE
    """
    # 1. 显式参数
    if lang_param:
        return normalize_language(lang_param)

    # 2. Cookie
    if request is not None:
        cookie_lang = request.cookies.get("rosetta_lang")
        if cookie_lang:
            normalized = normalize_language(cookie_lang)
            if normalized in LANGUAGE_CODES:
                return normalized

    # 3. Accept-Language 头
    if request is not None:
        accept_language = request.headers.get("Accept-Language")
        if accept_language:
            return parse_accept_language(accept_language)

    # 4. 默认
    return DEFAULT_LANGUAGE


def get_i18n_value(data: dict[str, str] | None, lang: str, fallback: bool = True) -> str:
    """
    从多语言字典中获取指定语言的值

    Args:
        data: 多语言数据字典
        lang: 目标语言代码
        fallback: 是否回退到默认语言

    Returns:
        对应语言的内容
    """
    if not data:
        return ""

    normalized_lang = normalize_language(lang)

    if data.get(normalized_lang):
        return data[normalized_lang]

    if fallback:
        if data.get(DEFAULT_LANGUAGE):
            return data[DEFAULT_LANGUAGE]
        for code in LANGUAGE_CODES:
            if data.get(code):
                return data[code]

    return ""


def set_i18n_value(data: dict[str, str], lang: str, value: str) -> dict[str, str]:
    """
    设置多语言字典中指定语言的值

    Args:
        data: 多语言数据字典
        lang: 目标语言代码
        value: 内容值

    Returns:
        更新后的字典
    """
    normalized_lang = normalize_language(lang)
    data[normalized_lang] = value
    return data


def create_i18n_dict(zh: str = "", en: str = "", ja: str = "", zh_Hant: str = "") -> dict[str, str]:
    """
    创建多语言字典

    Args:
        zh: 中文内容
        en: 英文内容
        ja: 日文内容
        zh_Hant: 繁体中文内容

    Returns:
        多语言字典
    """
    result: dict[str, str] = {}
    if zh:
        result["zh"] = zh
    if en:
        result["en"] = en
    if ja:
        result["ja"] = ja
    if zh_Hant:
        result["zh_Hant"] = zh_Hant
    return result


def merge_i18n_dicts(base: dict[str, str], override: dict[str, str]) -> dict[str, str]:
    """
    合并两个多语言字典

    Args:
        base: 基础字典
        override: 覆盖字典

    Returns:
        合并后的字典
    """
    result = base.copy()
    for lang, value in override.items():
        if value:
            result[lang] = value
    return result


class I18nContext:
    """
    国际化上下文

    用于在请求处理过程中传递语言偏好
    """

    _current_lang: str = DEFAULT_LANGUAGE

    @classmethod
    def set_language(cls, lang: str) -> None:
        """设置当前语言"""
        cls._current_lang = normalize_language(lang)

    @classmethod
    def get_language(cls) -> str:
        """获取当前语言"""
        return cls._current_lang

    @classmethod
    def reset(cls) -> None:
        """重置为默认语言"""
        cls._current_lang = DEFAULT_LANGUAGE


TRANSLATIONS: dict[str, dict[str, str]] = {
    "oobe_invalid_env": {
        "zh": "无效的环境类型",
        "en": "Invalid environment type",
        "ja": "無効な環境タイプです",
        "zh_Hant": "無效的環境類型",
    },
    "oobe_db_user_empty": {
        "zh": "数据库用户名不能为空",
        "en": "Database username cannot be empty",
        "ja": "データベースユーザー名は空にできません",
        "zh_Hant": "資料庫使用者名稱不能為空",
    },
    "oobe_db_name_empty": {
        "zh": "数据库名称不能为空",
        "en": "Database name cannot be empty",
        "ja": "データベース名は空にできません",
        "zh_Hant": "資料庫名稱不能為空",
    },
    "oobe_sqlite_no_test": {
        "zh": "SQLite 无需网络连接，将在安装时自动创建",
        "en": "SQLite does not require network connection, it will be created automatically during installation",
        "ja": "SQLite はネットワーク接続不要で、インストール時に自動作成されます",
        "zh_Hant": "SQLite 無需網路連線，將在安裝時自動建立",
    },
    "oobe_db_connection_success": {
        "zh": "数据库连接成功",
        "en": "Database connection successful",
        "ja": "データベース接続に成功しました",
        "zh_Hant": "資料庫連線成功",
    },
    "oobe_db_connection_failed": {
        "zh": "数据库连接失败",
        "en": "Database connection failed",
        "ja": "データベース接続に失敗しました",
        "zh_Hant": "資料庫連線失敗",
    },
    "oobe_site_name_empty": {
        "zh": "站点名称不能为空",
        "en": "Site name cannot be empty",
        "ja": "サイト名は空にできません",
        "zh_Hant": "網站名稱不能為空",
    },
    "oobe_site_email_empty": {
        "zh": "联系邮箱不能为空",
        "en": "Contact email cannot be empty",
        "ja": "連絡先メールは空にできません",
        "zh_Hant": "聯絡信箱不能為空",
    },
    "oobe_username_min": {
        "zh": "用户名至少3位",
        "en": "Username must be at least 3 characters",
        "ja": "ユーザー名は3文字以上である必要があります",
        "zh_Hant": "使用者名稱至少3位",
    },
    "oobe_username_max": {
        "zh": "用户名最多20位",
        "en": "Username cannot exceed 20 characters",
        "ja": "ユーザー名は20文字以下である必要があります",
        "zh_Hant": "使用者名稱最多20位",
    },
    "oobe_username_invalid": {
        "zh": "只能包含字母、数字、下划线和连字符",
        "en": "Can only contain letters, numbers, underscores, and hyphens",
        "ja": "文字、数字、アンダースコア、ハイフンのみ使用できます",
        "zh_Hant": "只能包含字母、數字、底線和連字號",
    },
    "oobe_password_min": {
        "zh": "密码至少8位",
        "en": "Password must be at least 8 characters",
        "ja": "パスワードは8文字以上である必要があります",
        "zh_Hant": "密碼至少8位",
    },
    "oobe_upload_image_only": {
        "zh": "请上传图片文件",
        "en": "Please upload an image file",
        "ja": "画像ファイルをアップロードしてください",
        "zh_Hant": "請上傳圖片檔案",
    },
    "oobe_file_too_large": {
        "zh": "文件大小超过限制 (最大 5MB)",
        "en": "File size exceeds limit (max 5MB)",
        "ja": "ファイルサイズが制限を超えています（最大5MB）",
        "zh_Hant": "檔案大小超過限制 (最大 5MB)",
    },
    "oobe_admin_not_created": {
        "zh": "请先创建管理员账户",
        "en": "Please create an admin account first",
        "ja": "最初に管理者アカウントを作成してください",
        "zh_Hant": "請先建立管理員帳戶",
    },
    "oobe_complete_success": {
        "zh": "配置完成！",
        "en": "Configuration complete!",
        "ja": "設定が完了しました！",
        "zh_Hant": "設定完成！",
    },
    "oobe_complete_failed": {
        "zh": "配置失败",
        "en": "Configuration failed",
        "ja": "設定に失敗しました",
        "zh_Hant": "設定失敗",
    },
    "oobe_reset_success": {
        "zh": "OOBE 状态已重置",
        "en": "OOBE state has been reset",
        "ja": "OOBE 状態がリセットされました",
        "zh_Hant": "OOBE 狀態已重設",
    },
    "oobe_already_complete": {
        "zh": "OOBE 已完成，无需再次配置",
        "en": "OOBE is already complete, no need to configure again",
        "ja": "OOBE は既に完了しています。再設定する必要はありません",
        "zh_Hant": "OOBE 已完成，無需再次配置",
    },
    "validation_error": {
        "zh": "请求参数验证失败",
        "en": "Request validation failed",
        "ja": "リクエストパラメータの検証に失敗しました",
        "zh_Hant": "請求參數驗證失敗",
    },
    "internal_server_error": {
        "zh": "服务器内部错误",
        "en": "Internal server error",
        "ja": "サーバー内部エラー",
        "zh_Hant": "伺服器內部錯誤",
    },
}


def t(key: str, lang: str | None = None, **kwargs) -> str:
    """
    获取翻译消息

    Args:
        key: 翻译键
        lang: 目标语言（默认为当前上下文语言）
        **kwargs: 格式化参数

    Returns:
        翻译后的消息
    """
    if lang is None:
        lang = I18nContext.get_language()

    normalized_lang = normalize_language(lang)
    translations = TRANSLATIONS.get(key, {})

    result = translations.get(normalized_lang, "")
    if not result:
        result = translations.get(DEFAULT_LANGUAGE, key)
    if not result:
        result = key

    if kwargs:
        try:
            return result.format(**kwargs)
        except (KeyError, IndexError):
            return result

    return result
