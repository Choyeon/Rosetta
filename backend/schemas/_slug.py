"""内容型 slug 的共用校验模式（文章 / 分类 / 标签 / 页面 / 系列）。

前端 `useAdminI18n.ts::slugify` 的保留字符集是 `[\\w\\u4e00-\\u9fa5-]`（JS 下
`\\w` = ASCII 字母数字下划线，再叠加 CJK 表意文字），刻意产出中文 slug；读取侧与
URL 层（Nitro `05-url-normalize` 中间件、`pages/[slug].vue` 自愈）也为中文 slug
专门建过一整套。写入侧若仍锁 `^[a-z0-9-]+$`，任何中文标题/分类名在后台保存时都会被
Pydantic 判 `string_pattern_mismatch` → 422，与既定设计冲突。此处放开到"前端
slugify 能产出的字符集"，同时继续禁止 `/ \\ . % 空格 < > ? & #` 等结构字符，
杜绝路径穿越与 URL 编码注入。

注意：插件 / 主题 manifest 的 slug 是内部标识（须 kebab-case ASCII），另用更严的
`^[a-z0-9-]{3,64}$`，不复用本常量。
"""

CONTENT_SLUG_PATTERN = r"^[a-z0-9_\u4e00-\u9fff-]+$"
