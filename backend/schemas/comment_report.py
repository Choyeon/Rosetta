"""
评论举报相关 Pydantic Schema。

举报是「用户侧标记 + 管理侧裁决」两段式：公开写口只落一行 ``comment_reports``
（并把 ``comments.reported_at`` 立成待处理标记），状态流转只在管理员口发生。
详见 ``backend/models/comment_report.py`` 与 ``backend/api/comment_report.py``。
"""

from typing import Literal

from pydantic import BaseModel, Field

ReportReason = Literal["spam", "abuse", "offtopic", "other"]
ReportStatus = Literal["open", "handled", "dismissed"]


class CommentReportCreate(BaseModel):
    """公开写口请求体：举报原因 + 可选的补充说明。"""

    reason: ReportReason = Field(
        ...,
        description="举报原因：spam（垃圾广告）/ abuse（辱骂攻击）/ offtopic（无关内容）/ other（其它）",
    )
    detail: str | None = Field(
        None, max_length=500, description="补充说明（可选，≤500 字），不要在这里贴原文"
    )


class CommentReportReceipt(BaseModel):
    """公开写口的响应体。

    ``duplicate=True`` 表示这次请求撞上了已存在的待处理举报、**没有**新建行
    （同一用户对同一条评论重复点举报，或同一 IP 24 小时内重复），
    此时 ``id`` 指向那条已存在的举报。两种结果都回成功：
    对访客而言"已经举报过了"不是错误，回 409 只会让前端多写一套分支。
    """

    id: int = Field(..., description="举报记录 ID（新建的，或命中的已存在记录）")
    comment_id: int = Field(..., description="被举报评论 ID")
    status: ReportStatus = Field(..., description="该举报当前状态，通常为 open")
    duplicate: bool = Field(..., description="true 表示未新建行、复用了已存在的待处理举报")
    message: str = Field(..., description="给访客看的提示文案")


class AdminCommentReportItem(BaseModel):
    """管理端举报列表的单条投影（评论与文章摘要一并带出，省掉 N+1 详情请求）。"""

    id: int = Field(..., description="举报 ID")
    comment_id: int = Field(..., description="被举报评论 ID")
    post_id: int = Field(..., description="评论所属文章 ID")
    reason: str = Field(..., description="举报原因枚举值")
    detail: str | None = Field(None, description="举报人填写的补充说明")
    status: str = Field(..., description="open / handled / dismissed")
    reporter_user_id: int | None = Field(None, description="举报人用户 ID，匿名举报为 null")
    reporter_name: str | None = Field(None, description="举报人显示名，匿名为 null")
    reporter_ip: str | None = Field(
        None, description="举报来源 IP（与评论列表同口径，仅 staff 可见）"
    )
    comment_excerpt: str = Field(..., description="被举报评论正文前 120 字")
    comment_author: str = Field(..., description="被举报评论作者显示名")
    comment_status: str = Field(..., description="被举报评论的审核状态")
    post_slug: str | None = Field(None, description="文章 slug，文章缺失为 null")
    post_title: str | None = Field(None, description="文章标题（默认语言），文章缺失为 null")
    created_at: str | None = Field(None, description="举报时间 ISO 8601")
    handled_at: str | None = Field(None, description="裁决时间 ISO 8601，未处理为 null")
    handled_by: str | None = Field(None, description="裁决人显示名，未处理为 null")


class AdminCommentReportCounts(BaseModel):
    """各状态举报数（不受当前筛选影响，用于页签角标）。"""

    open: int
    handled: int
    dismissed: int
    total: int


class AdminCommentReportListResponse(BaseModel):
    """管理端举报列表（裸分页 dict，无 success/data 信封）。"""

    items: list[AdminCommentReportItem]
    total: int = Field(..., description="当前筛选条件下的总数")
    page: int
    page_size: int
    total_pages: int
    counts: AdminCommentReportCounts


class AdminCommentReportUpdate(BaseModel):
    """管理员裁决：只允许落在终态 handled / dismissed。"""

    status: Literal["handled", "dismissed"] = Field(
        ..., description="handled（确认违规并已处置）或 dismissed（误报，驳回）"
    )


class AdminCommentReportUpdated(AdminCommentReportItem):
    """裁决后的响应体；比请求多一个 ``comment_reported`` 表示评论是否仍有待处理举报。"""

    comment_reported: bool = Field(
        ..., description="裁决后该评论是否仍挂着其它待处理举报（决定列表「待处理」标记）"
    )


from backend.schemas.strict_config import apply_strict_extra_forbid

apply_strict_extra_forbid(globals(), __name__)
