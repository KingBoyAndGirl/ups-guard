"""Windows 服务包装器（基于 pywin32）

本模块使用 win32serviceutil.ServiceFramework 实现标准的 Windows 服务接口，
正确地与 Windows 服务控制管理器（SCM）通信。

SCM 启动服务时调用 SvcDoRun() 启动 WebSocket 客户端循环。
SCM 发送停止信号时调用 SvcStop() 优雅地终止异步事件循环。
"""
import asyncio
import logging
import os
import platform
import sys

import servicemanager
import win32event
import win32service
import win32serviceutil

logger = logging.getLogger(__name__)

_WIN_SERVICE_NAME = "UPSGuardAgent"
_WIN_SERVICE_DISPLAY = "UPS Guard Agent"
_WIN_SERVICE_DESC = "UPS Guard Agent — 远程关机客户端，通过 WebSocket 反连 UPS Guard 服务端"


class UPSGuardAgentService(win32serviceutil.ServiceFramework):
    """Windows 服务框架实现"""

    _svc_name_ = _WIN_SERVICE_NAME
    _svc_display_name_ = _WIN_SERVICE_DISPLAY
    _svc_description_ = _WIN_SERVICE_DESC

    def __init__(self, args):
        super().__init__(args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self._client = None

    # ------------------------------------------------------------------ #
    #  SCM 回调
    # ------------------------------------------------------------------ #
    def SvcStop(self):
        """SCM 发送停止信号时调用"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        logger.info("收到 SCM 停止信号")
        if self._client:
            self._client.stop()
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        """SCM 启动服务时调用 — 主入口"""
        # 报告服务正在启动
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )

        try:
            self._main()
        except Exception as e:
            logger.error(f"服务致命错误: {e}", exc_info=True)
            servicemanager.LogErrorMsg(f"UPS Guard Agent 致命错误: {e}")
        finally:
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_, ""),
            )

    # ------------------------------------------------------------------ #
    #  Agent 逻辑
    # ------------------------------------------------------------------ #
    def _main(self):
        """初始化日志、加载配置、启动 WebSocket 客户端"""
        from ups_guard_agent.config import AgentConfig, CONFIG_FILE, get_log_file, cleanup_old_logs
        from ups_guard_agent.commands import handle_command
        from ups_guard_agent.client import AgentClient

        # 服务模式仅输出到文件（无控制台）
        log_file = get_log_file()
        _setup_service_logging(log_file)
        cleanup_old_logs()

        logger.info(f"服务启动中 — Python {sys.version}，平台 {platform.platform()}")
        logger.info(f"配置文件: {CONFIG_FILE}")

        cfg = AgentConfig.load()
        if not cfg.server_url or not cfg.token:
            logger.error("配置无效，服务无法启动")
            return

        logger.info(
            f"启动服务: id={cfg.agent_id} name={cfg.agent_name} "
            f"server={cfg.server_url}"
        )

        def status_callback(status: str, detail: str = ""):
            _write_status_file(status, detail, cfg.agent_id, cfg.server_url)

        self._client = AgentClient(
            server_url=cfg.server_url,
            token=cfg.token,
            agent_id=cfg.agent_id,
            agent_name=cfg.agent_name,
            command_handler=handle_command,
            status_callback=status_callback,
        )

        _write_status_file("connecting", "", cfg.agent_id, cfg.server_url)

        # 启动异步事件循环（client.start() 包含自动重连，直到 client.stop() 被调用）
        asyncio.run(self._client.start())


# ------------------------------------------------------------------ #
#  辅助函数
# ------------------------------------------------------------------ #
def _setup_service_logging(log_file, level: str = "INFO"):
    """配置服务模式的日志（仅写文件，无控制台）"""
    from logging.handlers import RotatingFileHandler
    from ups_guard_agent.config import LOG_MAX_SIZE_MB

    log_level = getattr(logging, level.upper(), logging.INFO)
    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    root = logging.getLogger()
    root.setLevel(log_level)

    try:
        handler = RotatingFileHandler(
            log_file,
            maxBytes=LOG_MAX_SIZE_MB * 1024 * 1024,
            backupCount=1,
            encoding="utf-8",
        )
        handler.setLevel(log_level)
        handler.setFormatter(logging.Formatter(fmt))
        root.addHandler(handler)
    except Exception:
        pass  # 服务模式下无法报告此错误


def _write_status_file(status: str, detail: str, agent_id: str, server_url: str):
    """写入状态 JSON 文件，供托盘伴侣进程读取"""
    from ups_guard_agent.config import STATUS_FILE
    from ups_guard_agent.system_info import get_mac_address
    import json
    from datetime import datetime

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
        STATUS_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def run_service_dispatch():
    """服务分发入口（由 main.py --service 调用）

    在 SCM 环境下启动服务分发器。
    在命令行直接运行时（如调试 --service），分发器会失败，自动降级为直接运行模式。
    """
    try:
        # SCM 期望干净的 argv — 移除自定义的 --service 参数
        original_argv = sys.argv[:]
        sys.argv = [sys.argv[0]]

        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(UPSGuardAgentService)
        servicemanager.StartServiceCtrlDispatcher()
    except Exception as e:
        # 非 SCM 环境（如用户在终端运行 UPSGuardAgent.exe --service）
        # 恢复 argv 并降级为直接运行
        sys.argv = original_argv
        _run_direct()


def _run_direct():
    """降级方案：不通过 SCM，直接运行 Agent 逻辑（用于命令行调试 --service）"""
    from ups_guard_agent.config import AgentConfig, CONFIG_FILE, get_log_file, cleanup_old_logs
    from ups_guard_agent.commands import handle_command
    from ups_guard_agent.client import AgentClient

    log_file = get_log_file()
    _setup_service_logging(log_file)
    cleanup_old_logs()

    logger.info(f"直接运行模式 — Python {sys.version}，平台 {platform.platform()}")

    cfg = AgentConfig.load()
    if not cfg.server_url or not cfg.token:
        logger.error("配置无效，无法启动")
        sys.exit(1)

    logger.info(f"启动: id={cfg.agent_id} name={cfg.agent_name} server={cfg.server_url}")

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

