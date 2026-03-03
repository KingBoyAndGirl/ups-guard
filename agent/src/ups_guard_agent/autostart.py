"""开机自启管理"""
import logging
import platform
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


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


def _install_windows(agent_name: str):
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        exe = sys.executable
        winreg.SetValueEx(key, "UpsGuardAgent", 0, winreg.REG_SZ, f'"{exe}" -m ups_guard_agent.main')
        winreg.CloseKey(key)
        logger.info("Autostart installed (Windows registry)")
    except Exception as e:
        logger.error(f"Failed to install autostart on Windows: {e}")


def _remove_windows():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.DeleteValue(key, "UpsGuardAgent")
        winreg.CloseKey(key)
        logger.info("Autostart removed (Windows registry)")
    except Exception as e:
        logger.error(f"Failed to remove autostart on Windows: {e}")


def _install_linux(agent_name: str):
    service_dir = Path.home() / ".config" / "systemd" / "user"
    service_dir.mkdir(parents=True, exist_ok=True)
    service_file = service_dir / "ups-guard-agent.service"
    exe = sys.executable
    content = f"""[Unit]
Description={agent_name}
After=network.target

[Service]
ExecStart={exe} -m ups_guard_agent.main
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
"""
    service_file.write_text(content)
    logger.info(f"Autostart installed: {service_file}")
    logger.info("Run: systemctl --user enable ups-guard-agent && systemctl --user start ups-guard-agent")


def _remove_linux():
    service_file = Path.home() / ".config" / "systemd" / "user" / "ups-guard-agent.service"
    if service_file.exists():
        service_file.unlink()
        logger.info("Autostart removed (systemd user service)")


def _install_macos(agent_name: str):
    plist_dir = Path.home() / "Library" / "LaunchAgents"
    plist_dir.mkdir(parents=True, exist_ok=True)
    plist_file = plist_dir / "com.kingboyandgirl.ups-guard-agent.plist"
    exe = sys.executable
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.kingboyandgirl.ups-guard-agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>{exe}</string>
        <string>-m</string>
        <string>ups_guard_agent.main</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
"""
    plist_file.write_text(content)
    logger.info(f"Autostart installed: {plist_file}")


def _remove_macos():
    plist_file = Path.home() / "Library" / "LaunchAgents" / "com.kingboyandgirl.ups-guard-agent.plist"
    if plist_file.exists():
        plist_file.unlink()
        logger.info("Autostart removed (macOS LaunchAgent)")
