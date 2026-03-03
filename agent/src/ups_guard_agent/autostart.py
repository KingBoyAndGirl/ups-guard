"""开机自启管理"""
import logging
import platform
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_REG_NAME = "UpsGuardAgent"
_LINUX_SERVICE = Path.home() / ".config" / "systemd" / "user" / "ups-guard-agent.service"
_MACOS_PLIST = Path.home() / "Library" / "LaunchAgents" / "com.kingboyandgirl.ups-guard-agent.plist"


def _get_exec_command() -> str:
    """返回适合当前运行方式的启动命令（frozen exe 或源码运行）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的 exe，直接运行自身
        return f'"{sys.executable}"'
    return f'"{sys.executable}" -m ups_guard_agent.main'


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


def _is_enabled_windows() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _REG_KEY,
            0,
            winreg.KEY_READ,
        )
        winreg.QueryValueEx(key, _REG_NAME)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def _install_windows(agent_name: str):
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _REG_KEY,
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, _REG_NAME, 0, winreg.REG_SZ, _get_exec_command())
        winreg.CloseKey(key)
        logger.info("Autostart installed (Windows registry)")
    except Exception as e:
        logger.error(f"Failed to install autostart on Windows: {e}")


def _remove_windows():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _REG_KEY,
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.DeleteValue(key, _REG_NAME)
        winreg.CloseKey(key)
        logger.info("Autostart removed (Windows registry)")
    except Exception as e:
        logger.error(f"Failed to remove autostart on Windows: {e}")


def _install_linux(agent_name: str):
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
    if _LINUX_SERVICE.exists():
        _LINUX_SERVICE.unlink()
        logger.info("Autostart removed (systemd user service)")


def _install_macos(agent_name: str):
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
    if _MACOS_PLIST.exists():
        _MACOS_PLIST.unlink()
        logger.info("Autostart removed (macOS LaunchAgent)")
