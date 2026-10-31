"""URL 字段的第三档校验：只挡可执行协议，站内路径与 http(s) 外链都放行。

放在独立叶子模块而不是 `backend/schemas/__init__.py`，是因为子模块（`hero.py`）要在
定义期就 import 它——从正在执行的包 `__init__` 里取名会撞循环导入。

与 `__init__.py` 里另两档的分工（三档不是重复实现，选哪档取决于这个值的消费点）：

- `_normalize_optional_url`（宽容档）：注册资料/友链这类"用户填 example.com 就是想跳 https"
  的字段，缺 scheme 就补。
- `_require_absolute_url`（严格档）：必须以 http(s) 开头。用在**文章原文出处链接**那种
  "补出来的地址点了不通、还不如直接拒"的出站链接。
- 本档：轮播按钮这类**本来就该填站内路径**（`/posts`、`/series/xxx`）的字段。
  严格档会把正常配置全拒掉，宽容档又会把 `javascript:` 补成 `https://javascript:...`，
  所以这一档只做一件不能商量的事——可执行协议不能成为 `<a href>` 的值。

渲染侧（`frontend/lib/hero-cta.ts::safeHeroHref`）还会再判一次：写入口不止本 schema
（导入 ZIP 直接落 ORM），库里可能躺着历史脏值。两道都留，缺一道就各有漏法。

判定前剥掉空白与控制字符，是因为浏览器解析 URL 时会自己剥掉 `\t` `\n` `\r` 与空格：
`javas\\tcript:alert(1)` 人眼看着是怪串，点上去就是执行。只剥**判定用的副本**，
返回值仍是原串——闸门管的是协议，不改写运营者填的链接。
"""

import re

# 剥空白与控制字符后从串首锚定；大小写混写由 IGNORECASE 兜。
PSEUDO_URL_SCHEME_RE = re.compile(r"(javascript|vbscript|data|file):", re.IGNORECASE)
_URL_STRIP_RE = re.compile(r"[\s\u0000-\u001f]")


def reject_pseudo_url_scheme(v: str | None) -> str | None:
    """伪协议 → ValueError（FastAPI 侧即 422）；其余原样返回，包括空值与站内路径。"""
    if isinstance(v, str) and PSEUDO_URL_SCHEME_RE.match(_URL_STRIP_RE.sub("", v)):
        raise ValueError("链接不能以可执行协议开头")
    return v


def require_internal_media_path(v: str | None, *, label: str = "媒体") -> str | None:
    """第四档：**音频/视频源地址**。空串归 None（= 清掉），非空必须是站内路径。

    和严格档相反：这里不是"必须绝对"，而是"必须相对到站内"。CSP 的 `media-src` 只有
    `'self' blob: data:`（`backend/core/security_middleware.py` ↔ `deploy/nginx-site.conf`
    两处同口径），外链音视频会被浏览器直接拦掉——写入口不拒，运营者看到的就是
    "后台保存成功、前台一个播放器都不显示"。`//host/x` 是协议相对外链，同样逃出 `'self'`。

    只挂写口：库里可能躺着导入 ZIP / 直连 SQL 留下的外链，读侧拒绝等于把详情口变成 500。
    """
    if v is None:
        return None
    value = v.strip()
    if not value:
        return None
    reject_pseudo_url_scheme(value)
    if not value.startswith("/") or value.startswith("//"):
        raise ValueError(
            f"{label}地址必须是站内路径（如 /media/xxx.mp4），外链会被 CSP 的 media-src 拦截"
        )
    return value
