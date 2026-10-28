"""多语言 JSON 列的查询谓词（搜索召回的唯一口径）。

为什么这里有一份，而不是三处各写各的 `col["zh"].ilike(...)`：

1. **语言清单只有一条**。本仓固定四语（`core/i18n.LANGUAGE_CODES`），但线上实测搜索谓词只写了
   `zh` 与 `en`：`GET /api/blog/posts?search=コンポジション` 返回 0 条，而 `/ja` 页面上这篇的
   标题正是「Vue 3 コンポジション API 実践」。对日语与繁体访客来说，**站内搜索看不见用他们
   的语言写的内容**——内容存在、URL 存在、只是搜不到。写死两语的第三个表现是加第五种语言时
   （AGENTS.md §14「新增语言」要同步的四个地方）搜索会静默漏掉它，不报错。
2. **裸字符串行取不到任何键**。批次 #34 收口的是"读到裸字符串就 500"；同一批数据在搜索里是
   另一种坏法：`col["zh"]` 对一个 JSON 字符串永远返回 NULL，于是这些行在搜索结果里彻底不存在，
   而它们照常出现在列表与详情页里（"看得见、搜不到"）。所以谓词必须兜住整列文本。
3. 同一功能曾有三份内联实现（公开列表口用 `cast(col[lang], String)`、仓储层用
   `col[lang].astext`、系列 autocomplete 又是一份），改一次口径要动九个地方，漏一处就是
   "同一个关键词在两个入口结果不同"。装饰用的写法差异本身也是风险：`astext` 是 PG 方言专有
   扩展，`cast(..., String)` 在 PG 与 SQLite 两边都编译得过——公开口那条已在生产验证。

`ilike` 一律大小写不敏感：英文站点的搜索词大小写由访客决定，`LIKE` 会把 "vue" 判成 0 条。
"""

from __future__ import annotations

from sqlalchemy import String, cast, not_, or_

from backend.core.i18n import LANGUAGE_CODES


def i18n_contains(column, term: str):
    """多语言列在**任一语言**或**裸字符串整值**上命中 `term`（`term` 需自带 `%`）。"""
    per_language = [cast(column[lang], String).ilike(term) for lang in LANGUAGE_CODES]
    # 兜裸字符串形态：`{` 开头是对象，已经按语言键逐个匹配过，不再扫整列文本——那会把 JSON 的
    # **键名**当成命中（搜 "zh" 或 "content" 就能匹配到每一行），代价是假阳性淹没真实结果。
    bare_value = not_(cast(column, String).like("{%")) & cast(column, String).ilike(term)
    return or_(*per_language, bare_value)
