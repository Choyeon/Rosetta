"""
系统环境检测服务

提供安装/初始化向导所需的系统环境探测：
- 操作系统信息（正确识别 Windows 11 等）
- CPU 型号（`get_processor_name`，OOBE 侧共用同一实现）
- 硬件资源检测（内存、磁盘；psutil 缺失时 Windows 下用 ctypes 兜底）
"""

import logging
import platform
import socket
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SystemResource:
    """系统资源信息"""

    cpu_count: int
    cpu_percent: float
    memory_total: int
    memory_available: int
    memory_percent: float
    disk_total: int
    disk_available: int
    disk_percent: float


@dataclass
class SystemInfo:
    """系统信息"""

    platform: str
    system: str
    release: str
    version: str
    machine: str
    processor: str  # CPU 品牌/型号名称
    python_version: str
    hostname: str
    resources: SystemResource


def get_windows_version_display() -> str:
    """正确识别 Windows 版本（区分 Win10/Win11 通过 build 号）"""
    ver = platform.version()
    try:
        parts = ver.split(".")
        if len(parts) >= 3:
            build = int(parts[2])
            if build >= 22000:
                return "11"
    except (ValueError, IndexError):
        pass
    return platform.release()


def get_processor_name() -> str:
    """获取 CPU 品牌/型号名称（纯展示用；OOBE 与安装向导共用）

    探测失败时退回 `platform.machine()`。异常面只覆盖"探测本身可能失败"的类别
    （注册表/子进程/文件读取），编程错误一律外抛——把真实 bug 吞成一个看起来
    合理的架构名，会让下游排查完全失去线索。
    """
    system = platform.system()
    try:
        if system == "Windows":
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
            from pathlib import Path

            cpuinfo = Path("/proc/cpuinfo")
            if cpuinfo.exists():
                for line in cpuinfo.read_text(encoding="utf-8").splitlines():
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
    except (OSError, ValueError, UnicodeDecodeError, subprocess.SubprocessError) as exc:
        logger.debug("[setup] CPU 型号探测失败，退回架构名: %s", exc)
    return platform.machine()


def _get_os_display_name() -> str:
    """获取友好的操作系统名称"""
    system = platform.system()
    if system == "Windows":
        return f"Windows {get_windows_version_display()}"
    elif system == "Darwin":
        mac_ver = platform.mac_ver()[0]
        if mac_ver:
            return f"macOS {mac_ver}"
        return f"macOS {platform.release()}"
    elif system == "Linux":
        try:
            from pathlib import Path

            os_release = Path("/etc/os-release")
            if os_release.exists():
                for line in os_release.read_text(encoding="utf-8").splitlines():
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip('"')
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            logger.debug("[setup] /etc/os-release 解析失败，退回通用名: %s", exc)
        return f"Linux {platform.release()}"
    else:
        return f"{system} {platform.release()}"


def psutil_errors() -> tuple[type[BaseException], ...]:
    """psutil 探测允许吞掉的异常集合（OOBE 侧共用）

    psutil 虽在依赖清单里，但安装向导恰恰跑在"后端依赖可能还没装"的时机，
    ImportError 是真实分支。这里把它与系统调用/版本 API 不兼容类异常并列，
    其余异常（编程错误）一律外抛——否则探测代码写错也会伪装成
    "这项指标拿不到"，最终以 0 值提交给安装判定。
    """
    errors: list[type[BaseException]] = [ImportError, OSError, ValueError, AttributeError]
    try:
        from psutil import Error as PsutilError  # type: ignore
    except ImportError:
        PsutilError = None  # type: ignore[assignment]
    if PsutilError is not None:
        errors.append(PsutilError)
    return tuple(errors)


class SystemService:
    """系统环境检测服务"""

    def __init__(self):
        self.is_windows = platform.system() == "Windows"

    def get_system_info(self) -> SystemInfo:
        """获取系统信息"""
        return SystemInfo(
            platform=platform.system(),
            system=_get_os_display_name(),
            release=platform.release(),
            version=platform.version(),
            machine=platform.machine(),
            processor=get_processor_name(),
            python_version=platform.python_version(),
            hostname=socket.gethostname(),
            resources=self.get_system_resources(),
        )

    def get_system_resources(self) -> SystemResource:
        """获取系统资源信息"""
        try:
            import psutil  # type: ignore

            cpu_count = psutil.cpu_count() or 1
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk_path = "C:\\" if self.is_windows else "/"
            disk = psutil.disk_usage(disk_path)

            return SystemResource(
                cpu_count=cpu_count,
                cpu_percent=cpu_percent,
                memory_total=memory.total,
                memory_available=memory.available,
                memory_percent=memory.percent,
                disk_total=disk.total,
                disk_available=disk.free,
                disk_percent=disk.percent,
            )
        except psutil_errors() as exc:
            logger.debug("[setup] psutil 资源探测失败，尝试 ctypes 兜底: %s", exc)
            try:
                import ctypes

                kernel32 = ctypes.windll.kernel32

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

                memStatus = MEMORYSTATUSEX()
                memStatus.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                kernel32.GlobalMemoryStatusEx(ctypes.byref(memStatus))

                free_bytes = ctypes.c_ulonglong(0)
                total_bytes = ctypes.c_ulonglong(0)
                kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p("C:\\"),
                    None,
                    ctypes.byref(total_bytes),
                    ctypes.byref(free_bytes),
                )

                return SystemResource(
                    cpu_count=1,
                    cpu_percent=0,
                    memory_total=memStatus.ullTotalPhys,
                    memory_available=memStatus.ullAvailPhys,
                    memory_percent=memStatus.dwMemoryLoad,
                    disk_total=total_bytes.value,
                    disk_available=free_bytes.value,
                    disk_percent=0,
                )
            except (OSError, ValueError, AttributeError) as exc:
                # ctypes 兜底只在 Windows 上有效；非 Windows 或调用失败时返回全 0，
                # 由前端显示为"未知"。必须留痕，否则资源探测永久失效也无人知晓。
                logger.debug("[setup] ctypes 资源兜底探测失败，返回 0 值: %s", exc)
                return SystemResource(
                    cpu_count=1,
                    cpu_percent=0,
                    memory_total=0,
                    memory_available=0,
                    memory_percent=0,
                    disk_total=0,
                    disk_available=0,
                    disk_percent=0,
                )
