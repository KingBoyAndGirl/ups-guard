"""开机自启管理"""
import logging
import platform
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_REG_NAME = "UpsGuardAgent"            # 旧版注册表项名称（升级时清理）
_WIN_TRAY_REG_NAME = "UpsGuardAgentTray"  # 托盘伴侣自启动注册表项
_WIN_SERVICE_NAME = "UPSGuardAgent"
_LINUX_SERVICE = Path.home() / ".config" / "systemd" / "user" / "ups-guard-agent.service"
_MACOS_PLIST = Path.home() / "Library" / "LaunchAgents" / "com.kingboyandgirl.ups-guard-agent.plist"


def _get_service_bin_path() -> str:
    """获取 Windows 服务的 binPath 字符串（包含 --service 参数）

    路径含空格时自动加引号，确保 SCM 能正确解析。
    """
    exe = sys.executable
    if " " in exe:
        exe = f'"{exe}"'
    if getattr(sys, "frozen", False):
        return f"{exe} --service"
    return f"{exe} -m ups_guard_agent.main --service"


def _get_tray_cmd() -> str:
    """获取托盘伴侣的自启动命令（包含 --tray-only 参数）"""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --tray-only'
    return f'"{sys.executable}" -m ups_guard_agent.main --tray-only'


def install_autostart(agent_name: str = "UPS Guard Agent"):
    """安装开机自启"""
    sys_name = platform.system()
    if sys_name == "Windows":
        _install_windows(agent_name)
    elif sys_name == "Darwin":
        _install_macos(agent_name)
    else:
        _install_linux(agent_name)


def remove_autostart(agent_name: str = "UPS Guard Agent"):
    """移除开机自启"""
    sys_name = platform.system()
    if sys_name == "Windows":
        _remove_windows()
    elif sys_name == "Darwin":
        _remove_macos()
    else:
        _remove_linux()


def is_autostart_enabled() -> bool:
    """检测当前是否已开启开机自启"""
    sys_name = platform.system()
    if sys_name == "Windows":
        return _is_enabled_windows()
    elif sys_name == "Darwin":
        return _MACOS_PLIST.exists()
    else:
        return _LINUX_SERVICE.exists()


# ─────────────────────────── Windows 辅助函数 ────────────────────────────── #

def _is_elevated_windows() -> bool:
    """检测当前进程是否拥有管理员权限"""
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _run_sc(*args: str) -> tuple[int, str]:
    """执行 sc.exe 命令并返回 (返回码, 输出内容)

    sc.exe 使用特殊的参数语法：每个选项格式为 'key= value'（等号后有空格）。
    使用 shell=True 让 cmd.exe 处理命令行，避免 Python subprocess 的自动引号
    与 sc.exe 的非标准参数解析冲突。
    """
    try:
        cmd = "sc.exe " + " ".join(args)
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode, result.stdout + result.stderr
    except Exception as e:
        logger.warning(f"sc.exe 调用失败: {e}")
        return -1, str(e)


def _is_enabled_windows() -> bool:
    """检测 Windows 服务是否存在且配置为自动启动"""
    rc, out = _run_sc("qc", _WIN_SERVICE_NAME)
    return rc == 0 and "AUTO_START" in out


def _install_service_elevated(agent_name: str) -> None:
    """创建或重新配置 Windows 服务（需要管理员权限）"""
    bin_path = _get_service_bin_path()
    rc, _ = _run_sc("qc", _WIN_SERVICE_NAME)
    if rc != 0:
        # 服务不存在 — 创建新服务
        # binPath 整体用双引号包裹，确保 cmd.exe 将其作为单个参数传给 sc.exe
        # 路径内的引号用反斜杠转义，供 CommandLineToArgvW / sc.exe 正确解析
        bin_path_sc = '"' + bin_path.replace('"', r'\"') + '"'
        rc, out = _run_sc(
            "create", _WIN_SERVICE_NAME,
            f"binPath= {bin_path_sc}",
            f'DisplayName= "{agent_name}"',
            "start= auto",
            "obj= LocalSystem",
        )
        if rc != 0:
            logger.error(f"sc.exe create 失败 (rc={rc}): {out.strip()}")
            raise RuntimeError(f"sc.exe create 失败 (rc={rc}): {out.strip()}")
        logger.info(f"Windows 服务 '{_WIN_SERVICE_NAME}' 已创建")
    else:
        # 服务已存在 — 确保为自动启动
        _run_sc("config", _WIN_SERVICE_NAME, "start= auto")
        logger.info(f"Windows 服务 '{_WIN_SERVICE_NAME}' 已重新配置为自动启动")

    # 配置故障恢复策略：10秒后重启，共重试3次，1小时后重置计数
    _run_sc(
        "failure", _WIN_SERVICE_NAME,
        "reset= 3600",
        "actions= restart/10000/restart/10000/restart/10000",
    )
    logger.info("服务故障恢复策略已配置")

    # 立即启动服务（错误码 1056 表示服务已在运行，可忽略）
    rc, out = _run_sc("start", _WIN_SERVICE_NAME)
    if rc not in (0, 1056):
        logger.warning(f"sc.exe start 返回 rc={rc}: {out.strip()}")
    else:
        logger.info(f"Windows 服务 '{_WIN_SERVICE_NAME}' 已启动")

    # 授予普通用户停止/启动服务的权限（类似向日葵的做法）
    # 这样退出托盘时可以不弹 UAC 直接停止服务
    _grant_service_stop_permission()


def _remove_service_elevated() -> None:
    """停止并删除 Windows 服务（需要管理员权限）"""
    _run_sc("stop", _WIN_SERVICE_NAME)
    rc, out = _run_sc("delete", _WIN_SERVICE_NAME)
    if rc != 0:
        logger.warning(f"sc.exe delete 返回 rc={rc}: {out.strip()}")
    else:
        logger.info(f"Windows 服务 '{_WIN_SERVICE_NAME}' 已删除")


def _grant_service_stop_permission() -> None:
    """授予 Authenticated Users 停止/启动服务的权限

    通过 sc.exe sdset 修改服务的安全描述符（DACL），
    添加 AU（Authenticated Users）的 SERVICE_START | SERVICE_STOP 权限。
    需要管理员权限执行（在 --install 提权流程中调用）。

    这样退出托盘时普通用户可以直接停止服务，无需 UAC 弹窗，
    与向日葵等软件的退出体验一致。
    """
    try:
        # 先读取当前 SDDL
        rc, out = _run_sc("sdshow", _WIN_SERVICE_NAME)
        if rc != 0:
            logger.warning(f"读取服务安全描述符失败: {out.strip()}")
            return

        # 提取 SDDL 字符串（sc sdshow 输出可能包含空行）
        sddl = ""
        for line in out.strip().splitlines():
            line = line.strip()
            if line.startswith("D:"):
                sddl = line
                break

        if not sddl:
            logger.warning("无法解析服务安全描述符")
            return

        # 检查是否已有 AU 的权限项，避免重复添加
        # (A;;RPWPDTLOSD;;;AU) = 允许 Authenticated Users 启动/停止/暂停/查询
        au_ace = "(A;;RPWPDTLOSD;;;AU)"
        if au_ace in sddl:
            logger.debug("普通用户已有服务停止权限，无需重复授予")
            return

        # 在 D: 后面插入 AU 的 ACE
        new_sddl = sddl.replace("D:", f"D:{au_ace}", 1)

        # 注意：不能用 _run_sc（shell=True），SDDL 中的括号会被 cmd.exe 错误解析
        # 必须直接调用 sc.exe，不经过 shell
        result = subprocess.run(
            ["sc.exe", "sdset", _WIN_SERVICE_NAME, new_sddl],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            logger.info("已授予普通用户停止/启动服务的权限")
        else:
            logger.warning(f"设置服务安全描述符失败 (rc={result.returncode}): "
                           f"{(result.stdout + result.stderr).strip()}")
    except Exception as e:
        # 非致命错误，只影响退出时是否需要 UAC
        logger.warning(f"授予服务权限失败: {e}")


def _set_tray_registry() -> None:
    """将托盘伴侣注册到 HKCU\\...\\Run，并清理旧版注册表项"""
    try:
        import winreg
        tray_cmd = _get_tray_cmd()
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, _WIN_TRAY_REG_NAME, 0, winreg.REG_SZ, tray_cmd)
        winreg.CloseKey(key)
        logger.info(f"托盘伴侣已注册到 HKCU Run: {tray_cmd}")
        _remove_legacy_registry()
    except Exception as e:
        logger.error(f"设置托盘注册表项失败: {e}")


def _remove_tray_registry() -> None:
    """从 HKCU\\...\\Run 移除托盘伴侣注册表项"""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, _WIN_TRAY_REG_NAME)
            logger.info("托盘伴侣注册表项已移除")
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
        _remove_legacy_registry()
    except Exception as e:
        logger.error(f"移除托盘注册表项失败: {e}")


def _remove_legacy_registry() -> None:
    """移除旧版的单进程 HKCU Run 注册表项（如果还存在）"""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, _REG_NAME)
            logger.info("旧版 HKCU Run 注册表项已移除")
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
    except Exception:
        pass


def _create_start_menu_shortcut() -> None:
    """创建开始菜单快捷方式，使应用可以在 Win10/11 中被固定到开始菜单

    快捷方式放置在当前用户的开始菜单程序目录：
      %APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\UPS Guard Agent.lnk

    指向 exe 本身（不带参数），双击即打开 GUI 配置窗口。
    """
    try:
        import ctypes.wintypes
        # 通过 SHGetFolderPath 获取开始菜单程序目录
        CSIDL_PROGRAMS = 0x0002  # 当前用户的 Start Menu\Programs
        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PROGRAMS, None, 0, buf)
        programs_dir = Path(buf.value)

        if not programs_dir.exists():
            logger.warning(f"开始菜单程序目录不存在: {programs_dir}")
            return

        lnk_path = programs_dir / "UPS Guard Agent.lnk"

        if getattr(sys, "frozen", False):
            target = sys.executable
        else:
            # 源码运行时不创建快捷方式
            logger.debug("非打包环境，跳过创建开始菜单快捷方式")
            return

        working_dir = str(Path(target).parent)

        # 使用 PowerShell 创建 .lnk 文件（无需额外 COM 依赖）
        ps_script = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$sc = $ws.CreateShortcut("{lnk_path}"); '
            f'$sc.TargetPath = "{target}"; '
            f'$sc.WorkingDirectory = "{working_dir}"; '
            f'$sc.Description = "UPS Guard Agent 远程关机客户端"; '
            f'$sc.Save()'
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            logger.info(f"开始菜单快捷方式已创建: {lnk_path}")
        else:
            logger.warning(f"创建开始菜单快捷方式失败: {result.stderr.strip()}")
    except Exception as e:
        # 非关键功能，失败不影响主流程
        logger.warning(f"创建开始菜单快捷方式失败: {e}")


def _remove_start_menu_shortcut() -> None:
    """移除开始菜单快捷方式"""
    try:
        import ctypes.wintypes
        CSIDL_PROGRAMS = 0x0002
        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PROGRAMS, None, 0, buf)
        lnk_path = Path(buf.value) / "UPS Guard Agent.lnk"
        if lnk_path.exists():
            lnk_path.unlink()
            logger.info(f"开始菜单快捷方式已移除: {lnk_path}")
    except Exception as e:
        logger.warning(f"移除开始菜单快捷方式失败: {e}")


def _request_uac(verb: str) -> None:
    """通过 ShellExecuteW (runas) 请求 UAC 提权重新启动程序

    提权后的进程异步运行，调用方立即返回。
    使用 SW_HIDE(0) 隐藏提权进程窗口，避免干扰其他应用。
    """
    import ctypes
    if getattr(sys, "frozen", False):
        exe = sys.executable
        params = verb
    else:
        exe = sys.executable
        params = f"-m ups_guard_agent.main {verb}"
    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 0)
    if result <= 32:
        raise RuntimeError(f"ShellExecuteW(runas) 失败，错误码 {result}")
    logger.info(f"已请求 UAC 提权: '{verb}'")


def _install_windows(agent_name: str) -> None:
    """安装 Windows 服务 + 注册托盘自启动 + 创建开始菜单快捷方式

    未提权时通过 UAC 弹窗委派给提权进程执行。
    已提权时（如通过 --install 启动）直接执行。
    """
    if _is_elevated_windows():
        _install_service_elevated(agent_name)
        _set_tray_registry()
        _create_start_menu_shortcut()
    else:
        _request_uac("--install")
        logger.info("服务安装已委派给提权进程")


def _remove_windows() -> None:
    """停止/删除服务 + 移除托盘注册表项 + 移除开始菜单快捷方式

    未提权时通过 UAC 弹窗请求权限。
    """
    if _is_elevated_windows():
        _remove_service_elevated()
        _remove_tray_registry()
        _remove_start_menu_shortcut()
    else:
        _request_uac("--uninstall")
        logger.info("服务卸载已委派给提权进程")


# ─────────────────────────── Linux 辅助函数 ──────────────────────────────── #

def _install_linux(agent_name: str):
    """安装 Linux systemd 用户服务"""
    service_dir = _LINUX_SERVICE.parent
    service_dir.mkdir(parents=True, exist_ok=True)
    if getattr(sys, 'frozen', False):
        exec_start = sys.executable
    else:
        exec_start = f"{sys.executable} -m ups_guard_agent.main"
    content = f"""[Unit]
Description={agent_name}
After=network.target

[Service]
ExecStart={exec_start}
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
"""
    _LINUX_SERVICE.write_text(content)
    logger.info(f"Autostart installed: {_LINUX_SERVICE}")
    logger.info("Run: systemctl --user enable ups-guard-agent && systemctl --user start ups-guard-agent")


def _remove_linux():
    """移除 Linux systemd 用户服务"""
    if _LINUX_SERVICE.exists():
        _LINUX_SERVICE.unlink()
        logger.info("Autostart removed (systemd user service)")


# ─────────────────────────── macOS 辅助函数 ──────────────────────────────── #

def _install_macos(agent_name: str):
    """安装 macOS LaunchAgent"""
    plist_dir = _MACOS_PLIST.parent
    plist_dir.mkdir(parents=True, exist_ok=True)
    if getattr(sys, 'frozen', False):
        args = [sys.executable]
    else:
        args = [sys.executable, "-m", "ups_guard_agent.main"]
    program_args = "\n".join(f"        <string>{a}</string>" for a in args)
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.kingboyandgirl.ups-guard-agent</string>
    <key>ProgramArguments</key>
    <array>
{program_args}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
"""
    _MACOS_PLIST.write_text(content)
    logger.info(f"Autostart installed: {_MACOS_PLIST}")


def _remove_macos():
    """移除 macOS LaunchAgent"""
    if _MACOS_PLIST.exists():
        _MACOS_PLIST.unlink()
        logger.info("开机自启已移除（macOS LaunchAgent）")
