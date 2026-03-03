"""命令执行器"""
import asyncio
import logging
import platform
from typing import Any, Dict

logger = logging.getLogger(__name__)

# 危险命令黑名单（execute action 安全检查）
_DANGEROUS_PATTERNS = [
    "rm -rf /",
    "dd if=",
    "mkfs",
    "> /dev/",
    "format c:",
    "del /f /s /q c:\\",
]


async def _run(cmd: list, operation: str, power_action: bool = False) -> Dict[str, Any]:
    """使用 asyncio.create_subprocess_exec 执行命令，关机类超时视为成功"""
    logger.info(f"Running {operation}: cmd={cmd}")
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
            if process.returncode == 0:
                result = {"success": True, "message": stdout.decode(errors="replace").strip()}
            else:
                result = {
                    "success": False,
                    "message": stderr.decode(errors="replace").strip() or f"Exit code {process.returncode}",
                }
            logger.info(f"{operation} result: success={result['success']} message={result['message']!r}")
            return result
        except asyncio.TimeoutError:
            if power_action:
                logger.info(f"{operation}: timed out, treating as success")
                return {"success": True, "message": "Command sent (timed out, treated as success)"}
            logger.warning(f"{operation}: timed out")
            return {"success": False, "message": f"{operation} timed out"}
    except Exception as e:
        if power_action:
            logger.info(f"{operation}: error ({e}), treating as success")
            return {"success": True, "message": f"Command sent ({e}, treated as success)"}
        logger.warning(f"{operation}: exception: {e}")
        return {"success": False, "message": str(e)}


async def _shutdown(params: Dict[str, Any]) -> Dict[str, Any]:
    delay = int(params.get("delay", 60))
    message = params.get("message", "UPS power lost")
    logger.info(f"shutdown: delay={delay} message={message!r}")
    sys = platform.system()
    if sys == "Windows":
        cmd = ["shutdown", "/s", "/t", str(delay), "/f", "/c", message]
    elif sys == "Darwin":
        cmd = ["sudo", "shutdown", "-h", f"+{delay // 60}"]
    else:
        cmd = ["sudo", "shutdown", "-h", f"+{delay // 60}"]
    return await _run(cmd, "shutdown", power_action=True)


async def _reboot(params: Dict[str, Any]) -> Dict[str, Any]:
    delay = int(params.get("delay", 0))
    logger.info(f"reboot: delay={delay}")
    sys = platform.system()
    if sys == "Windows":
        cmd = ["shutdown", "/r", "/t", str(delay), "/f"]
    elif sys == "Darwin":
        cmd = ["sudo", "shutdown", "-r", "now"]
    else:
        cmd = ["sudo", "reboot"]
    return await _run(cmd, "reboot", power_action=True)


async def _sleep(_params: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("sleep requested")
    sys = platform.system()
    if sys == "Windows":
        cmd = ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"]
    elif sys == "Darwin":
        cmd = ["pmset", "sleepnow"]
    else:
        cmd = ["systemctl", "suspend"]
    return await _run(cmd, "sleep", power_action=True)


async def _hibernate(_params: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("hibernate requested")
    sys = platform.system()
    if sys == "Windows":
        cmd = ["shutdown", "/h"]
    elif sys == "Darwin":
        cmd = ["pmset", "sleepnow"]
    else:
        cmd = ["systemctl", "hibernate"]
    return await _run(cmd, "hibernate", power_action=True)


async def _cancel_shutdown(_params: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("cancel_shutdown requested")
    sys = platform.system()
    if sys == "Windows":
        cmd = ["shutdown", "/a"]
    else:
        cmd = ["sudo", "shutdown", "-c"]
    return await _run(cmd, "cancel_shutdown")


async def _execute(params: Dict[str, Any]) -> Dict[str, Any]:
    import shlex
    command = params.get("command", "")
    if not command:
        return {"success": False, "message": "No command provided"}

    # 安全检查
    for pattern in _DANGEROUS_PATTERNS:
        if pattern.lower() in command.lower():
            logger.warning(f"Blocked dangerous command: {command}")
            return {"success": False, "message": f"Command blocked for safety: {pattern}"}

    try:
        cmd = shlex.split(command)
    except ValueError as e:
        return {"success": False, "message": f"Invalid command syntax: {e}"}
    return await _run(cmd, "execute")


async def handle_command(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """分发命令入口"""
    logger.info(f"Dispatching action={action} params={params}")
    handlers = {
        "shutdown": _shutdown,
        "reboot": _reboot,
        "sleep": _sleep,
        "hibernate": _hibernate,
        "cancel_shutdown": _cancel_shutdown,
        "execute": _execute,
    }
    handler = handlers.get(action)
    if handler is None:
        logger.warning(f"Unknown action: {action}")
        return {"success": False, "message": f"Unknown action: {action}"}
    result = await handler(params)
    logger.info(f"Action {action} finished: success={result.get('success')} message={result.get('message', '')!r}")
    return result
