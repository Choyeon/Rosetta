"""
系统环境检测服务

提供全面的系统环境检测功能：
- 操作系统信息
- 硬件资源检测
- 端口检测
- 权限检测
- 自动修复建议
"""

import platform
import socket
import subprocess
from dataclasses import dataclass
from typing import Any


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
class PortStatus:
    """端口状态"""

    port: int
    in_use: bool
    process: str | None = None


@dataclass
class SystemInfo:
    """系统信息"""

    platform: str
    system: str
    release: str
    version: str
    machine: str
    python_version: str
    hostname: str
    resources: SystemResource


class SystemService:
    """系统环境检测服务"""

    def __init__(self):
        self.is_windows = platform.system() == "Windows"
        self.is_linux = platform.system() == "Linux"
        self.is_macos = platform.system() == "Darwin"

    def get_system_info(self) -> SystemInfo:
        """获取系统信息"""
        return SystemInfo(
            platform=platform.system(),
            system=platform.system(),
            release=platform.release(),
            version=platform.version(),
            machine=platform.machine(),
            python_version=platform.python_version(),
            hostname=socket.gethostname(),
            resources=self.get_system_resources(),
        )

    def get_system_resources(self) -> SystemResource:
        """获取系统资源信息"""
        try:
            import psutil

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
        except ImportError:
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
            except Exception:
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

    def check_port(self, port: int, host: str = "localhost") -> PortStatus:
        """检测端口是否被占用"""
        try:
            if self.is_windows:
                result = subprocess.run(
                    ["netstat", "-ano"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                for line in result.stdout.split("\n"):
                    if f":{port}" in line and "LISTENING" in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            return PortStatus(port=port, in_use=True, process=parts[-1])
            else:
                result = subprocess.run(
                    ["lsof", "-i", f":{port}", "-n"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.strip().split("\n")
                    if len(lines) > 1:
                        parts = lines[1].split()
                        if len(parts) > 2:
                            return PortStatus(port=port, in_use=True, process=parts[0])

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()

            return PortStatus(port=port, in_use=result == 0)

        except Exception:
            return PortStatus(port=port, in_use=False)

    def find_available_port(self, start_port: int = 8000, end_port: int = 9000) -> int:
        """查找可用端口"""
        for port in range(start_port, end_port + 1):
            if not self.check_port(port).in_use:
                return port
        return start_port

    def check_directory_permissions(self, path: str) -> dict[str, Any]:
        """检查目录权限"""
        from pathlib import Path

        p = Path(path)
        result = {"readable": False, "writable": False, "exists": p.exists()}

        if result["exists"]:
            result["readable"] = p.is_dir() and list(p.iterdir()) is not None
            try:
                test_file = p / ".write_test"
                test_file.touch()
                test_file.unlink()
                result["writable"] = True
            except Exception:
                result["writable"] = False

        return result

    def check_command_available(self, command: str) -> bool:
        """检查命令是否可用"""
        import shutil

        return shutil.which(command) is not None

    def get_network_info(self) -> dict[str, Any]:
        """获取网络信息"""
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)

            return {
                "hostname": hostname,
                "local_ip": local_ip,
                "can_connect_external": self._check_external_connection(),
            }
        except Exception:
            return {"hostname": "unknown", "local_ip": "unknown", "can_connect_external": False}

    def _check_external_connection(self) -> bool:
        """检查是否能连接外部网络"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect(("8.8.8.8", 53))
            sock.close()
            return True
        except Exception:
            return False

    def get_diagnostics(self) -> dict[str, Any]:
        """获取完整的系统诊断信息"""
        return {
            "system": self.get_system_info().__dict__,
            "network": self.get_network_info(),
            "ports": {
                "8000": self.check_port(8000).__dict__,
                "3000": self.check_port(3000).__dict__,
                "5432": self.check_port(5432).__dict__,
                "6379": self.check_port(6379).__dict__,
            },
            "commands": {
                "python": self.check_command_available("python"),
                "python3": self.check_command_available("python3"),
                "uv": self.check_command_available("uv"),
                "node": self.check_command_available("node"),
                "npm": self.check_command_available("npm"),
                "pnpm": self.check_command_available("pnpm"),
            },
        }

    def format_bytes(self, bytes_value: int) -> str:
        """格式化字节数"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_value < 1024:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024
        return f"{bytes_value:.2f} PB"
