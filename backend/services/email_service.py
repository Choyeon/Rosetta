"""
Rosetta FastAPI 后端 - 邮件服务模块

提供异步邮件发送功能，包括：
- 异步邮件发送
- 邮件模板支持
- 邮件队列管理
- 多种邮件类型支持

Example:
    >>> from backend.services.email_service import EmailService, get_email_service
    >>>
    >>> email_service = get_email_service()
    >>> await email_service.send_welcome_email("user@example.com", "用户名")
"""

import asyncio
import logging
import smtplib
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.core.config import settings
from backend.core.tasks import BackgroundTaskManager, background_task

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    """
    邮件消息数据类

    Attributes:
        to: 收件人邮箱
        subject: 邮件主题
        body: 邮件正文（纯文本）
        html_body: 邮件正文（HTML）
        from_email: 发件人邮箱
        from_name: 发件人名称
        reply_to: 回复地址
        cc: 抄送列表
        bcc: 密送列表
        attachments: 附件列表
        created_at: 创建时间
        metadata: 元数据
    """

    to: str
    subject: str
    body: str | None = None
    html_body: str | None = None
    from_email: str | None = None
    from_name: str | None = None
    reply_to: str | None = None
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    attachments: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EmailResult:
    """
    邮件发送结果数据类

    Attributes:
        success: 是否成功
        message_id: 消息 ID
        error: 错误信息
        sent_at: 发送时间
    """

    success: bool
    message_id: str | None = None
    error: str | None = None
    sent_at: datetime = field(default_factory=datetime.now)


class EmailTemplateEngine:
    """
    邮件模板引擎

    使用 Jinja2 渲染邮件模板。

    Attributes:
        template_dir: 模板目录
        environment: Jinja2 环境
    """

    def __init__(self, template_dir: str | Path | None = None):
        """
        初始化模板引擎

        Args:
            template_dir: 模板目录路径，默认为 backend/templates/email
        """
        if template_dir is None:
            template_dir = Path(__file__).parent.parent / "templates" / "email"
        self.template_dir = Path(template_dir)

        if self.template_dir.exists():
            self.environment = Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                autoescape=select_autoescape(["html", "xml"]),
            )
        else:
            self.environment = None
            logger.warning(f"邮件模板目录不存在: {self.template_dir}")

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """
        渲染模板

        Args:
            template_name: 模板文件名
            context: 模板上下文

        Returns:
            str: 渲染后的 HTML

        Raises:
            FileNotFoundError: 模板文件不存在
        """
        if self.environment is None:
            raise FileNotFoundError("邮件模板目录不存在")

        template = self.environment.get_template(template_name)
        return template.render(**context)

    def render_text(self, template_name: str, context: dict[str, Any]) -> str:
        """
        渲染纯文本模板

        Args:
            template_name: 模板文件名
            context: 模板上下文

        Returns:
            str: 渲染后的文本
        """
        if self.environment is None:
            raise FileNotFoundError("邮件模板目录不存在")

        template = self.environment.get_template(template_name)
        return template.render(**context)


class EmailService:
    """
    邮件服务类

    提供异步邮件发送、模板渲染、队列管理等功能。

    Attributes:
        smtp_host: SMTP 服务器地址
        smtp_port: SMTP 服务器端口
        smtp_user: SMTP 用户名
        smtp_password: SMTP 密码
        smtp_use_tls: 是否使用 TLS
        from_email: 默认发件人邮箱
        from_name: 默认发件人名称
        template_engine: 模板引擎
        task_manager: 后台任务管理器

    Example:
        >>> service = EmailService()
        >>> result = await service.send_email(
        ...     to="user@example.com",
        ...     subject="欢迎",
        ...     body="欢迎注册！"
        ... )
    """

    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        smtp_user: str | None = None,
        smtp_password: str | None = None,
        smtp_use_tls: bool | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
        template_dir: str | Path | None = None,
        task_manager: BackgroundTaskManager | None = None,
    ):
        """
        初始化邮件服务

        Args:
            smtp_host: SMTP 服务器地址
            smtp_port: SMTP 服务器端口
            smtp_user: SMTP 用户名
            smtp_password: SMTP 密码
            smtp_use_tls: 是否使用 TLS
            from_email: 默认发件人邮箱
            from_name: 默认发件人名称
            template_dir: 模板目录
            task_manager: 后台任务管理器
        """
        self.smtp_host = smtp_host or settings.smtp_host
        self.smtp_port = smtp_port or settings.smtp_port
        self.smtp_user = smtp_user or settings.smtp_user
        self.smtp_password = smtp_password or settings.smtp_password
        self.smtp_use_tls = smtp_use_tls if smtp_use_tls is not None else settings.smtp_use_tls
        self.from_email = from_email or settings.smtp_from_email or self.smtp_user
        self.from_name = from_name or settings.site_name
        self.template_engine = EmailTemplateEngine(template_dir)
        self._task_manager = task_manager

    @property
    def is_configured(self) -> bool:
        """
        检查邮件服务是否已配置

        Returns:
            bool: 是否已配置 SMTP
        """
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    def _create_message(self, email: EmailMessage) -> MIMEMultipart:
        """
        创建 MIME 消息对象

        Args:
            email: 邮件消息

        Returns:
            MIMEMultipart: MIME 消息对象
        """
        msg = MIMEMultipart("alternative")

        from_name = email.from_name or self.from_name
        from_email = email.from_email or self.from_email
        msg["From"] = formataddr((from_name, from_email))
        msg["To"] = email.to
        msg["Subject"] = email.subject

        if email.reply_to:
            msg["Reply-To"] = email.reply_to

        if email.cc:
            msg["Cc"] = ", ".join(email.cc)

        if email.bcc:
            msg["Bcc"] = ", ".join(email.bcc)

        if email.body:
            msg.attach(MIMEText(email.body, "plain", "utf-8"))

        if email.html_body:
            msg.attach(MIMEText(email.html_body, "html", "utf-8"))

        return msg

    async def _send_sync(self, email: EmailMessage) -> EmailResult:
        """
        同步发送邮件（内部方法）

        Args:
            email: 邮件消息

        Returns:
            EmailResult: 发送结果
        """
        if not self.is_configured:
            logger.warning("邮件服务未配置，跳过发送")
            return EmailResult(
                success=False,
                error="邮件服务未配置",
            )

        try:
            msg = self._create_message(email)

            recipients = [email.to]
            if email.cc:
                recipients.extend(email.cc)
            if email.bcc:
                recipients.extend(email.bcc)

            loop = asyncio.get_event_loop()

            def send() -> None:
                if self.smtp_use_tls:
                    smtp = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
                else:
                    smtp = smtplib.SMTP(self.smtp_host, self.smtp_port)
                    smtp.starttls()

                smtp.login(self.smtp_user, self.smtp_password)
                smtp.sendmail(self.from_email, recipients, msg.as_string())
                smtp.quit()

            await loop.run_in_executor(None, send)

            logger.info(f"邮件发送成功: {email.to} - {email.subject}")
            return EmailResult(success=True)

        except Exception as e:
            logger.error(f"邮件发送失败: {email.to} - {email.subject}, 错误: {e}")
            return EmailResult(success=False, error=str(e))

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str | None = None,
        html_body: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
        reply_to: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        background: bool = True,
    ) -> EmailResult | str:
        """
        发送邮件

        Args:
            to: 收件人邮箱
            subject: 邮件主题
            body: 纯文本正文
            html_body: HTML 正文
            from_email: 发件人邮箱
            from_name: 发件人名称
            reply_to: 回复地址
            cc: 抄送列表
            bcc: 密送列表
            background: 是否后台发送

        Returns:
            EmailResult | str: 发送结果或任务 ID（后台发送时）
        """
        email = EmailMessage(
            to=to,
            subject=subject,
            body=body,
            html_body=html_body,
            from_email=from_email,
            from_name=from_name,
            reply_to=reply_to,
            cc=cc or [],
            bcc=bcc or [],
        )

        if background and self._task_manager:
            task_id = await self._task_manager.submit(
                self._send_sync,
                email,
                name="send_email",
                timeout=60.0,
                max_retries=3,
            )
            return task_id

        return await self._send_sync(email)

    async def send_template_email(
        self,
        to: str,
        subject: str,
        template_name: str,
        context: dict[str, Any],
        text_template_name: str | None = None,
        background: bool = True,
    ) -> EmailResult | str:
        """
        发送模板邮件

        Args:
            to: 收件人邮箱
            subject: 邮件主题
            template_name: HTML 模板文件名
            context: 模板上下文
            text_template_name: 纯文本模板文件名
            background: 是否后台发送

        Returns:
            EmailResult | str: 发送结果或任务 ID
        """
        html_body = self.template_engine.render(template_name, context)

        body = None
        if text_template_name:
            body = self.template_engine.render_text(text_template_name, context)

        return await self.send_email(
            to=to,
            subject=subject,
            body=body,
            html_body=html_body,
            background=background,
        )

    async def send_welcome_email(
        self,
        to: str,
        username: str,
        background: bool = True,
    ) -> EmailResult | str:
        """
        发送欢迎邮件

        Args:
            to: 收件人邮箱
            username: 用户名
            background: 是否后台发送

        Returns:
            EmailResult | str: 发送结果或任务 ID
        """
        context = {
            "username": username,
            "site_name": settings.site_name,
            "site_url": settings.site_url,
        }

        try:
            return await self.send_template_email(
                to=to,
                subject=f"欢迎加入 {settings.site_name}",
                template_name="welcome.html",
                context=context,
                background=background,
            )
        except FileNotFoundError:
            html_body = f"""
            <html>
            <body>
                <h2>欢迎加入 {settings.site_name}！</h2>
                <p>亲爱的 {username}，</p>
                <p>感谢您注册 {settings.site_name}。我们很高兴您的加入！</p>
                <p>请访问 <a href="{settings.site_url}">{settings.site_url}</a> 开始您的旅程。</p>
                <br>
                <p>祝好，</p>
                <p>{settings.site_name} 团队</p>
            </body>
            </html>
            """
            return await self.send_email(
                to=to,
                subject=f"欢迎加入 {settings.site_name}",
                html_body=html_body,
                background=background,
            )

    async def send_notification_email(
        self,
        to: str,
        title: str,
        content: str,
        link: str | None = None,
        background: bool = True,
    ) -> EmailResult | str:
        """
        发送通知邮件

        Args:
            to: 收件人邮箱
            title: 通知标题
            content: 通知内容
            link: 相关链接
            background: 是否后台发送

        Returns:
            EmailResult | str: 发送结果或任务 ID
        """
        context = {
            "title": title,
            "content": content,
            "link": link,
            "site_name": settings.site_name,
            "site_url": settings.site_url,
        }

        try:
            return await self.send_template_email(
                to=to,
                subject=f"[{settings.site_name}] {title}",
                template_name="notification.html",
                context=context,
                background=background,
            )
        except FileNotFoundError:
            link_html = f'<p><a href="{link}">点击查看详情</a></p>' if link else ""
            html_body = f"""
            <html>
            <body>
                <h2>{title}</h2>
                <p>{content}</p>
                {link_html}
                <br>
                <p>{settings.site_name}</p>
            </body>
            </html>
            """
            return await self.send_email(
                to=to,
                subject=f"[{settings.site_name}] {title}",
                html_body=html_body,
                background=background,
            )

    async def send_password_reset_email(
        self,
        to: str,
        username: str,
        reset_link: str,
        expire_hours: int = 24,
        background: bool = True,
    ) -> EmailResult | str:
        """
        发送密码重置邮件

        Args:
            to: 收件人邮箱
            username: 用户名
            reset_link: 重置链接
            expire_hours: 链接过期时间（小时）
            background: 是否后台发送

        Returns:
            EmailResult | str: 发送结果或任务 ID
        """
        context = {
            "username": username,
            "reset_link": reset_link,
            "expire_hours": expire_hours,
            "site_name": settings.site_name,
            "site_url": settings.site_url,
        }

        try:
            return await self.send_template_email(
                to=to,
                subject=f"[{settings.site_name}] 密码重置",
                template_name="password_reset.html",
                context=context,
                background=background,
            )
        except FileNotFoundError:
            html_body = f"""
            <html>
            <body>
                <h2>密码重置</h2>
                <p>亲爱的 {username}，</p>
                <p>您收到这封邮件是因为您请求重置密码。</p>
                <p>请点击以下链接重置密码：</p>
                <p><a href="{reset_link}">{reset_link}</a></p>
                <p>此链接将在 {expire_hours} 小时后过期。</p>
                <p>如果您没有请求重置密码，请忽略此邮件。</p>
                <br>
                <p>{settings.site_name}</p>
            </body>
            </html>
            """
            return await self.send_email(
                to=to,
                subject=f"[{settings.site_name}] 密码重置",
                html_body=html_body,
                background=background,
            )

    async def send_verification_email(
        self,
        to: str,
        username: str,
        verification_link: str,
        background: bool = True,
    ) -> EmailResult | str:
        """
        发送邮箱验证邮件

        Args:
            to: 收件人邮箱
            username: 用户名
            verification_link: 验证链接
            background: 是否后台发送

        Returns:
            EmailResult | str: 发送结果或任务 ID
        """
        context = {
            "username": username,
            "verification_link": verification_link,
            "site_name": settings.site_name,
            "site_url": settings.site_url,
        }

        try:
            return await self.send_template_email(
                to=to,
                subject=f"[{settings.site_name}] 邮箱验证",
                template_name="email_verification.html",
                context=context,
                background=background,
            )
        except FileNotFoundError:
            html_body = f"""
            <html>
            <body>
                <h2>邮箱验证</h2>
                <p>亲爱的 {username}，</p>
                <p>请点击以下链接验证您的邮箱地址：</p>
                <p><a href="{verification_link}">{verification_link}</a></p>
                <br>
                <p>{settings.site_name}</p>
            </body>
            </html>
            """
            return await self.send_email(
                to=to,
                subject=f"[{settings.site_name}] 邮箱验证",
                html_body=html_body,
                background=background,
            )

    async def send_comment_notification(
        self,
        to: str,
        post_title: str,
        commenter_name: str,
        comment_content: str,
        post_link: str,
        background: bool = True,
    ) -> EmailResult | str:
        """
        发送评论通知邮件

        Args:
            to: 收件人邮箱
            post_title: 文章标题
            commenter_name: 评论者名称
            comment_content: 评论内容
            post_link: 文章链接
            background: 是否后台发送

        Returns:
            EmailResult | str: 发送结果或任务 ID
        """
        context = {
            "post_title": post_title,
            "commenter_name": commenter_name,
            "comment_content": comment_content,
            "post_link": post_link,
            "site_name": settings.site_name,
            "site_url": settings.site_url,
        }

        try:
            return await self.send_template_email(
                to=to,
                subject=f"[{settings.site_name}] 您的文章收到了新评论",
                template_name="comment_notification.html",
                context=context,
                background=background,
            )
        except FileNotFoundError:
            html_body = f"""
            <html>
            <body>
                <h2>新评论通知</h2>
                <p>您的文章《{post_title}》收到了新评论：</p>
                <blockquote>{comment_content}</blockquote>
                <p>—— {commenter_name}</p>
                <p><a href="{post_link}">点击查看详情</a></p>
                <br>
                <p>{settings.site_name}</p>
            </body>
            </html>
            """
            return await self.send_email(
                to=to,
                subject=f"[{settings.site_name}] 您的文章收到了新评论",
                html_body=html_body,
                background=background,
            )

    def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """
        获取后台邮件任务状态

        Args:
            task_id: 任务 ID

        Returns:
            dict | None: 任务状态信息
        """
        if not self._task_manager:
            return None

        result = self._task_manager.get_task_status(task_id)
        return result.to_dict() if result else None


@background_task(name="send_email_task", max_retries=3)
async def send_email_task(
    to: str,
    subject: str,
    body: str | None = None,
    html_body: str | None = None,
) -> EmailResult:
    """
    后台邮件发送任务

    Args:
        to: 收件人邮箱
        subject: 邮件主题
        body: 纯文本正文
        html_body: HTML 正文

    Returns:
        EmailResult: 发送结果
    """
    service = EmailService()
    email = EmailMessage(
        to=to,
        subject=subject,
        body=body,
        html_body=html_body,
    )
    return await service._send_sync(email)


def get_email_service(
    task_manager: BackgroundTaskManager | None = None,
) -> EmailService:
    """
    获取邮件服务实例

    Args:
        task_manager: 后台任务管理器

    Returns:
        EmailService: 邮件服务实例
    """
    from backend.core.tasks import task_manager as default_task_manager

    return EmailService(task_manager=task_manager or default_task_manager)
