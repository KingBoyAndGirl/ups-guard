"""开机自启管理"""
import logging
import platform
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_REG_NAME = "UpsGuardAgent"            # Legacy plain-registry entry — cleaned up on upgrade
_WIN_TRAY_REG_NAME = "UpsGuardAgentTray"  # Tray companion auto-start entry
_WIN_SERVICE_NAME = "UpsGuardAgent"
_LINUX_SERVICE = Path.home() / ".config" / "systemd" / "user" / "ups-guard-agent.service"
_MACOS_PLIST = Path.home() / "Library" / "LaunchAgents" / "com.kingboyandgirl.ups-guard-agent.plist"


def _get_service_bin_path() -> str:
    """Return binPath string for Windows service (includes --service flag).

    The executable path is quoted to handle paths containing spaces.
    """
    exe = sys.executable
    # Quote the exe path if it contains spaces so SCM can parse the binary path
    if " " in exe:
        exe = f'"{exe}"'
    if getattr(sys, "frozen", False):
        return f"{exe} --service"
    return f"{exe} -m ups_guard_agent.main --service"


def _get_tray_cmd() -> str:
    """Return command for tray companion auto-start (includes --tray-only flag)."""
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


# ─────────────────────────── Windows helpers ────────────────────────────── #

def _is_elevated_windows() -> bool:
    """Return True if the current process has administrator privileges."""
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _run_sc(*args: str) -> tuple[int, str]:
    """Run sc.exe with *args and return (returncode, combined_output).

    sc.exe uses an unusual parameter syntax where each option is 'key= value'
    (with a space after '='). We use shell=True so that cmd.exe processes the
    command line exactly as a user would type it, avoiding Python subprocess
    auto-quoting interference with sc.exe's non-standard argument parsing.
    """
    try:
        # Build the command string: "sc.exe arg1 arg2 ..."
        # Each arg is expected to already be correctly formatted (e.g. 'binPath= "path"')
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
        logger.warning(f"sc.exe call failed: {e}")
        return -1, str(e)


def _is_enabled_windows() -> bool:
    """Check that Windows service exists and is configured for automatic start."""
    rc, out = _run_sc("qc", _WIN_SERVICE_NAME)
    return rc == 0 and "AUTO_START" in out


def _install_service_elevated(agent_name: str) -> None:
    """Create / reconfigure the Windows service (must run as Administrator)."""
    bin_path = _get_service_bin_path()
    rc, _ = _run_sc("qc", _WIN_SERVICE_NAME)
    if rc != 0:
        # Service does not exist — create it.
        # The entire binPath value (exe + args) must be wrapped in outer double-quotes so
        # cmd.exe passes it as a single token to sc.exe.  Any inner quotes (added by
        # _get_service_bin_path for paths that contain spaces) are escaped with backslash
        # so that CommandLineToArgvW / sc.exe interpret them correctly.
        bin_path_sc = '"' + bin_path.replace('"', r'\"') + '"'
        rc, out = _run_sc(
            "create", _WIN_SERVICE_NAME,
            f"binPath= {bin_path_sc}",
            f'DisplayName= "{agent_name}"',
            "start= auto",
            "obj= LocalSystem",
        )
        if rc != 0:
            logger.error(f"sc.exe create failed (rc={rc}): {out.strip()}")
            raise RuntimeError(f"sc.exe create failed (rc={rc}): {out.strip()}")
        logger.info(f"Windows service '{_WIN_SERVICE_NAME}' created")
    else:
        # Service exists — ensure auto-start
        _run_sc("config", _WIN_SERVICE_NAME, "start= auto")
        logger.info(f"Windows service '{_WIN_SERVICE_NAME}' reconfigured to auto-start")

    # Configure failure recovery: restart 3 times with 10-second delays, reset after 1 hour
    _run_sc(
        "failure", _WIN_SERVICE_NAME,
        "reset= 3600",
        "actions= restart/10000/restart/10000/restart/10000",
    )
    logger.info("Service failure recovery configured")

    # Start service immediately (error 1056 = already running is acceptable)
    rc, out = _run_sc("start", _WIN_SERVICE_NAME)
    if rc not in (0, 1056):
        logger.warning(f"sc.exe start returned rc={rc}: {out.strip()}")
    else:
        logger.info(f"Windows service '{_WIN_SERVICE_NAME}' started")


def _remove_service_elevated() -> None:
    """Stop and delete the Windows service (must run as Administrator)."""
    _run_sc("stop", _WIN_SERVICE_NAME)
    rc, out = _run_sc("delete", _WIN_SERVICE_NAME)
    if rc != 0:
        logger.warning(f"sc.exe delete returned rc={rc}: {out.strip()}")
    else:
        logger.info(f"Windows service '{_WIN_SERVICE_NAME}' deleted")


def _set_tray_registry() -> None:
    """Register tray companion in HKCU\\...\\Run and clean up legacy entry."""
    try:
        import winreg
        tray_cmd = _get_tray_cmd()
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, _WIN_TRAY_REG_NAME, 0, winreg.REG_SZ, tray_cmd)
        winreg.CloseKey(key)
        logger.info(f"Tray companion registered in HKCU Run: {tray_cmd}")
        _remove_legacy_registry()
    except Exception as e:
        logger.error(f"Failed to set tray registry entry: {e}")


def _remove_tray_registry() -> None:
    """Remove tray companion entry from HKCU\\...\\Run."""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, _WIN_TRAY_REG_NAME)
            logger.info("Tray companion registry entry removed")
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
        _remove_legacy_registry()
    except Exception as e:
        logger.error(f"Failed to remove tray registry entry: {e}")


def _remove_legacy_registry() -> None:
    """Remove the old single-process HKCU Run entry if it still exists."""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, _REG_NAME)
            logger.info("Legacy HKCU Run entry removed")
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
    except Exception:
        pass


def _request_uac(verb: str) -> None:
    """Re-launch this exe as Administrator via ShellExecuteW (runas).

    The elevated process runs asynchronously; the caller returns immediately.
    """
    import ctypes
    if getattr(sys, "frozen", False):
        exe = sys.executable
        params = verb
    else:
        exe = sys.executable
        params = f"-m ups_guard_agent.main {verb}"
    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    if result <= 32:
        raise RuntimeError(f"ShellExecuteW(runas) failed with code {result}")
    logger.info(f"UAC elevation requested for '{verb}'")


def _install_windows(agent_name: str) -> None:
    """Install Windows service + register tray companion in HKCU Run.

    When not elevated, requests UAC and delegates all work to the elevated process.
    When already elevated (e.g. launched via --install), performs work directly.
    """
    if _is_elevated_windows():
        _install_service_elevated(agent_name)
        _set_tray_registry()
    else:
        # Spawn an elevated UPSGuardAgent.exe --install; it will do everything.
        _request_uac("--install")
        logger.info("Service installation delegated to elevated process")


def _remove_windows() -> None:
    """Stop/delete service + remove tray registry entry.

    Requests UAC elevation when not already elevated.
    """
    if _is_elevated_windows():
        _remove_service_elevated()
        _remove_tray_registry()
    else:
        _request_uac("--uninstall")
        logger.info("Service removal delegated to elevated process")


# ─────────────────────────── Linux helpers ──────────────────────────────── #

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


# ─────────────────────────── macOS helpers ──────────────────────────────── #

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
