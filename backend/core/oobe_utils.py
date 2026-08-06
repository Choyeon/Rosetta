"""
OOBE 工具函数 — 环境检测、校验等可复用逻辑

从 oobe.py 的 oobe_check_environment 中提取的独立工具函数，
避免大函数耦合在 API 路由中，便于测试和复用。
"""

import ctypes
import logging
import platform
import subprocess
import sys
from typing import Any

logger = logging.getLogger(__name__)


def _ok(value=None, ok: bool = True, error: str | None = None) -> dict:
    """返回标准化的检测结果"""
    return {"ok": ok, "value": value, "error": error}


def check_python_version() -> dict:
    """检测 Python 版本"""
    return _ok(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


def run_command_check(name: str, cmd: list[str]) -> dict:
    """运行命令并返回检测结果

    Args:
        name: 检测项名称（用于日志）
        cmd: 要执行的命令列表

    Returns:
        {"ok": bool, "value": Any, "error": str | None}
    """
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if r.returncode == 0 and r.stdout.strip():
            version = r.stdout.strip().lstrip("v").splitlines()[0].strip()
            return _ok(version)
        else:
            err = (r.stderr or "").strip() or "non-zero exit"
            return _ok(None, ok=False, error=err)
    except FileNotFoundError as e:
        return _ok(None, ok=False, error=str(e))
    except subprocess.TimeoutExpired as e:
        return _ok(None, ok=False, error=f"timeout: {e}")
    except Exception as e:
        return _ok(None, ok=False, error=str(e))


def check_uv_installed() -> dict:
    """检测 uv 是否安装"""
    try:
        r = subprocess.run(["uv", "--version"], capture_output=True, text=True, timeout=8)
        if r.returncode == 0 and r.stdout.strip():
            result = _ok(True)
            result["uv_version"] = r.stdout.strip().lstrip("v").splitlines()[0].strip()
            return result
        return _ok(False, ok=False, error=(r.stderr or "").strip() or "non-zero exit")
    except FileNotFoundError as e:
        return _ok(False, ok=False, error=str(e))
    except subprocess.TimeoutExpired as e:
        return _ok(False, ok=False, error=f"timeout: {e}")
    except Exception as e:
        return _ok(False, ok=False, error=str(e))


async def check_database_connectivity() -> dict:
    """检测数据库连接"""
    try:
        from backend.core.database import check_db_connection

        db_ok = await check_db_connection()
        return _ok(db_ok, ok=db_ok)
    except Exception as e:
        return _ok(False, ok=False, error=str(e))


async def check_redis_connectivity() -> dict:
    """检测 Redis 连接"""
    import os

    try:
        import redis.asyncio as aioredis

        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        client = aioredis.from_url(redis_url, decode_responses=True, socket_connect_timeout=3)
        try:
            redis_ok = bool(await client.ping())
            return _ok(redis_ok, ok=redis_ok)
        finally:
            await client.aclose()
    except ImportError:
        return _ok(False, ok=False, error="redis library not installed")
    except Exception as e:
        return _ok(False, ok=False, error=str(e))


def check_disk_free_gb() -> dict:
    """检测磁盘可用空间（GB）"""
    try:
        import psutil

        disk_path = "C:\\" if platform.system() == "Windows" else "/"
        usage = psutil.disk_usage(disk_path)
        free_gb = round(usage.free / (1024 * 1024 * 1024), 2)
        return _ok(free_gb, ok=True)
    except ImportError:
        try:
            free_bytes = ctypes.c_ulonglong(0)
            total_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p("C:\\"), None, ctypes.byref(total_bytes), ctypes.byref(free_bytes)
            )
            free_gb = round(free_bytes.value / (1024 * 1024 * 1024), 2)
            return _ok(free_gb, ok=True)
        except Exception as e:
            return _ok(None, ok=False, error=str(e))
    except Exception as e:
        return _ok(None, ok=False, error=str(e))


def check_memory_free_mb() -> dict:
    """检测可用内存（MB）"""
    try:
        import psutil

        mem = psutil.virtual_memory()
        free_mb = round(mem.available / (1024 * 1024), 2)
        return _ok(free_mb, ok=True)
    except ImportError:
        try:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            ms = MEMORYSTATUSEX()
            ms.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
            free_mb = round(ms.ullAvailPhys / (1024 * 1024), 2)
            return _ok(free_mb, ok=True)
        except Exception as e:
            return _ok(None, ok=False, error=str(e))
    except Exception as e:
        return _ok(None, ok=False, error=str(e))