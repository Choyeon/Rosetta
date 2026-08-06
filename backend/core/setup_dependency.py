"""
依赖管理服务

提供智能依赖检测和安装功能：
- Python 环境检测
- uv 包管理器检测
- Node.js 环境检测
- pnpm 包管理器检测
- 自动安装支持
- 版本检查和兼容性验证
- 实时流式日志输出（支持 WebSocket）
"""

import os
import platform
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .setup_system import SystemService


class InstallStatus(Enum):
    """安装状态"""

    PENDING = "pending"
    INSTALLING = "installing"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class DependencyStatus(Enum):
    """依赖状态"""

    MISSING = "missing"
    OUTDATED = "outdated"
    INSTALLED = "installed"
    COMPATIBLE = "compatible"


@dataclass
class DependencyInfo:
    """依赖信息"""

    name: str
    status: DependencyStatus
    current_version: str | None = None
    required_version: str | None = None
    message: str = ""
    install_command: str | None = None


@dataclass
class InstallResult:
    """安装结果"""

    name: str
    status: InstallStatus
    message: str
    output: str | None = None
    duration: float | None = None


class DependencyService:
    """依赖管理服务"""

    MIN_PYTHON_VERSION = (3, 10)
    MIN_NODEJS_VERSION = 18

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path.cwd()
        self.system_service = SystemService()
        self.is_windows = platform.system() == "Windows"
        self.is_linux = platform.system() == "Linux"
        self.is_macos = platform.system() == "Darwin"
        self._progress_callback: Callable[[str, str, str], None] | None = None
        self._log_callback: Callable[[str], None] | None = None
        self._install_logs: list[dict] = []

    def set_progress_callback(self, callback: Callable[[str, str, str], None]):
        """设置进度回调函数"""
        self._progress_callback = callback

    def set_log_callback(self, callback: Callable[[str], None]):
        """设置日志回调函数（用于实时流式输出）"""
        self._log_callback = callback

    def _report_progress(self, name: str, status: str, message: str):
        """报告安装进度"""
        self._install_logs.append(
            {"name": name, "status": status, "message": message, "timestamp": None}
        )
        if self._progress_callback:
            self._progress_callback(name, status, message)

    def _log(self, message: str):
        """输出日志（支持流式）"""
        if self._log_callback:
            self._log_callback(message)

    def _get_install_logs(self) -> list[dict]:
        """获取安装日志"""
        return self._install_logs

    def _refresh_path(self) -> None:
        """刷新 PATH 环境变量（安装新工具后调用）"""
        try:
            import sysconfig

            scripts_dir = sysconfig.get_path("scripts")
            if scripts_dir and Path(scripts_dir).exists():
                sep = ";" if self.is_windows else ":"
                if scripts_dir not in os.environ.get("PATH", ""):
                    os.environ["PATH"] = scripts_dir + sep + os.environ.get("PATH", "")
        except Exception:
            pass

        if self.is_windows:
            try:
                import winreg

                with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                ) as key:
                    system_path, _ = winreg.QueryValueEx(key, "PATH")
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                    user_path, _ = winreg.QueryValueEx(key, "PATH")
                current = os.environ.get("PATH", "")
                os.environ["PATH"] = f"{current};{user_path};{system_path}"
            except Exception:
                pass

            common_paths = [
                r"C:\Program Files\nodejs",
                os.path.expanduser(r"~\AppData\Roaming\npm"),
                os.path.expanduser(r"~\AppData\Roaming\Python\Python310\Scripts"),
                os.path.expanduser(r"~\AppData\Roaming\Python\Python311\Scripts"),
                os.path.expanduser(r"~\AppData\Roaming\Python\Python312\Scripts"),
            ]
            sep = ";"
            current = os.environ.get("PATH", "")
            for p in common_paths:
                if Path(p).exists() and p not in current:
                    os.environ["PATH"] = p + sep + current
                    current = os.environ["PATH"]

    def _find_executable(self, name: str) -> str | None:
        """查找可执行文件路径（支持回退搜索）"""
        path = shutil.which(name)
        if path:
            return path

        if self.is_windows:
            try:
                import sysconfig

                scripts_dir = sysconfig.get_path("scripts")
                if scripts_dir:
                    exe_path = Path(scripts_dir) / f"{name}.exe"
                    if exe_path.exists():
                        return str(exe_path)
            except Exception:
                pass

            npm_global = os.path.expanduser(r"~\AppData\Roaming\npm")
            exe_path = Path(npm_global) / f"{name}.cmd"
            if exe_path.exists():
                return str(exe_path)

            nodejs_dir = r"C:\Program Files\nodejs"
            exe_path = Path(nodejs_dir) / f"{name}.exe"
            if exe_path.exists():
                return str(exe_path)
        else:
            common_dirs = [
                "/usr/local/bin",
                "/usr/bin",
                os.path.expanduser("~/.local/bin"),
            ]
            for d in common_dirs:
                exe_path = Path(d) / name
                if exe_path.exists():
                    return str(exe_path)

        return None

    def _run_command_streaming(
        self,
        cmd: list[str] | str,
        cwd: str | None = None,
        timeout: int = 600,
        shell: bool = False,
    ) -> int:
        """流式执行命令并实时输出日志"""
        self._log(f"[CMD] {' '.join(cmd) if isinstance(cmd, list) else cmd}")

        try:
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=shell,
                bufsize=1,
                universal_newlines=True,
            )

            start_time = time.time()
            while True:
                if time.time() - start_time > timeout:
                    process.terminate()
                    self._log(f"[TIMEOUT] Command timed out after {timeout}s")
                    return 1

                line = process.stdout.readline()
                if not line:
                    if process.poll() is not None:
                        break
                    time.sleep(0.1)
                    continue

                line = line.rstrip()
                if line:
                    self._log(line)

            return process.returncode
        except Exception as e:
            self._log(f"[ERROR] {str(e)}")
            return 1

    def check_python(self) -> DependencyInfo:
        """检查 Python 环境"""
        import sys

        version_info = sys.version_info
        current_version = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
        is_compatible = version_info >= self.MIN_PYTHON_VERSION

        return DependencyInfo(
            name="Python",
            status=DependencyStatus.COMPATIBLE if is_compatible else DependencyStatus.OUTDATED,
            current_version=current_version,
            required_version=".".join(map(str, self.MIN_PYTHON_VERSION)),
            message=f"Python {current_version} {'已安装' if is_compatible else '版本过低，需要 ' + '.'.join(map(str, self.MIN_PYTHON_VERSION)) + '+'}",
        )

    def _find_system_python(self) -> str | None:
        """查找系统 Python（跳过虚拟环境）"""
        candidates = ["py", "python", "python3"]
        for cmd in candidates:
            try:
                path = shutil.which(cmd)
                if path:
                    return path
            except Exception:
                pass
        return None

    def _check_uv_with_python(self, python_exe: str) -> tuple[str, str] | None:
        """用指定 Python 检查 uv"""
        try:
            result = subprocess.run(
                [python_exe, "-m", "uv", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                version = parts[1] if len(parts) >= 2 else parts[-1]
                return version, python_exe
        except Exception:
            pass
        return None

    def check_uv(self) -> DependencyInfo:
        """检查 uv 包管理器"""
        self._refresh_path()
        uv_path = self._find_executable("uv")

        if uv_path:
            try:
                result = subprocess.run(
                    [uv_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    parts = result.stdout.strip().split()
                    version = parts[1] if len(parts) >= 2 else parts[-1]
                    return DependencyInfo(
                        name="uv",
                        status=DependencyStatus.INSTALLED,
                        current_version=version,
                        message=f"uv {version} 已安装",
                    )
            except Exception:
                pass

        found = self._check_uv_with_python(sys.executable)
        if found:
            version, _ = found
            return DependencyInfo(
                name="uv",
                status=DependencyStatus.INSTALLED,
                current_version=version,
                message=f"uv {version} 已安装 (python -m uv)",
            )

        base_prefix = getattr(sys, "base_prefix", None)
        if base_prefix and base_prefix != sys.prefix:
            ext = ".exe" if self.is_windows else ""
            base_python = str(Path(base_prefix) / f"python{ext}")
            if Path(base_python).exists():
                found = self._check_uv_with_python(base_python)
                if found:
                    version, _ = found
                    return DependencyInfo(
                        name="uv",
                        status=DependencyStatus.INSTALLED,
                        current_version=version,
                        message=f"uv {version} 已安装 (系统 Python)",
                    )

        system_python = self._find_system_python()
        if system_python:
            found = self._check_uv_with_python(system_python)
            if found:
                version, _ = found
                return DependencyInfo(
                    name="uv",
                    status=DependencyStatus.INSTALLED,
                    current_version=version,
                    message=f"uv {version} 已安装 (系统 Python)",
                )

        for extra_python in ["py", "python", "python3"]:
            ppath = shutil.which(extra_python)
            if ppath and ppath != sys.executable:
                found = self._check_uv_with_python(ppath)
                if found:
                    version, _ = found
                    return DependencyInfo(
                        name="uv",
                        status=DependencyStatus.INSTALLED,
                        current_version=version,
                        message=f"uv {version} 已安装 (系统 Python)",
                    )

        return DependencyInfo(
            name="uv",
            status=DependencyStatus.MISSING,
            message="uv 未安装",
            install_command=self._get_uv_install_command(),
        )

    def check_nodejs(self) -> DependencyInfo:
        """检查 Node.js 环境"""
        self._refresh_path()
        node_path = self._find_executable("node")

        if node_path:
            try:
                result = subprocess.run(
                    [node_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    version_str = result.stdout.strip().lstrip("v")
                    major_version = int(version_str.split(".")[0]) if version_str else 0

                    is_compatible = major_version >= self.MIN_NODEJS_VERSION

                    return DependencyInfo(
                        name="Node.js",
                        status=DependencyStatus.COMPATIBLE
                        if is_compatible
                        else DependencyStatus.OUTDATED,
                        current_version=version_str,
                        required_version=f"{self.MIN_NODEJS_VERSION}.0.0",
                        message=f"Node.js {version_str} {'已安装' if is_compatible else f'版本过低，需要 {self.MIN_NODEJS_VERSION}+'}",
                        install_command=self._get_nodejs_install_command(),
                    )
            except Exception:
                pass

        return DependencyInfo(
            name="Node.js",
            status=DependencyStatus.MISSING,
            message="Node.js 未安装",
            install_command=self._get_nodejs_install_command(),
        )

    def check_pnpm(self) -> DependencyInfo:
        """检查 pnpm 包管理器"""
        self._refresh_path()
        pnpm_path = self._find_executable("pnpm")

        if pnpm_path:
            try:
                result = subprocess.run(
                    [pnpm_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    version = result.stdout.strip()
                    return DependencyInfo(
                        name="pnpm",
                        status=DependencyStatus.INSTALLED,
                        current_version=version,
                        message=f"pnpm {version} 已安装",
                    )
            except Exception:
                pass

        return DependencyInfo(
            name="pnpm",
            status=DependencyStatus.MISSING,
            message="pnpm 未安装",
            install_command="npm install -g pnpm",
        )

    def check_postgresql(self) -> DependencyInfo:
        """检查 PostgreSQL 客户端"""
        self._refresh_path()
        psql_path = self._find_executable("psql")

        if psql_path:
            try:
                result = subprocess.run(
                    [psql_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    version = result.stdout.strip().split()[-1]
                    return DependencyInfo(
                        name="PostgreSQL",
                        status=DependencyStatus.INSTALLED,
                        current_version=version,
                        message=f"PostgreSQL 客户端 {version} 已安装",
                    )
            except Exception:
                pass

        return DependencyInfo(
            name="PostgreSQL",
            status=DependencyStatus.MISSING,
            message="PostgreSQL 客户端未安装（可选）",
            install_command="brew install postgresql"
            if self.is_macos
            else "sudo apt install postgresql-client",
        )

    def check_redis(self) -> DependencyInfo:
        """检查 Redis 客户端"""
        self._refresh_path()
        redis_cli_path = self._find_executable("redis-cli")

        if redis_cli_path:
            try:
                result = subprocess.run(
                    [redis_cli_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    version = result.stdout.strip().split()[-1]
                    return DependencyInfo(
                        name="Redis",
                        status=DependencyStatus.INSTALLED,
                        current_version=version,
                        message=f"Redis 客户端 {version} 已安装",
                    )
            except Exception:
                pass

        return DependencyInfo(
            name="Redis",
            status=DependencyStatus.MISSING,
            message="Redis 客户端未安装（可选）",
            install_command="brew install redis"
            if self.is_macos
            else "sudo apt install redis-tools",
        )

    def check_all(self) -> dict[str, DependencyInfo]:
        """检查所有依赖"""
        return {
            "python": self.check_python(),
            "uv": self.check_uv(),
            "nodejs": self.check_nodejs(),
            "pnpm": self.check_pnpm(),
            "postgresql": self.check_postgresql(),
            "redis": self.check_redis(),
        }

    def get_missing_dependencies(self) -> list[DependencyInfo]:
        """获取缺失的依赖列表"""
        all_deps = self.check_all()
        return [
            dep
            for dep in all_deps.values()
            if dep.status in (DependencyStatus.MISSING, DependencyStatus.OUTDATED)
        ]

    def is_ready(self) -> bool:
        """检查是否所有必需依赖都已就绪"""
        python_dep = self.check_python()
        if python_dep.status == DependencyStatus.OUTDATED:
            return False
        return len(self.get_missing_dependencies()) == 0

    def get_required_dependencies(self) -> list[DependencyInfo]:
        """获取必需的依赖列表"""
        all_deps = self.check_all()
        required = ["python", "uv"]
        return [all_deps[name] for name in required if name in all_deps]

    def get_optional_dependencies(self) -> list[DependencyInfo]:
        """获取可选的依赖列表"""
        all_deps = self.check_all()
        optional = ["nodejs", "pnpm", "postgresql", "redis"]
        return [all_deps[name] for name in optional if name in all_deps]

    def _get_uv_install_command(self) -> str:
        """获取 uv 安装命令"""
        if self.is_windows:
            return "pip install uv"
        return "pip install uv"

    def _get_nodejs_install_command(self) -> str:
        """获取 Node.js 安装命令"""
        if self.is_windows:
            return "winget install OpenJS.NodeJS.LTS"
        elif self.is_linux:
            return "curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - && sudo apt-get install -y nodejs"
        elif self.is_macos:
            return "brew install node"
        return "访问 https://nodejs.org 下载安装"

    def install_uv(self) -> InstallResult:
        """安装 uv 包管理器"""
        start_time = time.time()
        self._report_progress("uv", "installing", "正在安装 uv...")
        self._log("===== 安装 uv 包管理器 =====")

        try:
            if not self.is_windows:
                self._log("尝试使用官方安装脚本...")
                code = self._run_command_streaming(
                    "curl -LsSf https://astral.sh/uv/install.sh | sh",
                    shell=True,
                    timeout=120,
                )
                if code == 0:
                    self._refresh_path()
                    if self._find_executable("uv"):
                        duration = time.time() - start_time
                        self._report_progress("uv", "success", "uv 安装成功")
                        self._log("[OK] uv 安装成功")
                        return InstallResult(
                            name="uv",
                            status=InstallStatus.SUCCESS,
                            message="uv 安装成功",
                            duration=duration,
                        )
                self._log("官方脚本失败，尝试使用 pip 安装...")

            python_exe = sys.executable
            code = self._run_command_streaming(
                [python_exe, "-m", "pip", "install", "uv"],
                timeout=120,
            )

            duration = time.time() - start_time

            if code == 0:
                self._refresh_path()
                self._report_progress("uv", "success", "uv 安装成功")
                self._log("[OK] uv 安装成功")
                return InstallResult(
                    name="uv",
                    status=InstallStatus.SUCCESS,
                    message="uv 安装成功",
                    duration=duration,
                )
            else:
                self._report_progress("uv", "failed", "uv 安装失败")
                self._log("[FAIL] uv 安装失败")
                return InstallResult(
                    name="uv",
                    status=InstallStatus.FAILED,
                    message="uv 安装失败，请手动安装",
                    duration=duration,
                )
        except Exception as e:
            duration = time.time() - start_time
            self._report_progress("uv", "failed", f"uv 安装异常: {str(e)}")
            self._log(f"[ERROR] {str(e)}")
            return InstallResult(
                name="uv",
                status=InstallStatus.FAILED,
                message=f"安装异常: {str(e)}",
                duration=duration,
            )

    def install_nodejs(self) -> InstallResult:
        """安装 Node.js"""
        start_time = time.time()
        self._report_progress("nodejs", "installing", "检查 Node.js 安装方式...")
        self._log("===== 安装 Node.js =====")

        if self.is_windows:
            return self._install_nodejs_windows(start_time)
        elif self.is_linux:
            return self._install_nodejs_linux(start_time)
        elif self.is_macos:
            return self._install_nodejs_macos(start_time)

        return InstallResult(
            name="Node.js",
            status=InstallStatus.FAILED,
            message="请手动安装 Node.js",
        )

    def _install_nodejs_windows(self, start_time: float) -> InstallResult:
        """Windows 安装 Node.js"""
        winget_path = self._find_executable("winget")
        if winget_path:
            self._report_progress("nodejs", "installing", "使用 winget 安装 Node.js...")
            self._log("使用 winget 安装 Node.js LTS...")
            code = self._run_command_streaming(
                [
                    "winget",
                    "install",
                    "OpenJS.NodeJS.LTS",
                    "--accept-source-agreements",
                    "--accept-package-agreements",
                ],
                timeout=600,
            )
            duration = time.time() - start_time
            if code == 0:
                self._refresh_path()
                time.sleep(2)
                self._refresh_path()
                if self._find_executable("node"):
                    self._report_progress("nodejs", "success", "Node.js 安装成功")
                    self._log("[OK] Node.js 安装成功")
                    return InstallResult(
                        name="Node.js",
                        status=InstallStatus.SUCCESS,
                        message="Node.js 安装成功",
                        duration=duration,
                    )
                self._log("[WARN] Node.js 已安装但未在 PATH 中，请重启终端")
                return InstallResult(
                    name="Node.js",
                    status=InstallStatus.SUCCESS,
                    message="Node.js 安装成功，请重启终端后继续",
                    duration=duration,
                )
            self._log("[FAIL] winget 安装失败")

        self._log("尝试使用 choco 安装...")
        choco_path = self._find_executable("choco")
        if choco_path:
            code = self._run_command_streaming(
                ["choco", "install", "nodejs-lts", "-y"],
                timeout=600,
            )
            duration = time.time() - start_time
            if code == 0:
                self._refresh_path()
                if self._find_executable("node"):
                    self._report_progress("nodejs", "success", "Node.js 安装成功")
                    self._log("[OK] Node.js 安装成功")
                    return InstallResult(
                        name="Node.js",
                        status=InstallStatus.SUCCESS,
                        message="Node.js 安装成功",
                        duration=duration,
                    )

        duration = time.time() - start_time
        self._report_progress("nodejs", "failed", "请手动安装 Node.js")
        self._log("[FAIL] 请访问 https://nodejs.org 下载安装 Node.js LTS 版本")
        return InstallResult(
            name="Node.js",
            status=InstallStatus.FAILED,
            message="请访问 https://nodejs.org 下载安装 Node.js LTS 版本",
            duration=duration,
        )

    def _install_nodejs_linux(self, start_time: float) -> InstallResult:
        """Linux 安装 Node.js"""
        try:
            self._report_progress("nodejs", "installing", "使用 NodeSource 安装 Node.js...")
            self._log("检测 Linux 发行版...")
            code, out, _ = subprocess.run(
                "cat /etc/os-release", shell=True, capture_output=True, text=True, timeout=10
            )
            is_debian = "debian" in out.lower() or "ubuntu" in out.lower()
            is_rhel = "rhel" in out.lower() or "fedora" in out.lower() or "centos" in out.lower()

            if is_debian:
                self._log("检测到 Debian/Ubuntu 系统，使用 NodeSource...")
                commands = [
                    "curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -",
                    "sudo apt-get install -y nodejs",
                ]
            elif is_rhel:
                self._log("检测到 RHEL/Fedora/CentOS 系统，使用 NodeSource...")
                commands = [
                    "curl -fsSL https://rpm.nodesource.com/setup_lts.x | sudo bash -",
                    "sudo yum install -y nodejs",
                ]
            else:
                self._log("使用 snap 安装...")
                commands = ["sudo snap install node --classic"]

            for cmd in commands:
                self._log(f"执行命令: {cmd[:50]}...")
                code = self._run_command_streaming(cmd, shell=True, timeout=300)
                if code != 0:
                    duration = time.time() - start_time
                    self._report_progress("nodejs", "failed", "Node.js 安装失败")
                    self._log("[FAIL] Node.js 安装失败")
                    return InstallResult(
                        name="Node.js",
                        status=InstallStatus.FAILED,
                        message="安装失败，请手动安装",
                        duration=duration,
                    )

            self._refresh_path()
            duration = time.time() - start_time
            self._report_progress("nodejs", "success", "Node.js 安装成功")
            self._log("[OK] Node.js 安装成功")
            return InstallResult(
                name="Node.js",
                status=InstallStatus.SUCCESS,
                message="Node.js 安装成功",
                duration=duration,
            )
        except Exception as e:
            duration = time.time() - start_time
            self._report_progress("nodejs", "failed", f"Node.js 安装异常: {str(e)}")
            self._log(f"[ERROR] {str(e)}")
            return InstallResult(
                name="Node.js",
                status=InstallStatus.FAILED,
                message=f"安装异常: {str(e)}",
                duration=duration,
            )

    def _install_nodejs_macos(self, start_time: float) -> InstallResult:
        """macOS 安装 Node.js"""
        brew_path = self._find_executable("brew")
        if brew_path:
            self._report_progress("nodejs", "installing", "使用 Homebrew 安装 Node.js...")
            self._log("使用 Homebrew 安装 Node.js...")
            code = self._run_command_streaming(["brew", "install", "node"], timeout=300)
            duration = time.time() - start_time

            if code == 0:
                self._refresh_path()
                self._report_progress("nodejs", "success", "Node.js 安装成功")
                self._log("[OK] Node.js 安装成功")
                return InstallResult(
                    name="Node.js",
                    status=InstallStatus.SUCCESS,
                    message="Node.js 安装成功",
                    duration=duration,
                )
            else:
                self._report_progress("nodejs", "failed", "Node.js 安装失败")
                self._log("[FAIL] Homebrew 安装失败")

        duration = time.time() - start_time
        self._report_progress("nodejs", "failed", "请手动安装 Node.js")
        self._log("[FAIL] 请访问 https://nodejs.org 下载安装 Node.js LTS 版本")
        return InstallResult(
            name="Node.js",
            status=InstallStatus.FAILED,
            message="请访问 https://nodejs.org 下载安装 Node.js LTS 版本",
            duration=duration,
        )

    def install_pnpm(self) -> InstallResult:
        """安装 pnpm"""
        start_time = time.time()
        self._report_progress("pnpm", "installing", "正在安装 pnpm...")
        self._log("===== 安装 pnpm =====")

        npm_path = self._find_executable("npm")
        if not npm_path:
            duration = time.time() - start_time
            self._report_progress("pnpm", "failed", "npm 未安装，无法安装 pnpm")
            self._log("[FAIL] npm 未安装，请先安装 Node.js")
            return InstallResult(
                name="pnpm",
                status=InstallStatus.FAILED,
                message="npm 未安装，请先安装 Node.js",
                duration=duration,
            )

        self._log("使用 npm 安装 pnpm...")
        code = self._run_command_streaming(
            [npm_path, "install", "-g", "pnpm"],
            timeout=120,
        )
        duration = time.time() - start_time

        if code == 0:
            self._refresh_path()
            self._report_progress("pnpm", "success", "pnpm 安装成功")
            self._log("[OK] pnpm 安装成功")
            return InstallResult(
                name="pnpm",
                status=InstallStatus.SUCCESS,
                message="pnpm 安装成功",
                duration=duration,
            )
        else:
            self._report_progress("pnpm", "failed", "pnpm 安装失败")
            self._log("[FAIL] pnpm 安装失败")
            return InstallResult(
                name="pnpm",
                status=InstallStatus.FAILED,
                message="pnpm 安装失败，请手动安装",
                duration=duration,
            )

    def install_backend_deps(self) -> InstallResult:
        """安装后端 Python 依赖"""
        start_time = time.time()
        self._report_progress("backend", "installing", "正在安装后端依赖...")
        self._log("===== 安装后端依赖 =====")

        uv_path = self._find_executable("uv")
        if not uv_path:
            duration = time.time() - start_time
            self._report_progress("backend", "failed", "uv 未安装")
            self._log("[FAIL] uv 未安装，请先安装 uv")
            return InstallResult(
                name="backend",
                status=InstallStatus.FAILED,
                message="uv 未安装，请先安装 uv",
                duration=duration,
            )

        pyproject_file = self.base_dir / "pyproject.toml"
        if not pyproject_file.exists():
            duration = time.time() - start_time
            self._report_progress("backend", "failed", "pyproject.toml 不存在")
            self._log("[FAIL] pyproject.toml 不存在")
            return InstallResult(
                name="backend",
                status=InstallStatus.FAILED,
                message="pyproject.toml 不存在",
                duration=duration,
            )

        self._log("使用 uv sync 安装后端依赖...")
        code = self._run_command_streaming(
            [uv_path, "sync", "--frozen"],
            cwd=str(self.base_dir),
            timeout=600,
        )
        duration = time.time() - start_time

        if code == 0:
            self._report_progress("backend", "success", "后端依赖安装成功")
            self._log("[OK] 后端依赖安装成功")
            return InstallResult(
                name="backend",
                status=InstallStatus.SUCCESS,
                message="后端依赖安装成功",
                duration=duration,
            )
        else:
            self._report_progress("backend", "failed", "后端依赖安装失败")
            self._log("[FAIL] 后端依赖安装失败")
            return InstallResult(
                name="backend",
                status=InstallStatus.FAILED,
                message="后端依赖安装失败，请手动安装",
                duration=duration,
            )

    def install_frontend_deps(self) -> InstallResult:
        """安装前端 npm 依赖"""
        start_time = time.time()
        self._report_progress("frontend", "installing", "正在安装前端依赖...")
        self._log("===== 安装前端依赖 =====")

        pnpm_path = self._find_executable("pnpm")
        if not pnpm_path:
            duration = time.time() - start_time
            self._report_progress("frontend", "failed", "pnpm 未安装")
            self._log("[FAIL] pnpm 未安装，请先安装 pnpm")
            return InstallResult(
                name="frontend",
                status=InstallStatus.FAILED,
                message="pnpm 未安装，请先安装 pnpm",
                duration=duration,
            )

        frontend_dir = self.base_dir / "frontend"
        if not frontend_dir.exists():
            duration = time.time() - start_time
            self._report_progress("frontend", "failed", "frontend 目录不存在")
            self._log("[FAIL] frontend 目录不存在")
            return InstallResult(
                name="frontend",
                status=InstallStatus.FAILED,
                message="frontend 目录不存在",
                duration=duration,
            )

        self._log("使用 pnpm 安装前端依赖...")
        code = self._run_command_streaming(
            [pnpm_path, "install"],
            cwd=str(frontend_dir),
            timeout=600,
        )
        duration = time.time() - start_time

        if code == 0:
            self._report_progress("frontend", "success", "前端依赖安装成功")
            self._log("[OK] 前端依赖安装成功")
            return InstallResult(
                name="frontend",
                status=InstallStatus.SUCCESS,
                message="前端依赖安装成功",
                duration=duration,
            )
        else:
            self._report_progress("frontend", "failed", "前端依赖安装失败")
            self._log("[FAIL] 前端依赖安装失败")
            return InstallResult(
                name="frontend",
                status=InstallStatus.FAILED,
                message="前端依赖安装失败，请手动安装",
                duration=duration,
            )

    def install_missing(self) -> dict[str, InstallResult]:
        """安装缺失的依赖"""
        results: dict[str, InstallResult] = {}
        deps = self.check_all()

        if deps["uv"].status == DependencyStatus.MISSING:
            results["uv"] = self.install_uv()

        if deps["nodejs"].status == DependencyStatus.MISSING:
            results["nodejs"] = self.install_nodejs()

        if deps["pnpm"].status == DependencyStatus.MISSING:
            results["pnpm"] = self.install_pnpm()

        return results

    def install_all(self) -> dict[str, InstallResult]:
        """安装所有依赖（包括后端和前端）"""
        results = self.install_missing()

        deps = self.check_all()
        if deps["uv"].status == DependencyStatus.INSTALLED:
            results["backend"] = self.install_backend_deps()

        if deps["pnpm"].status == DependencyStatus.INSTALLED:
            results["frontend"] = self.install_frontend_deps()

        return results

    def get_install_summary(self, results: dict[str, InstallResult]) -> dict:
        """获取安装摘要"""
        success_count = sum(1 for r in results.values() if r.status == InstallStatus.SUCCESS)
        failed_count = sum(1 for r in results.values() if r.status == InstallStatus.FAILED)
        skipped_count = sum(1 for r in results.values() if r.status == InstallStatus.SKIPPED)

        return {
            "total": len(results),
            "success": success_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "all_success": failed_count == 0,
            "results": {
                name: {
                    "status": r.status.value,
                    "message": r.message,
                    "duration": r.duration,
                }
                for name, r in results.items()
            },
            "logs": self._get_install_logs(),
        }

    def export_status(self) -> dict:
        """导出依赖状态"""
        deps = self.check_all()
        return {
            "required": {
                name: {
                    "status": dep.status.value,
                    "current_version": dep.current_version,
                    "required_version": dep.required_version,
                    "message": dep.message,
                    "install_command": dep.install_command,
                }
                for name, dep in deps.items()
                if name in ("python", "uv")
            },
            "optional": {
                name: {
                    "status": dep.status.value,
                    "current_version": dep.current_version,
                    "message": dep.message,
                    "install_command": dep.install_command,
                }
                for name, dep in deps.items()
                if name not in ("python", "uv")
            },
            "is_ready": self.is_ready(),
        }
