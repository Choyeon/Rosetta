"""前台只读视图（归档 / 统计 / 上一篇下一篇）的响应模型。

这些端点历史上直接 return repository 拼出来的 dict，OpenAPI 里查不到任何结构，
前端只能靠读源码猜字段。这里按**实际返回**逐字段建模型，并只用 `responses=`
挂进文档：FastAPI 的 `responses` 只生成 schema，不会过滤运行时响应体，
所以补文档的同时不会抹掉 repository 以后新增的字段。
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.schemas import BaseResponse


class ArchivePostCategory(BaseModel):
    """归档列表里嵌的分类摘要。"""

    id: int = Field(..., description="分类 ID")
    name: str = Field(..., description="按请求语言解析后的分类名")
    color: str | None = Field(None, description="分类强调色（十六进制），未设置为 null")


class ArchivePostItem(BaseModel):
    """归档列表里的单篇文章条目（比列表页的卡片字段更精简）。"""

    id: int = Field(..., description="文章 ID")
    title: str = Field(..., description="按请求语言解析后的标题，缺失时回退 zh")
    slug: str = Field(..., description="文章 slug，用于拼详情页 URL")
    created_at: str | None = Field(None, description="创建时间 ISO 8601；无创建时间时为 null")
    published_at: str | None = Field(
        None,
        description="发布时间 ISO 8601（缺发布日时回退创建日）；归档的分组与日期显示都以此为准",
    )
    category: ArchivePostCategory | None = Field(None, description="所属分类，未归类时为 null")
    views: int = Field(0, description="累计浏览量")


class ArchiveMonthGroup(BaseModel):
    """归档页的一个「年-月」分组。"""

    year: int = Field(..., description="年份")
    month: int = Field(..., description="月份（1-12）")
    count: int = Field(..., description="该月返回的文章条数（等于 posts 长度）")
    posts: list[ArchivePostItem] = Field(
        default_factory=list, description="该月文章条目，按月内倒序"
    )


class ArchiveMonthPage(ArchiveMonthGroup):
    """单月归档分页响应：在年月分组之上叠分页字段。"""

    page: int = Field(1, description="当前页码，从 1 开始")
    page_size: int = Field(20, description="每页条数")
    total_pages: int = Field(0, description="总页数；无数据时为 0")


class ArchiveStats(BaseModel):
    """归档页顶部的年度统计。"""

    total_posts: int = Field(..., description="已发布文章总数")
    total_years: int = Field(..., description="有文章的年份数")
    years: list[int] = Field(default_factory=list, description="年份列表，倒序")
    year_stats: dict[int, int] = Field(
        default_factory=dict,
        description='年份 → 该年文章数。注意 JSON 序列化后键是字符串，如 {"2026": 12}',
    )


class SiteStats(BaseModel):
    """全站统计（关于页 / 页脚用）。"""

    total_words: int = Field(0, description="已发布文章的中文字数 + 英文词数合计")
    total_posts: int = Field(0, description="已发布文章数")
    total_categories: int = Field(0, description="被文章引用过的去重分类数")
    total_tags: int = Field(0, description="被文章引用过的去重标签数")


class AdjacentPost(BaseModel):
    """相邻文章（上一篇 / 下一篇）指向。"""

    slug: str = Field(..., description="相邻文章 slug")
    title: str = Field(..., description="按请求语言解析后的标题")


class PostAdjacentData(BaseModel):
    """文章详情页上下篇数据体。"""

    previous: AdjacentPost | None = Field(None, description="更早的一篇，已是最早时为 null")
    next: AdjacentPost | None = Field(None, description="更晚的一篇，已是最新时为 null")


class PostAdjacentResponse(BaseResponse):
    """`GET /blog/posts/{slug}/adjacent` 的完整响应。"""

    data: PostAdjacentData | None = Field(None, description="上下篇数据")
    message: str = ""


class UserBlogStats(BaseModel):
    """「我的统计」：当前登录作者的产出与互动量。"""

    posts: int = Field(0, description="本人创建的文章数（含草稿）")
    comments: int = Field(0, description="本人发表的评论数")
    likes: int = Field(0, description="本人文章收到的点赞总数")


class UserBlogStatsResponse(BaseResponse):
    """`GET /blog/users/me/stats` 的完整响应。"""

    data: UserBlogStats | None = Field(None, description="统计数据")
    message: str = "获取统计成功"
