"""
翻译 API 路由

提供多语言翻译功能，支持一键翻译中文到其他语言。
"""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.core.auth import get_current_user
from backend.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/translate", tags=["翻译"])


class TranslateRequest(BaseModel):
    """翻译请求"""

    text: str = Field(..., min_length=1, max_length=10000, description="待翻译文本")
    source_lang: str = Field(default="zh", description="源语言")
    target_langs: list[str] = Field(default=["en", "ja", "zh_Hant"], description="目标语言列表")


class TranslateResponse(BaseModel):
    """翻译响应"""

    translations: dict[str, str] = Field(default_factory=dict, description="翻译结果")


LANG_NAMES = {
    "zh": "简体中文",
    "en": "English",
    "ja": "日本語",
    "zh_Hant": "繁體中文",
}

SIMPLIFIED_TO_TRADITIONAL = {
    "博客": "部落格",
    "文章": "文章",
    "分类": "分類",
    "标签": "標籤",
    "评论": "評論",
    "用户": "使用者",
    "设置": "設定",
    "搜索": "搜尋",
    "发布": "發布",
    "编辑": "編輯",
    "删除": "刪除",
    "保存": "儲存",
    "取消": "取消",
    "确认": "確認",
    "返回": "返回",
    "首页": "首頁",
    "管理": "管理",
    "登录": "登入",
    "注册": "註冊",
    "密码": "密碼",
    "邮箱": "電子郵件",
    "昵称": "暱稱",
    "头像": "頭像",
    "简介": "簡介",
    "网站": "網站",
    "链接": "連結",
    "图片": "圖片",
    "视频": "影片",
    "音频": "音訊",
    "文件": "檔案",
    "上传": "上傳",
    "下载": "下載",
    "导出": "匯出",
    "导入": "匯入",
    "数据": "資料",
    "系统": "系統",
    "配置": "配置",
    "状态": "狀態",
    "时间": "時間",
    "日期": "日期",
    "信息": "資訊",
    "消息": "訊息",
    "通知": "通知",
    "成功": "成功",
    "失败": "失敗",
    "错误": "錯誤",
    "警告": "警告",
    "提示": "提示",
    "帮助": "說明",
    "关于": "關於",
    "联系": "聯絡",
    "服务": "服務",
    "条款": "條款",
    "隐私": "隱私",
    "政策": "政策",
    "版权": "版權",
    "所有": "所有",
    " rights": " 權利",
    " reserved": " 保留",
}


def simple_zh_to_zh_hant(text: str) -> str:
    """简体中文转繁体中文（简单替换）"""
    result = text
    for simplified, traditional in SIMPLIFIED_TO_TRADITIONAL.items():
        result = result.replace(simplified, traditional)
    return result


async def translate_with_libretranslate(text: str, source: str, target: str) -> str:
    """使用 LibreTranslate API 进行翻译"""
    import aiohttp

    lang_map = {
        "zh": "zh",
        "en": "en",
        "ja": "ja",
        "zh_Hant": "zh",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://libretranslate.de/translate",
                json={
                    "q": text,
                    "source": lang_map.get(source, source),
                    "target": lang_map.get(target, target),
                    "format": "text",
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("translatedText", text)
    except Exception as e:
        logger.warning(f"LibreTranslate failed: {e}")

    return text


async def translate_with_mymemory(text: str, source: str, target: str) -> str:
    """使用 MyMemory API 进行翻译"""
    import aiohttp

    lang_map = {
        "zh": "zh-CN",
        "en": "en-GB",
        "ja": "ja-JP",
        "zh_Hant": "zh-TW",
    }

    source_code = lang_map.get(source, source)
    target_code = lang_map.get(target, target)

    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.mymemory.translated.net/get?q={text}&langpair={source_code}|{target_code}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("responseStatus") == 200:
                        return data.get("responseData", {}).get("translatedText", text)
    except Exception as e:
        logger.warning(f"MyMemory translation failed: {e}")

    return text


async def mock_translate(text: str, source: str, target: str) -> str:
    """模拟翻译（用于开发测试）"""
    await asyncio.sleep(0.3)

    if target == "zh_Hant":
        return simple_zh_to_zh_hant(text)

    mock_translations: dict[str, dict[str, str]] = {
        "en": {
            "博客": "Blog",
            "文章": "Article",
            "分类": "Category",
            "标签": "Tag",
            "评论": "Comment",
            "用户": "User",
            "设置": "Settings",
            "搜索": "Search",
            "发布": "Publish",
            "编辑": "Edit",
            "删除": "Delete",
            "保存": "Save",
            "取消": "Cancel",
            "确认": "Confirm",
            "返回": "Back",
            "首页": "Home",
            "管理": "Admin",
            "登录": "Login",
            "注册": "Register",
            "密码": "Password",
            "邮箱": "Email",
            "昵称": "Nickname",
            "头像": "Avatar",
            "简介": "Bio",
            "网站": "Website",
            "链接": "Link",
            "图片": "Image",
            "视频": "Video",
            "音频": "Audio",
            "文件": "File",
            "上传": "Upload",
            "下载": "Download",
            "导出": "Export",
            "导入": "Import",
            "数据": "Data",
            "系统": "System",
            "配置": "Configuration",
            "状态": "Status",
            "时间": "Time",
            "日期": "Date",
            "信息": "Information",
            "消息": "Message",
            "通知": "Notification",
            "成功": "Success",
            "失败": "Failed",
            "错误": "Error",
            "警告": "Warning",
            "提示": "Tip",
            "帮助": "Help",
            "关于": "About",
            "联系": "Contact",
            "服务": "Service",
            "条款": "Terms",
            "隐私": "Privacy",
            "政策": "Policy",
            "版权": "Copyright",
            "所有": "All",
        },
        "ja": {
            "博客": "ブログ",
            "文章": "記事",
            "分类": "カテゴリ",
            "标签": "タグ",
            "评论": "コメント",
            "用户": "ユーザー",
            "设置": "設定",
            "搜索": "検索",
            "发布": "公開",
            "编辑": "編集",
            "删除": "削除",
            "保存": "保存",
            "取消": "キャンセル",
            "确认": "確認",
            "返回": "戻る",
            "首页": "ホーム",
            "管理": "管理",
            "登录": "ログイン",
            "注册": "登録",
            "密码": "パスワード",
            "邮箱": "メール",
            "昵称": "ニックネーム",
            "头像": "アバター",
            "简介": "自己紹介",
            "网站": "ウェブサイト",
            "链接": "リンク",
            "图片": "画像",
            "视频": "動画",
            "音频": "音声",
            "文件": "ファイル",
            "上传": "アップロード",
            "下载": "ダウンロード",
            "导出": "エクスポート",
            "导入": "インポート",
            "数据": "データ",
            "系统": "システム",
            "配置": "設定",
            "状态": "ステータス",
            "时间": "時間",
            "日期": "日付",
            "信息": "情報",
            "消息": "メッセージ",
            "通知": "通知",
            "成功": "成功",
            "失败": "失敗",
            "错误": "エラー",
            "警告": "警告",
            "提示": "ヒント",
            "帮助": "ヘルプ",
            "关于": "について",
            "联系": "連絡",
            "服务": "サービス",
            "条款": "利用規約",
            "隐私": "プライバシー",
            "政策": "ポリシー",
            "版权": "著作権",
            "所有": "すべて",
        },
    }

    target_dict = mock_translations.get(target, {})
    result = text
    for zh, translated in target_dict.items():
        result = result.replace(zh, translated)

    return result


@router.post("", response_model=TranslateResponse, summary="翻译文本")
async def translate_text(
    request: TranslateRequest,
    current_user: Any = Depends(get_current_user),
) -> TranslateResponse:
    """
    翻译文本到多种语言

    支持的语言：
    - zh: 简体中文
    - en: English
    - ja: 日本語
    - zh_Hant: 繁體中文

    需要登录用户权限。
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="翻译文本不能为空")

    translations: dict[str, str] = {}

    for target_lang in request.target_langs:
        if target_lang == request.source_lang:
            translations[target_lang] = request.text
            continue

        if target_lang not in settings.supported_languages:
            logger.warning(f"Unsupported target language: {target_lang}")
            continue

        if settings.is_development:
            translated = await mock_translate(request.text, request.source_lang, target_lang)
        else:
            translated = await translate_with_mymemory(
                request.text, request.source_lang, target_lang
            )
            if translated == request.text:
                translated = await mock_translate(request.text, request.source_lang, target_lang)

        translations[target_lang] = translated

    logger.info(f"Translated text for user {current_user.username}: {len(translations)} languages")

    return TranslateResponse(translations=translations)
