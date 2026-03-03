"""UPS Guard Agent 入口"""
import argparse
import asyncio
import logging
import sys


def setup_logging(debug: bool = False):
    """配置日志：同时输出到控制台和文件"""
    from ups_guard_agent.config import LOG_FILE

    level = logging.DEBUG if debug else logging.INFO
    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
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
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(fmt))
        root_logger.addHandler(file_handler)
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


def _open_settings():
    """从托盘菜单打开设置窗口（非阻塞）"""
    from ups_guard_agent.gui import ConfigWindow
    win = ConfigWindow()
    win.show(wait=False)


def _is_gui_available() -> bool:
    """检测是否有 GUI 环境（打包 exe 或桌面环境）"""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.destroy()
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="UPS Guard Agent")
    parser.add_argument("--server", help="服务器地址，如 http://192.168.1.100:8000")
    parser.add_argument("--token", help="API Token")
    parser.add_argument("--name", help="设备名称")
    parser.add_argument("--no-tray", action="store_true", help="禁用系统托盘图标")
    parser.add_argument("--no-gui", action="store_true", help="禁用 GUI，使用命令行交互")
    parser.add_argument("--install", action="store_true", help="安装开机自启")
    parser.add_argument("--uninstall", action="store_true", help="移除开机自启")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    args = parser.parse_args()

    setup_logging(args.debug)
    logger = logging.getLogger(__name__)

    from ups_guard_agent.config import AgentConfig

    if args.install:
        from ups_guard_agent.autostart import install_autostart
        install_autostart()
        sys.exit(0)

    if args.uninstall:
        from ups_guard_agent.autostart import remove_autostart
        remove_autostart()
        sys.exit(0)

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
        if not args.no_gui and _is_gui_available():
            cfg = _gui_setup()
        else:
            cfg = interactive_setup()

    # 配置仍然无效，退出
    if not cfg.server_url or not cfg.token:
        logger.error("No valid configuration. Exiting.")
        sys.exit(1)

    logger.info(f"Starting UPS Guard Agent: id={cfg.agent_id} name={cfg.agent_name} server={cfg.server_url}")

    from ups_guard_agent.commands import handle_command
    from ups_guard_agent.client import AgentClient

    tray = None
    if not args.no_tray:
        try:
            from ups_guard_agent.tray import TrayIcon
            tray = TrayIcon(on_settings=_open_settings)
            tray.start()
        except Exception as e:
            logger.warning(f"Tray icon unavailable: {e}")

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

    asyncio.run(client.start())


if __name__ == "__main__":
    main()
