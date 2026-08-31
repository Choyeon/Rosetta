r"""
Shortcode 引擎（WordPress 风格）
=================================

*零额外依赖*：手写 allowlist sanitize（不引入 bleach，用 stdlib html + re）。
符合计划 Task C 的全部接口契约。

公开 API（与插件 ctx 对接）：
    - ``register_shortcode(name, fn, plugin=None)`` — 注册
    - ``unregister_shortcode(name)`` — 注销
    - ``do_shortcode(html, ctx=None)`` — 渲染整段 HTML 中的短代码
    - ``shortcode_manager.remove_for_plugin(plugin_slug)`` — 插件禁用时批量摘除
    - ``ShortcodeManager`` 类（便于测试隔离 / 并行上下文）

语法（WordPress 兼容子集）：
    自闭合：   ``[greet name=Rosetta /]``
    成对：     ``[box cls=warning]小心[/box]``
    属性：     ``key=value`` / ``key="value"`` / ``key='value'``
    命名：     ``^[A-Za-z_][\w\-]*$`` （首字母不能是数字）

安全模型：
    1. 所有 handler 输出 **强制** 经过 allowlist 二次清洗（见 ``_sanitize_output``）。
       允许标签：a/abbr/b/blockquote/br/code/div/dl/em/h1~h6/hr/i/img/li/ol/
                p/pre/small/span/strong/sub/sup/table/thead/tbody/tfoot/tr/th/td/
                caption/col/colgroup/details/summary/ul/u/q/dt/dd
       高危 script/style/iframe 等被整段剥离；onxxx= 事件属性、javascript: 协议被删除。
       未列入白名单的标签被转义为实体（保留其包裹的文本，浏览器不渲染）。
    2. 未注册的短代码 **原样保留**（不丢弃用户内容，便于迁移 / 排查）。
"""

from __future__ import annotations

import html as _html
import logging
import re
import shlex
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger("rosetta.shortcodes")


# ═══════════════════════════════════════════════════════════════════════
# 内部：数据结构
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class ShortcodeInfo:
    """对外暴露的短代码注册信息（只读视图）。

    为保持与旧版 ``[(name, plugin)]`` 形式的兼容，本类支持按序解包：
    ``tag, plugin = info``，``plugin`` 字段在第 2 位。
    """

    tag: str
    has_paired: bool = True
    plugin: str | None = None
    description: str | None = None

    def __iter__(self):
        # 按 (tag, plugin) 顺序解包 → 兼容旧测试 for n, _p in list_shortcodes()
        return iter((self.tag, self.plugin))


@dataclass
class _HandlerRecord:
    name: str
    fn: Callable[..., Any]
    plugin: str | None = None
    has_paired: bool = True
    description: str | None = None


_NAME_PATTERN = r"[A-Za-z_][\w\-]*"
_NAME_RE = re.compile(_NAME_PATTERN)

# 开标签正则： [name(attrs)(/?)]
_OPEN_RE = re.compile(
    r"\[(" + _NAME_PATTERN + r")"   # group(1): name
    r"([^\]]*?)"                    # group(2): 属性块 (可为空/含空白)
    r"(\/)?\]"                      # group(3): 自闭合斜杠
)


# ═══════════════════════════════════════════════════════════════════════
# 属性解析
# ═══════════════════════════════════════════════════════════════════════

_ATTRS_SHLEX_RE = re.compile(
    r"""
    ([A-Za-z_][\w\-]*)               # key
    (?:\s*=\s*                       # = (可选，对裸 flag 省略)
        (?:
            "((?:[^"\\]|\\.)*)"      # double-quoted (支持 \" 转义)
          | '((?:[^'\\]|\\.)*)'      # single-quoted (支持 \' 转义)
          | ([^\s"'=<>`]+)           # unquoted bareword
        )
    )?
    """,
    re.VERBOSE,
)


def _parse_attrs(raw_block: str) -> dict[str, str]:
    """解析 ``k1=v1 k2='v2' k3="v3" flag`` → dict。

    - 引号使用 shlex 语义（可嵌套 / 转义）；
    - 降级：shlex 解析失败时回退正则解析；
    - 无 ``=`` 的裸 token 视为 flag（值为 ``"True"``，WP 兼容）。
    """
    if not raw_block or not raw_block.strip():
        return {}
    result: dict[str, str] = {}
    try:
        tokens = shlex.split(raw_block, posix=True)
    except ValueError:
        tokens = []
    if tokens:
        for tok in tokens:
            if "=" in tok:
                k, _, v = tok.partition("=")
                k = k.strip()
                if k:
                    result[k] = v
            elif tok:
                result[tok] = "True"
        return result
    # shlex 异常 → 正则降级
    for m in _ATTRS_SHLEX_RE.finditer(raw_block):
        k = m.group(1)
        v_dq, v_sq, v_br = m.group(2), m.group(3), m.group(4)
        value = v_dq if v_dq is not None else (v_sq if v_sq is not None else v_br)
        if value is None:
            # flag 形式
            result[k] = "True"
        else:
            result[k] = value
    return result


# ═══════════════════════════════════════════════════════════════════════
# 安全：Allowlist Sanitizer
# ═══════════════════════════════════════════════════════════════════════

_ALLOWED_TAGS = frozenset({
    # 结构化
    "a", "abbr", "b", "blockquote", "br", "caption", "cite", "code",
    "col", "colgroup", "dd", "del", "details", "div", "dl", "dt", "em",
    "figcaption", "figure", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i",
    "img", "ins", "li", "mark", "ol", "p", "pre", "q", "small", "span",
    "strong", "sub", "summary", "sup", "table", "tbody", "td", "tfoot",
    "th", "thead", "tr", "u", "ul",
})

_ALLOWED_ATTRS: dict[str, frozenset[str]] = {
    "a":    frozenset({"href", "title", "target", "rel"}),
    "img":  frozenset({"src", "alt", "title", "width", "height", "loading"}),
    "td":   frozenset({"colspan", "rowspan"}),
    "th":   frozenset({"colspan", "rowspan", "scope"}),
    "col":  frozenset({"span"}),
    "colgroup": frozenset({"span"}),
    "*":    frozenset({"class", "id", "style", "title", "alt"}),
}

# 整段剥离：开-闭配对的危险内容（script/style 等可能含大量代码）
_STRIP_PAIR_TAGS = (
    "script", "style", "iframe", "object", "embed", "noscript", "textarea",
)

# 自闭合形式的危险标签
_ESCAPE_SINGLE_RE = re.compile(
    r"<\s*(script|iframe|object|embed|link|meta|style|form|input|"
    r"button|select|option|textarea|fieldset)\b[^>]*?\/?\s*>",
    re.IGNORECASE | re.DOTALL,
)

# 所有 HTML 标签：用于 allowlist 二次走查
_ANY_TAG_RE = re.compile(r"<(\s*\/?\s*)([A-Za-z_][\w\-\:]*)(\s+[^>]*?|)\s*(\/)?>")


def _attrs_allowed_for(tag_lower: str) -> frozenset[str]:
    per = _ALLOWED_ATTRS.get(tag_lower, frozenset())
    star = _ALLOWED_ATTRS.get("*", frozenset())
    return per | star


_ATTR_KEY_RE = re.compile(r"([A-Za-z_][\w\-]*)")
_ATTR_VALUE_RE = re.compile(
    r"""(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)'|([^\s"'=<>`]+))""",
    re.VERBOSE,
)


def _rewrite_attrs(tag: str, attr_string: str) -> str:
    """对属性串做 allowlist 过滤 + javascript/vbscript 伪协议剥离 + onxxx 删除。"""
    if not attr_string.strip():
        return ""
    allowed = _attrs_allowed_for(tag)
    out: list[str] = []
    pos = 0
    s = attr_string
    while pos < len(s):
        # 跳过空白
        while pos < len(s) and s[pos].isspace():
            pos += 1
        if pos >= len(s):
            break
        # 读取 key
        km = _ATTR_KEY_RE.match(s, pos)
        if not km:
            pos += 1
            continue
        key = km.group(1).lower()
        pos = km.end()
        # 可选 =value
        has_eq = False
        while pos < len(s) and s[pos].isspace():
            pos += 1
        if pos < len(s) and s[pos] == "=":
            has_eq = True
            pos += 1
            while pos < len(s) and s[pos].isspace():
                pos += 1
            vm = _ATTR_VALUE_RE.match(s, pos)
            if vm:
                v = vm.group(1) if vm.group(1) is not None else (
                    vm.group(2) if vm.group(2) is not None else vm.group(3)
                )
                pos = vm.end()
            else:
                # 等号后无合法值 → 跳过
                break
        else:
            v = None  # flag-only attribute

        # 事件属性 (onxxx) 一律丢弃
        if key.startswith("on"):
            continue
        # 非白名单属性丢弃
        if key not in allowed:
            continue
        # href/src/action/formaction：剔除 javascript/vbscript + data: 伪协议
        if has_eq and v and key in {"href", "src", "action", "formaction", "poster"}:
            lv = v.strip().lower().replace("\u0000", "")
            # 处理可能的 \x 或 tab 嵌入的伪协议变体
            lv_no_ws = re.sub(r"\s+", "", lv)
            if lv_no_ws.startswith(("javascript:", "vbscript:", "data:text/html")):
                continue
        if not has_eq or v is None:
            out.append(key)
        else:
            safe = _html.escape(v, quote=True)
            out.append(f'{key}="{safe}"')
    return (" " + " ".join(out)) if out else ""


def _sanitize_output(raw: str) -> str:
    """短代码输出安全清洗（零 bleach 依赖，纯 stdlib 正则）。"""
    if not raw:
        return ""

    # 1) 移除 script/style/iframe/object 等成对危险标签及其内容
    for t in _STRIP_PAIR_TAGS:
        pat = re.compile(
            rf"<\s*{t}\b[^>]*>.*?<\s*\/\s*{t}\s*>",
            re.DOTALL | re.IGNORECASE,
        )
        raw = pat.sub("", raw)

    # 2) 转义未闭合 / 自闭合的危险标签（保留文本痕迹，避免丢失审计信息）
    raw = _ESCAPE_SINGLE_RE.sub(lambda m: _html.escape(m.group(0)), raw)

    # 3) 对剩余所有标签做 allowlist 走查
    def _process_tag(m: re.Match[str]) -> str:
        leading = m.group(1)      # 可能含 '/'
        tagname = m.group(2)      # 可能含命名空间前缀等
        attr_str = m.group(3)
        self_close = m.group(4)

        # 规范化 tag 名：仅保留 ASCII 部分 + 小写
        clean_tag_m = re.match(r"[A-Za-z_][\w\-]*", tagname)
        if not clean_tag_m:
            return _html.escape(m.group(0))
        tag_lower = clean_tag_m.group(0).lower()

        is_closing = "/" in leading

        if tag_lower not in _ALLOWED_TAGS:
            # 不在白名单 → 转义整段标签（保留其内容），并补规范化
            return _html.escape(m.group(0))

        if is_closing:
            return f"</{tag_lower}>"

        rewritten = _rewrite_attrs(tag_lower, attr_str or "")
        if self_close:
            # img/br/hr 不需要 HTML 显式自闭合，但保留语义
            if tag_lower in {"img", "br", "hr", "col"}:
                return f"<{tag_lower}{rewritten}>"
            return f"<{tag_lower}{rewritten}>"
        return f"<{tag_lower}{rewritten}>"

    return _ANY_TAG_RE.sub(_process_tag, raw)


# ═══════════════════════════════════════════════════════════════════════
# ShortcodeManager 核心（每个实例注册表独立 → 测试隔离 / 并行安全）
# ═══════════════════════════════════════════════════════════════════════

class ShortcodeManager:
    """短代码管理器。生产环境使用全局 ``shortcode_manager`` 单例。"""

    def __init__(self) -> None:
        self._registry: dict[str, _HandlerRecord] = {}

    # ── 注册 / 注销 ────────────────────────────────────────────

    def register(
        self,
        name: str,
        fn: Callable[..., Any],
        *,
        plugin: str | None = None,
        has_paired: bool = True,
        description: str | None = None,
    ) -> None:
        """注册。重复注册覆盖旧记录。"""
        if not _NAME_RE.fullmatch(name):
            raise ValueError(
                f"Invalid shortcode name {name!r}; must match {_NAME_PATTERN}"
            )
        if not callable(fn):
            raise TypeError(f"Shortcode handler for {name!r} must be callable")
        self._registry[name] = _HandlerRecord(
            name=name,
            fn=fn,
            plugin=plugin,
            has_paired=has_paired,
            description=description,
        )
        logger.debug("Shortcode registered: %s (plugin=%s)", name, plugin)

    def unregister(self, name: str) -> bool:
        """返回注销前是否存在。"""
        existed = name in self._registry
        if existed:
            del self._registry[name]
            logger.debug("Shortcode unregistered: %s", name)
        return existed

    def remove_for_plugin(self, plugin_slug: str) -> int:
        """移除归属该插件的所有短代码，返回移除个数。"""
        drops = [n for n, rec in self._registry.items() if rec.plugin == plugin_slug]
        for n in drops:
            del self._registry[n]
        if drops:
            logger.info(
                "Removed %d shortcodes for plugin=%s: %s",
                len(drops), plugin_slug, drops,
            )
        return len(drops)

    def is_registered(self, name: str) -> bool:
        return name in self._registry

    def list_registered(self) -> list[ShortcodeInfo]:
        """返回公开的 ShortcodeInfo 列表。"""
        return [
            ShortcodeInfo(
                tag=r.name,
                has_paired=r.has_paired,
                plugin=r.plugin,
                description=r.description,
            )
            for r in self._registry.values()
        ]

    # ── 渲染 ───────────────────────────────────────────────────

    def render(self, text: str | None, ctx: dict[str, Any] | None = None) -> str:
        """渲染整段文本。``None`` 或非字符串 → 返回空串。"""
        if text is None:
            return ""
        if not isinstance(text, str):
            text = str(text)
        if not text:
            return ""

        # 空注册表：快速返回
        if not self._registry:
            return text

        return _do_render_impl(self._registry, text, ctx or {})


# ═══════════════════════════════════════════════════════════════════════
# 渲染主循环实现（共享给 ShortcodeManager.render 与全局 do_shortcode）
# ═══════════════════════════════════════════════════════════════════════

def _close_tag_pattern(name: str) -> re.Pattern[str]:
    return re.compile(r"\[\/" + re.escape(name) + r"\s*\]")


def _do_render_impl(
    registry: dict[str, _HandlerRecord],
    text: str,
    ctx: dict[str, Any],
) -> str:
    """基于 index 扫描 + 栈深度的成对匹配。

    算法概要：
      cursor 从 0 到 len(text)
        找下一个 _OPEN_RE 匹配（m_start..m_end）
        若 name 未注册 → 追加 text[cursor:m_end]，cursor=m_end，继续
        若自闭合 /   → 追加 text[cursor:m_start] + 调用 handler 结果，cursor=m_end，继续
        否则 → 栈匹配：深度 depth=1，扫描 text 后续的同 name 开/闭标签，depth 归零时的
                close_start..close_end 作为 body 边界。body 递归 render。
                若找不到闭合 → 追加原开标签不变，cursor=m_end。
    """
    out: list[str] = []
    cursor = 0
    n = len(text)

    while cursor < n:
        m = _OPEN_RE.search(text, cursor)
        if not m:
            out.append(text[cursor:])
            break

        name = m.group(1)
        attrs_raw = m.group(2) or ""
        self_closing = bool(m.group(3))

        if name not in registry:
            # 未注册 → 原样保留（防内容丢失）
            out.append(text[cursor:m.end()])
            cursor = m.end()
            continue

        # 自闭合 → 直接展开
        if self_closing:
            out.append(text[cursor:m.start()])
            attrs = _parse_attrs(attrs_raw)
            rendered = _call_handler(registry[name], attrs, "", ctx)
            out.append(rendered)
            cursor = m.end()
            continue

        # 成对：栈匹配找最近的同深度闭标签
        close_re = _close_tag_pattern(name)
        depth = 1
        scan_pos = m.end()
        close_start = close_end = None
        while depth > 0:
            next_open = _OPEN_RE.search(text, scan_pos)
            next_close = close_re.search(text, scan_pos)
            if not next_close:
                # 无匹配闭合 → 放弃匹配
                break
            if next_open and next_open.start() < next_close.start():
                if next_open.group(1) == name and not next_open.group(3):
                    depth += 1  # 同名开标签且非自闭合 → 深度 +1
                scan_pos = next_open.end()
                continue
            # 遇到 close
            depth -= 1
            if depth == 0:
                close_start = next_close.start()
                close_end = next_close.end()
                break
            scan_pos = next_close.end()

        if close_start is None or close_end is None:
            # 找不到闭合 → 原开标签保留
            out.append(text[cursor:m.end()])
            cursor = m.end()
            continue

        body_raw = text[m.end():close_start]
        body_rendered = _do_render_impl(registry, body_raw, ctx)

        out.append(text[cursor:m.start()])
        attrs = _parse_attrs(attrs_raw)
        rendered = _call_handler(registry[name], attrs, body_rendered, ctx)
        out.append(rendered)
        cursor = close_end

    return "".join(out)


def _call_handler(
    rec: _HandlerRecord,
    attrs: dict[str, str],
    content: str,
    ctx: dict[str, Any],
) -> str:
    """调用 handler（兼容 sync / 异常隔离），结果强制 sanitize。"""
    kwargs: dict[str, Any] = {**attrs}
    # 两个别名：content（主） / _content（兼容旧实现）
    kwargs["content"] = content
    kwargs["_content"] = content
    kwargs["ctx"] = ctx
    try:
        result = rec.fn(**kwargs)
    except TypeError:
        # 老处理器可能不接受 content/ctx：重试仅传 attrs + _content
        try:
            alt = {**attrs, "_content": content}
            result = rec.fn(**alt)
        except Exception as exc:  # pragma: no cover - 防御性
            logger.exception("Shortcode %s handler failed", rec.name)
            result = f"<!-- shortcode-error {rec.name}: {_html.escape(str(exc))} -->"
    except Exception as exc:  # noqa: BLE001 - 有意沙箱隔离
        logger.exception("Shortcode %s handler error", rec.name)
        result = f"<!-- shortcode-error {rec.name}: {_html.escape(str(exc))} -->"

    if result is None:
        return ""
    if not isinstance(result, str):
        try:
            result = str(result)
        except Exception:
            return ""

    return _sanitize_output(result)


# ═══════════════════════════════════════════════════════════════════════
# 全局单例 + 函数式 API（插件 ctx / 外部模块使用）
# ═══════════════════════════════════════════════════════════════════════

shortcode_manager = ShortcodeManager()


def register_shortcode(
    name: str | None = None,
    fn: Callable[..., Any] | None = None,
    *,
    tag: str | None = None,
    plugin: str | None = None,
    has_paired: bool = True,
    description: str | None = None,
    handler: Callable[..., Any] | None = None,
) -> None:
    """全局注册（支持 ``name`` / ``tag``，``fn`` / ``handler`` 别名以便调用方使用更语义化名称）。"""
    actual_tag = tag if tag is not None else name
    if actual_tag is None:
        raise TypeError("register_shortcode() missing required argument: 'name' or 'tag'")
    actual_fn = handler if handler is not None else fn
    if actual_fn is None:
        raise TypeError("register_shortcode() missing required argument: 'fn' or 'handler'")
    shortcode_manager.register(
        actual_tag,
        actual_fn,
        plugin=plugin,
        has_paired=has_paired,
        description=description,
    )


def unregister_shortcode(name: str) -> bool:
    """全局注销。返回是否存在。"""
    return shortcode_manager.unregister(name)


def do_shortcode(text: str | None, ctx: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> str:
    """公开入口：文章渲染前调用。``ctx`` 与 ``context`` 等价，取非空者。"""
    actual_ctx = context if context is not None else ctx
    return shortcode_manager.render(text, actual_ctx)


def list_shortcodes() -> list[ShortcodeInfo]:
    """返回 ShortcodeInfo 列表（用于管理 API & 调试）。"""
    return list(shortcode_manager.list_registered())


def _reset_shortcodes_for_tests() -> None:
    """清空短代码注册表（仅测试隔离使用）。"""
    shortcode_manager._registry.clear()  # noqa: SLF001
