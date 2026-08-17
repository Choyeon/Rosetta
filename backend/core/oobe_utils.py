"""
OOBE 工具函数 — 环境检测、校验等可复用逻辑

从 oobe.py 的 oobe_check_environment 中提取的独立工具函数，
避免大函数耦合在 API 路由中，便于测试和复用。
"""

import ctypes
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Windows build 号阈值：>= 22000 是 Windows 11
_WIN11_BUILD_THRESHOLD = 22000


def _ok(value=None, ok: bool = True, error: str | None = None) -> dict:
    """返回标准化的检测结果"""
    return {"ok": ok, "value": value, "error": error}


def _get_windows_version_display() -> str:
    """正确识别 Windows 版本（区分 Win10/Win11）

    platform.release() 在 Windows 11 上仍返回 '10'，
    需要通过 build 号判断：build >= 22000 为 Windows 11。
    """
    rel = platform.release()
    ver = platform.version()  # 如 "10.0.22621"
    try:
        parts = ver.split(".")
        if len(parts) >= 3:
            build = int(parts[2])
            if build >= _WIN11_BUILD_THRESHOLD:
                return "11"
    except (ValueError, IndexError):
        pass
    return rel


def _get_os_name() -> str:
    """获取友好的操作系统名称，如 'Windows 11', 'macOS 14', 'Ubuntu 22.04'"""
    system = platform.system()
    if system == "Windows":
        return f"Windows {_get_windows_version_display()}"
    elif system == "Darwin":
        rel = platform.release()
        mac_ver = platform.mac_ver()[0]
        if mac_ver:
            return f"macOS {mac_ver}"
        return f"macOS {rel}"
    elif system == "Linux":
        # 尝试读取 /etc/os-release 获取发行版名称
        try:
            import distro  # type: ignore

            name = distro.name(pretty=True)
            if name:
                return name
        except ImportError:
            pass
        try:
            os_release = Path("/etc/os-release")
            if os_release.exists():
                for line in os_release.read_text(encoding="utf-8").splitlines():
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip('"')
        except Exception:  # noqa: BLE001
            pass
        return f"Linux {platform.release()}"
    else:
        return f"{system} {platform.release()}"


def _get_cpu_name() -> str:
    """获取 CPU 品牌/型号名称"""
    system = platform.system()
    try:
        if system == "Windows":
            # 通过注册表读取 CPU 名称
            import winreg  # type: ignore

            key_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                return str(name).strip()
        elif system == "Darwin":
            r = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        elif system == "Linux":
            cpuinfo = Path("/proc/cpuinfo")
            if cpuinfo.exists():
                for line in cpuinfo.read_text(encoding="utf-8").splitlines():
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
    except Exception as e:  # noqa: BLE001
        logger.debug("Failed to get CPU name: %s", e)

    # Fallback: 返回通用描述
    arch = platform.machine()
    return f"{arch} processor"


def check_python_version() -> dict:
    """检测 Python 版本"""
    return _ok(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


def _is_windows_executable(path: Path) -> bool:
    """检查文件是否是 Windows 可执行文件（.exe/.cmd/.bat/.ps1/.com）"""
    if not path.is_file():
        return False
    suf = path.suffix.lower()
    return suf in (".exe", ".cmd", ".bat", ".com", ".ps1")


def run_command_check(name: str, cmd: list[str]) -> dict:
    """运行命令并返回检测结果

    Windows 下针对命令查找做了多层 fallback：
    1. shutil.which 找到的绝对路径（优先 .exe/.cmd/.bat 等可执行扩展名）
    2. Windows 系统目录（通过 where.exe 查找）
    3. 项目本地 frontend/node_modules/.bin 下的 shim（仅 Windows 可执行文件）
    4. 项目 .venv/Scripts 下的可执行文件
    避免 [WinError 2]（找不到文件）和 [WinError 193]（不是有效的 Win32 应用，bash 脚本）。
    """
    if not cmd:
        return _ok(None, ok=False, error="empty command")

    base = cmd[0]
    rest = cmd[1:]
    is_windows = platform.system() == "Windows"
    project_root = Path(__file__).resolve().parent.parent.parent
    candidates: list[list[str]] = []

    # ---- 1. shutil.which 绝对路径（最可靠） ----
    which_path = shutil.which(base)
    if which_path:
        wp = Path(which_path)
        if not is_windows or _is_windows_executable(wp):
            candidates.append([str(wp), *rest])
        else:
            # which 找到的不是 Windows 可执行文件（可能是 bash 脚本），
            # 尝试同名的 .cmd/.exe 版本
            for ext in (".cmd", ".exe", ".bat", ".ps1"):
                alt = wp.with_suffix(ext)
                if alt.is_file():
                    candidates.append([str(alt), *rest])
                    break

    # ---- 2. Windows 上：用 where.exe 查找所有匹配，逐一尝试 ----
    if is_windows:
        try:
            wr = subprocess.run(
                ["where.exe", base], capture_output=True, text=True, timeout=5
            )
            if wr.returncode == 0 and wr.stdout.strip():
                for line in wr.stdout.strip().splitlines():
                    p = Path(line.strip())
                    if p.is_file() and _is_windows_executable(p):
                        sp = str(p)
                        if not any(c[0] == sp for c in candidates):
                            candidates.append([sp, *rest])
        except Exception:  # noqa: BLE001
            pass

    # ---- 3. 项目本地 frontend/node_modules/.bin ----
    frontend_bin = project_root / "frontend" / "node_modules" / ".bin"
    if frontend_bin.is_dir():
        if is_windows:
            for ext in (".cmd", ".exe", ".bat", ".ps1"):
                p = frontend_bin / f"{base}{ext}"
                if p.is_file():
                    candidates.append([str(p), *rest])
        else:
            p = frontend_bin / base
            if p.is_file() and os.access(str(p), os.X_OK):
                candidates.append([str(p), *rest])

    # ---- 4. 项目 .venv/Scripts ----
    if is_windows:
        venv_scripts = project_root / ".venv" / "Scripts"
        for ext in (".exe", ".cmd", ".bat"):
            p = venv_scripts / f"{base}{ext}"
            if p.is_file():
                candidates.append([str(p), *rest])
    else:
        venv_bin = project_root / ".venv" / "bin"
        p = venv_bin / base
        if p.is_file() and os.access(str(p), os.X_OK):
            candidates.append([str(p), *rest])

    # ---- 5. 最后才尝试裸名（可能因 shell/PATHEXT 问题失败） ----
    if not is_windows:
        candidates.append(cmd)

    # ---- 执行候选命令 ----
    last_error: str | None = None
    for candidate in candidates:
        try:
            r = subprocess.run(
                candidate, capture_output=True, text=True, timeout=8
            )
            stdout = (r.stdout or "").strip()
            stderr = (r.stderr or "").strip()
            if r.returncode == 0 and stdout:
                # 提取版本号：去除前导 v，取第一行
                version = stdout.lstrip("v").splitlines()[0].strip()
                return _ok(version)
            # 非零退出码或无 stdout
            if not last_error:
                last_error = stderr or f"exit code {r.returncode}"
        except FileNotFoundError:
            continue
        except OSError as e:
            # WinError 193 = ERROR_BAD_EXE_FORMAT（不是有效的 Win32 应用）
            # 通常是找到了 bash 脚本而非 .cmd/.exe，继续下一个
            if getattr(e, "winerror", None) == 193 or getattr(e, "errno", None) == 193:
                continue
            if not last_error:
                last_error = str(e)
        except subprocess.TimeoutExpired as e:
            last_error = f"timeout: {e}"
            break
        except Exception as e:  # noqa: BLE001
            if not last_error:
                last_error = str(e)

    # 兜底：友好提示安装方式
    if not last_error:
        last_error = "not found in PATH or project directories"
    friendly: dict[str, str] = {
        "pnpm": "请运行 `npm install -g pnpm` 或启用 Corepack: `corepack enable`",
        "node": "请安装 Node.js ≥ 20 LTS (https://nodejs.org/)",
        "uv": "请按 https://docs.astral.sh/uv/getting-started/installation/ 安装 uv",
        "npm": "通常随 Node.js 一起安装，可尝试重装 Node.js LTS",
    }
    if base in friendly:
        last_error = f"{last_error} — {friendly[base]}"
    return _ok(None, ok=False, error=last_error)


def check_uv_installed() -> dict:
    """检测 uv 是否安装（复用 run_command_check 保证 Windows 兼容性）"""
    result = run_command_check("uv", ["uv", "--version"])
    if result["ok"] and result["value"]:
        raw_version = str(result["value"])
        # uv --version 输出类似 "uv 0.12.0 (b88d7c5c4 2026-07-28 x86_64-pc-windows-msvc)"
        # 提取纯版本号（第二部分）
        version = raw_version
        parts = raw_version.split()
        if len(parts) >= 2:
            version = parts[1]
        out = {
            "ok": True,
            "value": True,
            "error": None,
            "uv_version": version,
        }
        return out
    return {
        "ok": False,
        "value": False,
        "error": result.get("error", "not detected"),
    }


async def check_database_connectivity() -> dict:
    """检测数据库连接"""
    try:
        from backend.core.database import check_db_connection

        db_ok = await check_db_connection()
        return _ok(db_ok, ok=db_ok, error=None if db_ok else "数据库连接失败")
    except Exception as e:  # noqa: BLE001
        return _ok(False, ok=False, error=str(e))


async def check_redis_connectivity() -> dict:
    """检测 Redis 连接

    Redis 是可选组件（开发环境用 SQLite 时不需要），
    因此连接失败只返回 warning 级别，不阻断 OOBE 流程。
    """
    try:
        import redis.asyncio as aioredis

        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        client = aioredis.from_url(
            redis_url, decode_responses=True, socket_connect_timeout=2
        )
        try:
            redis_ok = bool(await client.ping())
            return _ok(redis_ok, ok=redis_ok)
        finally:
            await client.aclose()
    except ImportError:
        # redis 库未安装，标记为可选
        return _ok(False, ok=True, error="redis 库未安装（可选组件，不影响基础功能）")
    except Exception as e:  # noqa: BLE001
        # Redis 未启动或连接失败，标记为 warning（非致命）
        return _ok(
            False,
            ok=True,  # 不阻断流程
            error=f"Redis 未运行（可选组件）：{e}",
        )


def _fmt_bytes(num_bytes: float) -> str:
    """把字节数格式化为人类可读：保留 1 位小数"""
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(num_bytes)
    for u in units:
        if size < 1024.0 or u == units[-1]:
            return f"{size:.1f} {u}"
        size /= 1024.0
    return f"{size:.1f} PB"


def _os_summary() -> dict:
    """返回系统信息字典

    包含 os_name, arch, cpu_name, cpu_count, total_mem_MB, avail_mem_MB,
    total_disk_GB, avail_disk_GB 等字段。
    尽力而为；任何一项拿不到就放一个保守默认值。
    """
    system_name = platform.system()
    arch = platform.machine()
    cpu_count = os.cpu_count() or 1
    cpu_name = _get_cpu_name()
    os_name = _get_os_name()
    total_mem = 0
    avail_mem = 0
    total_disk = 0
    avail_disk = 0

    # 优先使用 psutil
    try:
        import psutil  # type: ignore

        cpu_count = psutil.cpu_count() or cpu_count
        mem = psutil.virtual_memory()
        total_mem = mem.total
        avail_mem = mem.available
        disk_path = "C:\\" if system_name == "Windows" else "/"
        disk = psutil.disk_usage(disk_path)
        total_disk = disk.total
        avail_disk = disk.free
    except Exception:  # noqa: BLE001
        # psutil 不可用时，Windows 下用 ctypes 兜底
        if system_name == "Windows":
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
                total_mem = ms.ullTotalPhys
                avail_mem = ms.ullAvailPhys

                free_bytes = ctypes.c_ulonglong(0)
                total_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p("C:\\"),
                    None,
                    ctypes.byref(total_bytes),
                    ctypes.byref(free_bytes),
                )
                total_disk = total_bytes.value
                avail_disk = free_bytes.value
            except Exception:  # noqa: BLE001
                pass

    # 转换单位
    total_mem_MB = round(total_mem / (1024 * 1024)) if total_mem else 0
    avail_mem_MB = round(avail_mem / (1024 * 1024)) if avail_mem else 0
    total_disk_GB = round(total_disk / (1024 * 1024 * 1024)) if total_disk else 0
    avail_disk_GB = round(avail_disk / (1024 * 1024 * 1024)) if avail_disk else 0

    os_summary = f"{os_name} · {arch} · {cpu_count} CPU 核"
    return {
        "os_summary": os_summary,
        "os_name": os_name,
        "arch": arch,
        "cpu_name": cpu_name,
        "cpu_count": cpu_count,
        "total_mem_MB": total_mem_MB,
        "avail_mem_MB": avail_mem_MB,
        "total_disk_GB": total_disk_GB,
        "avail_disk_GB": avail_disk_GB,
    }


# 缓存系统摘要：OOBE 检查这几个函数通常一次请求一起调用，没必要重复读系统参数
_OS_CACHE: dict[str, object] | None = None


def _get_os_cache() -> dict[str, object]:
    global _OS_CACHE
    if _OS_CACHE is None:
        _OS_CACHE = _os_summary()
    return _OS_CACHE


def reset_os_cache() -> None:
    """重置系统信息缓存（用于测试）"""
    global _OS_CACHE
    _OS_CACHE = None


def check_disk_free_gb() -> dict:
    """检测磁盘可用空间（GB）。附带总量、使用率、系统摘要等丰富信息。"""
    cache = _get_os_cache()
    avail_gb = int(cache.get("avail_disk_GB", 0) or 0)
    total_gb = int(cache.get("total_disk_GB", 0) or 0)
    used_gb = max(total_gb - avail_gb, 0)
    usage_pct = 0
    if total_gb > 0:
        usage_pct = round(used_gb / total_gb * 100)
    os_info = str(cache.get("os_summary", ""))
    disk_path = "C:\\" if platform.system() == "Windows" else "/"
    display = f"可用 {avail_gb} GB / 总量 {total_gb} GB · 使用率 {usage_pct}% · 卷 {disk_path}"
    extra_error = None if avail_gb >= 2 else f"剩余空间偏低（建议 ≥ 2 GB，当前仅 {avail_gb} GB）"
    result = _ok(float(avail_gb), ok=avail_gb >= 2, error=extra_error)
    result["display"] = display
    result["os_summary"] = os_info
    result["total_gb"] = total_gb
    result["used_gb"] = used_gb
    result["usage_pct"] = int(usage_pct)
    result["path"] = disk_path
    return result


def check_memory_free_mb() -> dict:
    """检测可用内存（MB）。附带总量、使用率、单位格式化显示。"""
    cache = _get_os_cache()
    avail_mb = int(cache.get("avail_mem_MB", 0) or 0)
    total_mb = int(cache.get("total_mem_MB", 0) or 0)
    used_mb = max(total_mb - avail_mb, 0)
    usage_pct = 0
    if total_mb > 0:
        usage_pct = round(used_mb / total_mb * 100)
    avail_gb = round(avail_mb / 1024, 1)
    total_gb = round(total_mb / 1024, 1)
    used_gb = round(used_mb / 1024, 1)
    cpu_count = int(cache.get("cpu_count", 1) or 1)
    cpu_name = str(cache.get("cpu_name", ""))
    arch = str(cache.get("arch", ""))
    display = f"可用 {avail_gb} GB / 总量 {total_gb} GB · 使用率 {usage_pct}%"
    ok = avail_mb >= 1024  # 内存建议 ≥ 1 GB（开发模式）
    extra_error = None if ok else f"可用内存偏低（建议 ≥ 1 GB，当前仅 {avail_gb} GB）"
    result = _ok(float(avail_mb), ok=ok, error=extra_error)
    result["display"] = display
    result["cpu_count"] = cpu_count
    result["cpu_name"] = cpu_name
    result["arch"] = arch
    result["total_mb"] = total_mb
    result["used_mb"] = used_mb
    result["usage_pct"] = int(usage_pct)
    result["avail_gb"] = avail_gb
    result["total_gb"] = total_gb
    result["used_gb"] = used_gb
    result["os_summary"] = cache.get("os_summary", "")
    return result
