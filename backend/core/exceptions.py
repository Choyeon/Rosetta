"""
Rosetta FastAPI 后端 - 异常处理模块

提供统一的异常处理机制，包括：
- 自定义异常类
- 异常处理器
- 错误响应格式

Example:
    >>> from backend.core.exceptions import AppException
    >>>
    >>> raise AppException(
    >>>     status_code=404,
    >>>     message="资源不存在",
    >>>     error_code="RESOURCE_NOT_FOUND"
    >>> )
"""

from typing import Any


class AppException(Exception):
    """
    应用异常基类

    所有自定义异常都应继承此类。

    Attributes:
        status_code: HTTP 状态码
        message: 错误消息
        error_code: 应用错误码
        details: 额外详情
    """

    def __init__(
        self,
        status_code: int = 500,
        message: str = "服务器内部错误",
        error_code: str | int = "INTERNAL_ERROR",
        details: Any = None,
    ):
        self.status_code = status_code
        self.message = message
        self.error_code = error_code
        self.details = details
        super().__init__(self.message)


class NotFoundException(AppException):
    """资源不存在异常"""

    def __init__(self, message: str = "资源不存在", details: Any = None):
        super().__init__(
            status_code=404,
            message=message,
            error_code="NOT_FOUND",
            details=details,
        )


class BadRequestException(AppException):
    """错误请求异常"""

    def __init__(self, message: str = "请求参数错误", details: Any = None):
        super().__init__(
            status_code=400,
            message=message,
            error_code="BAD_REQUEST",
            details=details,
        )


class UnauthorizedException(AppException):
    """未授权异常"""

    def __init__(self, message: str = "未授权访问", details: Any = None):
        super().__init__(
            status_code=401,
            message=message,
            error_code="UNAUTHORIZED",
            details=details,
        )


class ForbiddenException(AppException):
    """禁止访问异常"""

    def __init__(self, message: str = "禁止访问", details: Any = None):
        super().__init__(
            status_code=403,
            message=message,
            error_code="FORBIDDEN",
            details=details,
        )


class ConflictException(AppException):
    """冲突异常"""

    def __init__(self, message: str = "资源冲突", details: Any = None):
        super().__init__(
            status_code=409,
            message=message,
            error_code="CONFLICT",
            details=details,
        )


class ValidationException(AppException):
    """验证异常"""

    def __init__(self, message: str = "数据验证失败", details: Any = None):
        super().__init__(
            status_code=422,
            message=message,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class RateLimitException(AppException):
    """请求频率限制异常"""

    def __init__(self, message: str = "请求过于频繁", details: Any = None):
        super().__init__(
            status_code=429,
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details,
        )


class ServiceUnavailableException(AppException):
    """服务不可用异常"""

    def __init__(self, message: str = "服务暂时不可用", details: Any = None):
        super().__init__(
            status_code=503,
            message=message,
            error_code="SERVICE_UNAVAILABLE",
            details=details,
        )


OOBE_REQUIRED = "OOBE_REQUIRED"
OOBE_ALREADY_COMPLETED = "OOBE_ALREADY_COMPLETED"
WEAK_PASSWORD = "WEAK_PASSWORD"
ADMIN_NOT_CREATED = "ADMIN_NOT_CREATED"


class OOBERequiredException(AppException):
    """OOBE 未完成异常"""

    def __init__(self, message: str = "请先完成安装向导", details: Any = None):
        super().__init__(
            status_code=503,
            message=message,
            error_code=OOBE_REQUIRED,
            details=details,
        )


class OOBEAlreadyCompletedException(AppException):
    """OOBE 已完成异常"""

    def __init__(self, message: str = "OOBE 已完成，不可重复安装", details: Any = None):
        super().__init__(
            status_code=409,
            message=message,
            error_code=OOBE_ALREADY_COMPLETED,
            details=details,
        )


class WeakPasswordException(AppException):
    """弱密码异常"""

    def __init__(self, message: str = "管理员密码至少 8 位", details: Any = None):
        super().__init__(
            status_code=422,
            message=message,
            error_code=WEAK_PASSWORD,
            details=details,
        )


class AdminNotCreatedException(AppException):
    """管理员未创建异常"""

    def __init__(self, message: str = "管理员账户未配置", details: Any = None):
        super().__init__(
            status_code=400,
            message=message,
            error_code=ADMIN_NOT_CREATED,
            details=details,
        )


async def exception_handler(request, exc: AppException) -> dict:
    """
    异常处理器

    Args:
        request: 请求对象
        exc: 异常实例

    Returns:
        dict: 错误响应
    """
    return {
        "success": False,
        "message": exc.message,
        "error_code": exc.error_code,
        "details": exc.details,
    }
