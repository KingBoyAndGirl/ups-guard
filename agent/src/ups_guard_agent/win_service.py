"""Windows Service wrapper using win32serviceutil (pywin32).

This module provides a proper Windows service implementation that correctly
communicates with the Windows Service Control Manager (SCM).

When the SCM starts the service, it calls SvcDoRun() which launches the
AgentClient WebSocket loop. When SCM sends a stop signal, SvcStop() sets
an event that gracefully terminates the asyncio loop.
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
    """Windows Service Framework implementation for UPS Guard Agent."""

    _svc_name_ = _WIN_SERVICE_NAME
    _svc_display_name_ = _WIN_SERVICE_DISPLAY
    _svc_description_ = _WIN_SERVICE_DESC

    def __init__(self, args):
        super().__init__(args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self._client = None

    # ------------------------------------------------------------------ #
    #  SCM callbacks
    # ------------------------------------------------------------------ #
    def SvcStop(self):
        """Called by SCM when the service should stop."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        logger.info("Service stop requested by SCM")
        if self._client:
            self._client.stop()
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        """Called by SCM when the service starts — this is the main entry point."""
        # Report that we're starting up
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )

        try:
            self._main()
        except Exception as e:
            logger.error(f"Service fatal error: {e}", exc_info=True)
            servicemanager.LogErrorMsg(f"UPS Guard Agent fatal error: {e}")
        finally:
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_, ""),
            )

    # ------------------------------------------------------------------ #
    #  Agent logic
    # ------------------------------------------------------------------ #
    def _main(self):
        """Initialise logging, load config, and run the WebSocket client."""
        from ups_guard_agent.config import AgentConfig, CONFIG_FILE, LOG_FILE, STATUS_FILE
        from ups_guard_agent.commands import handle_command
        from ups_guard_agent.client import AgentClient

        # Setup logging (file only — no console when running as a service)
        _setup_service_logging(LOG_FILE)

        logger.info(
            f"Service starting — Python {sys.version} on {platform.platform()}"
        )
        logger.info(f"Config file: {CONFIG_FILE}")

        cfg = AgentConfig.load()
        if not cfg.server_url or not cfg.token:
            logger.error("No valid configuration. Service cannot start.")
            return

        logger.info(
            f"Starting service: id={cfg.agent_id} name={cfg.agent_name} "
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

        # Run the async client in an event loop
        # client.start() loops forever (with reconnect) until client.stop() is called
        asyncio.run(self._client.start())


# ------------------------------------------------------------------ #
#  Helpers
# ------------------------------------------------------------------ #
def _setup_service_logging(log_file, level: str = "INFO"):
    """Configure file-only logging for service mode."""
    from logging.handlers import RotatingFileHandler

    log_level = getattr(logging, level.upper(), logging.INFO)
    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    root = logging.getLogger()
    root.setLevel(log_level)

    try:
        handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setLevel(log_level)
        handler.setFormatter(logging.Formatter(fmt))
        root.addHandler(handler)
    except Exception:
        pass  # Service mode — nowhere to report this


def _write_status_file(status: str, detail: str, agent_id: str, server_url: str):
    """Write status JSON for the tray companion to read."""
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
    """Entry point called from main.py --service.

    When launched by SCM (as a Windows service), we start the service dispatcher.
    When launched directly from the command line (e.g. for debugging `--service`),
    the dispatcher call will fail and we fall back to running the agent directly.
    """
    try:
        # SCM expects clean argv — remove our custom --service flag
        original_argv = sys.argv[:]
        sys.argv = [sys.argv[0]]

        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(UPSGuardAgentService)
        servicemanager.StartServiceCtrlDispatcher()
    except Exception as e:
        # Not under SCM control (e.g. user ran `UPSGuardAgent.exe --service` from terminal)
        # Restore argv and fall back to running the agent directly
        sys.argv = original_argv
        _run_direct()


def _run_direct():
    """Fallback: run agent logic directly without SCM (for debugging --service locally)."""
    from ups_guard_agent.config import AgentConfig, CONFIG_FILE, LOG_FILE
    from ups_guard_agent.commands import handle_command
    from ups_guard_agent.client import AgentClient

    _setup_service_logging(LOG_FILE)
    logger.info(f"Direct service mode — Python {sys.version} on {platform.platform()}")

    cfg = AgentConfig.load()
    if not cfg.server_url or not cfg.token:
        logger.error("No valid configuration. Cannot start.")
        sys.exit(1)

    logger.info(f"Starting: id={cfg.agent_id} name={cfg.agent_name} server={cfg.server_url}")

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

