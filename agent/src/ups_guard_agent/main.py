"""UPS Guard Agent 入口"""
import multiprocessing
import sys

# Windows 下 PyInstaller 打包必须在最开始调用
if __name__ == "__main__":
    multiprocessing.freeze_support()
    # 设置 spawn 模式，避免 fork 导致的问题
    if sys.platform == "win32":
        multiprocessing.set_start_method("spawn", force=True)

import argparse
import asyncio
import json
import logging
import os
import platform
import threading
import time
from datetime import datetime

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO"):
    """配置日志：同时输出到控制台和文件

    Args:
        level: 日志等级，可选 DEBUG, INFO, WARNING, ERROR
    """
    from ups_guard_agent.config import LOG_FILE

    log_level = getattr(logging, level.upper(), logging.INFO)
    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(fmt))
    root_logger.addHandler(console_handler)

    # 文件输出（5MB 轮转，保留 3 个备份）
    try:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(fmt))
        root_logger.addHandler(file_handler)
        root_logger.info(f"Log file: {LOG_FILE}")
    except Exception as e:
        root_logger.warning(f"Failed to create log file {LOG_FILE}: {e}")


def interactive_setup() -> "AgentConfig":  # type: ignore[name-defined]
    """命令行交互式配置（CLI 模式兜底）"""
    from ups_guard_agent.config import AgentConfig

    print("=== UPS Guard Agent 初始配置 ===")
    server_url = input("服务器地址（如 http://192.168.1.100:8000）: ").strip()
    token = input("API Token: ").strip()
    default_name_hint = __import__("socket").gethostname()
    agent_name = input(f"设备名称（直接回车使用 {default_name_hint}）: ").strip() or default_name_hint

    cfg = AgentConfig.load()
    cfg.server_url = server_url
    cfg.token = token
    cfg.agent_name = agent_name
    cfg.save()
    print(f"配置已保存。Agent ID: {cfg.agent_id}")
    return cfg


def _gui_setup() -> "AgentConfig":  # type: ignore[name-defined]
    """GUI 配置窗口（打包 exe 时使用）"""
    from ups_guard_agent.config import AgentConfig

    saved_cfg = None

    def on_save(cfg):
        nonlocal saved_cfg
        saved_cfg = cfg

    from ups_guard_agent.gui import ConfigWindow
    win = ConfigWindow(on_save=on_save)
    win.show(wait=True)  # 阻塞直到窗口关闭

    if saved_cfg and saved_cfg.server_url and saved_cfg.token:
        return saved_cfg

    # 用户关闭窗口但没保存有效配置
    return AgentConfig.load()


def _open_settings(client=None):
    """从托盘菜单打开设置窗口（非阻塞）"""
    from ups_guard_agent.gui import ConfigWindow

    save_callback = None
    autostart_callback = None

    if client is not None:
        def save_callback(cfg):
            client.update_config(cfg.server_url, cfg.token, cfg.agent_id, cfg.agent_name)
            client.reconnect()

        def autostart_callback(enabled: bool):
            """服务安装/卸载后处理 WebSocket 冲突。

            安装服务后：服务进程会启动自己的 WebSocket 客户端，
            当前进程必须停止自己的客户端，避免两个连接竞争同一个 agent_id。
            卸载服务后：当前进程需要重新连接。
            """
            if enabled:
                logger.info("Service installed — stopping current WebSocket client to avoid conflict")
                client.stop()
            else:
                logger.info("Service removed — reconnecting WebSocket client")
                client.reconnect()

    win = ConfigWindow(on_save=save_callback, on_autostart_changed=autostart_callback)
    win.show(wait=False)


def _is_gui_available() -> bool:
    """检测是否有 GUI 环境（打包 exe 或桌面环境）"""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.destroy()
        logger.debug("GUI environment available")
        return True
    except Exception as e:
        logger.debug(f"GUI environment not available: {e}")
        return False


def _write_status_file(status: str, detail: str, agent_id: str, server_url: str) -> None:
    """Write current connection status to shared status file for tray companion."""
    from ups_guard_agent.config import STATUS_FILE
    from ups_guard_agent.system_info import get_mac_address
    try:
        data = {
            "status": status,
            "detail": detail,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "pid": os.getpid(),
            "agent_id": agent_id,
            "server_url": server_url,
            "mac_address": get_mac_address(),
        }
        STATUS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.debug(f"Status file written: {status}")
    except Exception as e:
        logger.warning(f"Failed to write status file: {e}")


def _run_service_mode(args) -> None:
    """Windows 服务模式：纯后台运行，无 GUI / 无托盘，负责 WebSocket 连接。

    状态通过共享 JSON 文件暴露给托盘伴侣进程。

    在 Windows 上使用 pywin32 ServiceFramework 与 SCM 正确通信。
    在非 Windows 平台上直接运行 asyncio 事件循环（兼容 Linux/macOS）。
    """
    if sys.platform == "win32":
        try:
            from ups_guard_agent.win_service import run_service_dispatch
            run_service_dispatch()
            return
        except ImportError:
            logger.warning("pywin32 not available, falling back to direct mode")

    # 非 Windows 或 pywin32 不可用时的降级方案
    from ups_guard_agent.config import AgentConfig, CONFIG_FILE
    from ups_guard_agent.commands import handle_command
    from ups_guard_agent.client import AgentClient

    log_level = "DEBUG" if args.debug else args.log_level
    setup_logging(log_level)

    logger.info(f"Service mode starting — Python {sys.version} on {platform.platform()}")
    logger.info(f"Config file: {CONFIG_FILE}")

    cfg = AgentConfig.load()
    if args.server:
        cfg.server_url = args.server
    if args.token:
        cfg.token = args.token
    if args.name:
        cfg.agent_name = args.name

    if not cfg.server_url or not cfg.token:
        logger.error("No valid configuration. Service cannot start.")
        sys.exit(1)

    logger.info(f"Starting service: id={cfg.agent_id} name={cfg.agent_name} server={cfg.server_url}")

    def status_callback(status: str, detail: str = ""):
        _write_status_file(status, detail, cfg.agent_id, cfg.server_url)

    client = AgentClient(
        server_url=cfg.server_url,
        token=cfg.token,
        agent_id=cfg.agent_id,
        agent_name=cfg.agent_name,
        command_handler=handle_command,
        status_callback=status_callback,
    )

    _write_status_file("connecting", "", cfg.agent_id, cfg.server_url)
    asyncio.run(client.start())


def _run_tray_only_mode(args) -> None:
    """托盘伴侣模式：用户登录后启动，轮询状态文件显示托盘图标。

    不建立 WebSocket 连接，仅做状态展示和配置管理。
    """
    from ups_guard_agent.config import STATUS_FILE
    from ups_guard_agent.tray import TrayIcon

    log_level = "DEBUG" if args.debug else args.log_level
    setup_logging(log_level)

    logger.info(f"Tray-only mode starting — Python {sys.version} on {platform.platform()}")

    tray = TrayIcon(on_settings=lambda: _open_settings(None))
    tray.start()
    logger.info("Tray icon started (tray-only mode)")

    def _poll_status_file():
        """轮询状态文件，每 2 秒更新一次托盘状态。"""
        last_updated_at: str | None = None
        while True:
            try:
                if STATUS_FILE.exists():
                    data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
                    updated_at = data.get("updated_at")
                    if updated_at != last_updated_at:
                        last_updated_at = updated_at
                        tray.update_status(
                            data.get("status", "disconnected"),
                            data.get("detail", ""),
                        )
                else:
                    tray.update_status("disconnected", "")
            except Exception as e:
                logger.debug(f"Error reading status file: {e}")
            time.sleep(2)

    poll_thread = threading.Thread(target=_poll_status_file, daemon=True)
    poll_thread.start()

    # Keep the main thread alive; tray runs in a daemon thread via TrayIcon.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        tray.stop()


def main():
    parser = argparse.ArgumentParser(description="UPS Guard Agent")
    parser.add_argument("--server", help="服务器地址，如 http://192.168.1.100:8000")
    parser.add_argument("--token", help="API Token")
    parser.add_argument("--name", help="设备名称")
    parser.add_argument("--no-tray", action="store_true", help="禁用系统托盘图标")
    parser.add_argument("--no-gui", action="store_true", help="禁用 GUI，使用命令行交互")
    parser.add_argument("--install", action="store_true",
                        help="安装开机自启（Windows: 安装服务 + 注册托盘自启动）")
    parser.add_argument("--uninstall", action="store_true",
                        help="移除开机自启（Windows: 卸载服务 + 移除托盘自启动）")
    parser.add_argument("--service", action="store_true",
                        help="以 Windows 服务模式运行（无托盘、无 GUI，纯后台 WebSocket 连接）")
    parser.add_argument("--tray-only", action="store_true",
                        help="仅启动托盘伴侣（读取状态文件显示状态，不做 WebSocket 连接）")
    parser.add_argument("--debug", action="store_true", help="调试模式（等同于 --log-level DEBUG）")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        default="INFO", help="日志等级（默认 INFO）")
    args = parser.parse_args()

    # Service mode: pure background process, no GUI/tray
    if args.service:
        _run_service_mode(args)
        return

    # Tray-only mode: read status file and display tray icon
    if args.tray_only:
        _run_tray_only_mode(args)
        return

    # --debug 优先级高于 --log-level
    log_level = "DEBUG" if args.debug else args.log_level
    setup_logging(log_level)

    logger.info(f"Python {sys.version} on {platform.platform()}")

    from ups_guard_agent.config import AgentConfig, CONFIG_FILE

    logger.info(f"Config file: {CONFIG_FILE}")

    if args.install:
        logger.info("Installing autostart")
        from ups_guard_agent.autostart import install_autostart
        install_autostart()
        sys.exit(0)

    if args.uninstall:
        logger.info("Removing autostart")
        from ups_guard_agent.autostart import remove_autostart
        remove_autostart()
        sys.exit(0)

    # ============================================================
    # 第一步：先创建托盘图标（确保用户始终能看到托盘）
    # ============================================================
    tray = None
    if not args.no_tray:
        try:
            from ups_guard_agent.tray import TrayIcon
            tray = TrayIcon(on_settings=None)
            tray.start()
            logger.info("Tray icon started")
        except Exception as e:
            logger.warning(f"Tray icon unavailable: {e}")

    # ============================================================
    # 第二步：加载 / 获取配置
    # ============================================================
    logger.info("Loading configuration")
    cfg = AgentConfig.load()

    # 命令行参数覆盖配置文件
    if args.server:
        cfg.server_url = args.server
    if args.token:
        cfg.token = args.token
    if args.name:
        cfg.agent_name = args.name

    # 首次运行：无有效配置时弹出配置界面
    if not cfg.server_url or not cfg.token:
        logger.info("No valid config found, starting setup")
        if not args.no_gui and _is_gui_available():
            logger.info("Launching GUI setup")
            cfg = _gui_setup()
        else:
            logger.info("Launching CLI setup")
            cfg = interactive_setup()

    # 配置仍然无效，退出
    if not cfg.server_url or not cfg.token:
        logger.error("No valid configuration. Exiting.")
        if tray:
            tray.stop()
        sys.exit(1)

    # ============================================================
    # 第三步：启动 WebSocket 连接
    # ============================================================
    logger.info(f"Starting UPS Guard Agent: id={cfg.agent_id} name={cfg.agent_name} server={cfg.server_url}")

    from ups_guard_agent.commands import handle_command
    from ups_guard_agent.client import AgentClient

    client = AgentClient(
        server_url=cfg.server_url,
        token=cfg.token,
        agent_id=cfg.agent_id,
        agent_name=cfg.agent_name,
        command_handler=handle_command,
        status_callback=tray.update_status if tray else None,
    )

    if tray:
        tray._on_quit = client.stop
        tray._on_settings = lambda: _open_settings(client)

    asyncio.run(client.start())


if __name__ == "__main__":
    main()

