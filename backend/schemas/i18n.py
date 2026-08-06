"""
国际化相关的 Pydantic 模式

定义多语言字段的请求和响应模型。
"""

from pydantic import BaseModel, Field


class I18nTextBase(BaseModel):
    """
    多语言文本基础模型

    支持中文、英文、日语、繁体中文四种语言
    """

    zh: str = Field(default="", description="中文内容")
    en: str = Field(default="", description="英文内容")
    ja: str = Field(default="", description="日语内容")
    zh_Hant: str = Field(default="", description="繁体中文内容")

    def to_dict(self) -> dict[str, str]:
        """转换为字典，只包含非空值"""
        result = {}
        if self.zh:
            result["zh"] = self.zh
        if self.en:
            result["en"] = self.en
        if self.ja:
            result["ja"] = self.ja
        if self.zh_Hant:
            result["zh_Hant"] = self.zh_Hant
        return result

    @classmethod
    def from_dict(cls, data: dict[str, str] | None) -> "I18nTextBase":
        """从字典创建实例"""
        if not data:
            return cls()
        return cls(
            zh=data.get("zh", ""),
            en=data.get("en", ""),
            ja=data.get("ja", ""),
            zh_Hant=data.get("zh_Hant", ""),
        )

    def get(self, lang: str, fallback: bool = True) -> str:
        """
        获取指定语言的内容

        Args:
            lang: 语言代码
            fallback: 是否回退到默认语言
        """
        normalized_lang = lang
        if lang in ["zh-cn", "zh-CN", "zh-hans", "zh-Hans"]:
            normalized_lang = "zh"
        elif lang in ["zh-tw", "zh-TW", "zh-hant", "zh-Hant"]:
            normalized_lang = "zh_Hant"
        elif lang in ["jp"]:
            normalized_lang = "ja"
        elif lang in ["en-us", "en-US", "en-gb", "en-GB"]:
            normalized_lang = "en"

        value = getattr(self, normalized_lang, "")
        if value:
            return value

        if fallback:
            if self.zh:
                return self.zh
            for field in ["en", "ja", "zh_Hant"]:
                val = getattr(self, field, "")
                if val:
                    return val

        return ""


class I18nTextCreate(BaseModel):
    """
    多语言文本创建模型

    创建时至少需要提供中文内容
    """

    zh: str = Field(..., min_length=1, description="中文内容（必填）")
    en: str = Field(default="", description="英文内容")
    ja: str = Field(default="", description="日语内容")
    zh_Hant: str = Field(default="", description="繁体中文内容")


class I18nTextOptional(BaseModel):
    """
    多语言文本可选模型

    用于更新操作，所有字段都是可选的
    """

    zh: str | None = Field(None, description="中文内容")
    en: str | None = Field(None, description="英文内容")
    ja: str | None = Field(None, description="日语内容")
    zh_Hant: str | None = Field(None, description="繁体中文内容")

    def to_dict(self) -> dict[str, str]:
        """转换为字典，只包含非空值"""
        result = {}
        if self.zh is not None:
            result["zh"] = self.zh
        if self.en is not None:
            result["en"] = self.en
        if self.ja is not None:
            result["ja"] = self.ja
        if self.zh_Hant is not None:
            result["zh_Hant"] = self.zh_Hant
        return result


class I18nContentBase(BaseModel):
    """
    多语言内容基础模型

    用于长文本内容（如文章正文）
    """

    zh: str = Field(default="", description="中文内容")
    en: str = Field(default="", description="英文内容")
    ja: str = Field(default="", description="日语内容")
    zh_Hant: str = Field(default="", description="繁体中文内容")

    def to_dict(self) -> dict[str, str]:
        """转换为字典，只包含非空值"""
        result = {}
        if self.zh:
            result["zh"] = self.zh
        if self.en:
            result["en"] = self.en
        if self.ja:
            result["ja"] = self.ja
        if self.zh_Hant:
            result["zh_Hant"] = self.zh_Hant
        return result

    @classmethod
    def from_dict(cls, data: dict[str, str] | None) -> "I18nContentBase":
        """从字典创建实例"""
        if not data:
            return cls()
        return cls(
            zh=data.get("zh", ""),
            en=data.get("en", ""),
            ja=data.get("ja", ""),
            zh_Hant=data.get("zh_Hant", ""),
        )


class I18nContentCreate(BaseModel):
    """
    多语言内容创建模型

    创建时至少需要提供中文内容
    """

    zh: str = Field(..., min_length=1, description="中文内容（必填）")
    en: str = Field(default="", description="英文内容")
    ja: str = Field(default="", description="日语内容")
    zh_Hant: str = Field(default="", description="繁体中文内容")


class LanguageInfo(BaseModel):
    """
    语言信息模型

    用于返回支持的语言列表
    """

    code: str = Field(..., description="语言代码")
    name: str = Field(..., description="语言名称")
    native_name: str = Field(..., description="本地语言名称")


SUPPORTED_LANGUAGES_INFO = [
    LanguageInfo(code="zh", name="Chinese (Simplified)", native_name="简体中文"),
    LanguageInfo(code="en", name="English", native_name="English"),
    LanguageInfo(code="ja", name="Japanese", native_name="日本語"),
    LanguageInfo(code="zh_Hant", name="Chinese (Traditional)", native_name="繁體中文"),
]


import sys as _sys  # noqa: E402

_STRICT_EXTRA_FORBID = {"strict": True, "extra": "forbid"}
for _name in list(globals().keys()):
    _obj = globals()[_name]
    if (
        isinstance(_obj, type)
        and issubclass(_obj, BaseModel)
        and _obj is not BaseModel
        and _obj.__module__ == _sys.modules[__name__].__name__
    ):
        _existing = _obj.model_config if isinstance(_obj.model_config, dict) else {}
        _merged = {**_existing, **_STRICT_EXTRA_FORBID}
        try:
            _obj.model_config = _merged
        except Exception:
            pass
    del _name, _obj
