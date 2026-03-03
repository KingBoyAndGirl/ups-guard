"""UPS Guard Agent 入口"""
import argparse
import asyncio
import logging
import sys


def setup_logging(debug: bool = False):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def interactive_setup() -> "AgentConfig":  # type: ignore[name-defined]
    """首次运行交互式配置"""
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


def main():
    parser = argparse.ArgumentParser(description="UPS Guard Agent")
    parser.add_argument("--server", help="服务器地址，如 http://192.168.1.100:8000")
    parser.add_argument("--token", help="API Token")
    parser.add_argument("--name", help="设备名称")
    parser.add_argument("--no-tray", action="store_true", help="禁用系统托盘图标")
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

    # 首次运行交互式配置
    if not cfg.server_url or not cfg.token:
        cfg = interactive_setup()

    logger.info(f"Starting UPS Guard Agent: id={cfg.agent_id} name={cfg.agent_name} server={cfg.server_url}")

    from ups_guard_agent.commands import handle_command
    from ups_guard_agent.client import AgentClient

    tray = None
    if not args.no_tray:
        try:
            from ups_guard_agent.tray import TrayIcon
            tray = TrayIcon()
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
