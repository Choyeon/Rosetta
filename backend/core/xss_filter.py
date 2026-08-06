"""
XSS 输入过滤（bleach 依赖不存在，手写正则 allowlist 清洗）

策略：
1. 粗过滤（正则剔除）：<script>...</script> / <iframe>... / onxxx="..." / onxxx='...' / javascript:
2. allowlist 二次清洗：
   允许 tags：a, abbr, b, blockquote, code, em, h1, h2, h3, h4, h5, h6, i, li, ol, p, pre,
               strong, ul, br, img
   属性白名单：
     全局：class, id, alt, title
     a：href (必须 http(s)/mailto)、target="_blank"（强制 rel="noopener noreferrer"）
     img：src (http(s)/data:)、alt、title
"""

from __future__ import annotations

import re
from html import escape as _html_escape
from html.parser import HTMLParser
from urllib.parse import urlparse


def _escape_dangerous_tag_names(text: str) -> str:
    """把危险标签（script/iframe/object/embed/link/meta）的尖括号转义成实体，
    保留原文可读但不执行。同时转义 onxxx= 事件属性和 javascript: 伪协议。

    这样做的好处：不丢弃用户原文（方便后台审计与回显），浏览器不执行。
    若直接整段删除，XSS 攻击载荷的痕迹将完全消失，不利于问题追踪与合规审计。
    """
    if not isinstance(text, str) or not text:
        return text or ""

    # 1) <script> / <iframe> 等标签：< 和 > 转义 → &lt;script&gt;
    #    覆盖成对和自闭合形式（不区分大小写、可带属性）
    dangerous_tag_re = re.compile(
        r"(?is)</?(script|iframe|object|embed|link|meta)\b([^>]*?)(/?>)",
    )

    def _tag_escaper(m: re.Match) -> str:
        leading_slash = m.group(0)[1] == "/"  # "</...".startswith("</")
        tagname = m.group(1)
        attrs = m.group(2) or ""
        closing = m.group(3) or ""
        # 转义属性里的 onxxx= 和 javascript:（双重保险）
        attrs_safe = _escape_attrs(attrs)
        prefix = "</" if leading_slash else "<"
        return f"&lt;{'/' if leading_slash else ''}{tagname}{attrs_safe}{closing.replace('>', '&gt;')}"

    text = dangerous_tag_re.sub(_tag_escaper, text)

    # 2) onxxx= 事件属性：把 = 前的 on 转义为 o&#110;，浏览器不识别为事件处理器
    #    同时转义属性值防止跨上下文逃逸
    on_event_re = re.compile(
        r"(?is)\s+(on\w+)\s*(=)\s*(\"[^\"]*\"|'[^']*'|[^\s\"'>]+)",
    )
    text = on_event_re.sub(
        lambda m: f" &#111;&#110;{m.group(1)[2:]}&#61;"
        f"{_html_escape(m.group(3), quote=True)}",
        text,
    )

    # 3) javascript: 伪协议（出现在任意裸词上下文）→ 替换成 # 前导的无害形式
    #    同时转义剩余的危险字符：< > 单双引号裸形式
    js_proto_re = re.compile(r"(?i)javascript\s*:\s*")
    text = js_proto_re.sub("#javascript:", text)
    return text


def _escape_attrs(attrs_chunk: str) -> str:
    """标签内部属性块安全化：转义 onxxx=、事件值和尖括号。"""
    if not attrs_chunk:
        return ""
    attrs_chunk = re.sub(
        r"(?is)\s+(on\w+)\s*(=)",
        lambda m: f" &#111;&#110;{m.group(1)[2:]}&#61;",
        attrs_chunk,
    )
    js_proto_re = re.compile(r"(?i)javascript\s*:\s*")
    attrs_chunk = js_proto_re.sub("#javascript:", attrs_chunk)
    attrs_chunk = attrs_chunk.replace("<", "&lt;").replace(">", "&gt;")
    return attrs_chunk


_ROUGH_STRIP_RE = None  # 旧字段，已被 _escape_dangerous_tag_names 语义替代


def _rough_strip(text: str) -> str:
    """兼容旧调用：不再整段删除，改为转义危险标签。"""
    return _escape_dangerous_tag_names(text)


# --- Allowlist 二次清洗：允许安全的 HTML 标签通过（用于富文本评论/文章）---
_ALLOWED_TAGS = {
    "a",
    "abbr",
    "b",
    "blockquote",
    "code",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "i",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "ul",
    "br",
    "img",
}
_GLOBAL_ATTRS = {"class", "id", "alt", "title"}
_ATTRS_BY_TAG = {
    "a": {"href", "target", "rel"},
    "img": {"src", "alt", "title", "width", "height"},
}
_HREF_PREFIXES = ("http://", "https://", "mailto:", "/", "#")
_SRC_PREFIXES = ("http://", "https://", "data:")


def _is_safe_href(v: str) -> bool:
    if not v:
        return False
    lv = v.lower().lstrip()
    if any(lv.startswith(p) for p in _HREF_PREFIXES):
        return True
    return False


def _is_safe_src(v: str) -> bool:
    if not v:
        return False
    lv = v.lower().lstrip()
    if any(lv.startswith(p) for p in _SRC_PREFIXES):
        return True
    try:
        parsed = urlparse(v)
        if parsed.scheme in ("http", "https", "data"):
            return True
    except Exception:
        return False
    return False


class _AllowlistParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._out: list[str] = []
        self._tag_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        tag = tag.lower()
        if tag not in _ALLOWED_TAGS:
            return
        allowed_attr_names = _GLOBAL_ATTRS | _ATTRS_BY_TAG.get(tag, set())
        rebuilt = []
        add_rel = False
        for k, v in attrs:
            k = (k or "").lower()
            if k not in allowed_attr_names:
                continue
            if v is None:
                rebuilt.append(k)
                continue
            if tag == "a" and k == "href":
                if not _is_safe_href(v):
                    continue
            if tag == "img" and k == "src":
                if not _is_safe_src(v):
                    continue
            if tag == "a" and k == "target":
                if v.lower() == "_blank":
                    add_rel = True
                else:
                    continue
            escaped_v = (
                v.replace("&", "&amp;")
                .replace('"', "&quot;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            rebuilt.append(f'{k}="{escaped_v}"')
        if tag == "a" and add_rel:
            rebuilt.append('rel="noopener noreferrer"')
        attr_str = (" " + " ".join(rebuilt)) if rebuilt else ""
        if tag == "br" or tag == "img":
            self._out.append(f"<{tag}{attr_str}>")
        else:
            self._out.append(f"<{tag}{attr_str}>")
            self._tag_stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag not in _ALLOWED_TAGS or tag in ("br", "img"):
            return
        if self._tag_stack and self._tag_stack[-1] == tag:
            self._tag_stack.pop()
            self._out.append(f"</{tag}>")

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if tag not in _ALLOWED_TAGS:
            return
        allowed_attr_names = _GLOBAL_ATTRS | _ATTRS_BY_TAG.get(tag, set())
        rebuilt = []
        for k, v in attrs:
            k = (k or "").lower()
            if k not in allowed_attr_names:
                continue
            if v is None:
                rebuilt.append(k)
                continue
            if tag == "img" and k == "src":
                if not _is_safe_src(v):
                    continue
            escaped_v = (
                v.replace("&", "&amp;")
                .replace('"', "&quot;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            rebuilt.append(f'{k}="{escaped_v}"')
        attr_str = (" " + " ".join(rebuilt)) if rebuilt else ""
        self._out.append(f"<{tag}{attr_str}>")

    def handle_data(self, data: str) -> None:
        self._out.append(data)

    def handle_entityref(self, name: str) -> None:
        self._out.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self._out.append(f"&#{name};")

    def result(self) -> str:
        out = "".join(self._out)
        while self._tag_stack:
            t = self._tag_stack.pop()
            out += f"</{t}>"
        return out


def sanitize_html(text: str) -> str:
    """清除 XSS payload，返回安全 HTML 文本（allowlist 二次清洗）。"""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    stripped = _rough_strip(text)
    try:
        parser = _AllowlistParser()
        parser.feed(stripped)
        parser.close()
        cleaned = parser.result()
    except Exception:
        cleaned = stripped
    return cleaned
