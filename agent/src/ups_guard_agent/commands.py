"""命令执行器"""
import asyncio
import logging
import platform
from typing import Any, Dict

logger = logging.getLogger(__name__)

# 危险命令黑名单（execute 动作的安全检查）
_DANGEROUS_PATTERNS = [
    "rm -rf /",
    "dd if=",
    "mkfs",
    "> /dev/",
    "format c:",
    "del /f /s /q c:\\",
]


async def _run(cmd: list, operation: str, power_action: bool = False) -> Dict[str, Any]:
    """使用 asyncio.create_subprocess_exec 执行命令

    Args:
        cmd: 命令参数列表
        operation: 操作名称（用于日志）
        power_action: 是否为电源操作（关机/重启等），超时时视为成功
    """
    logger.info(f"执行 {operation}: cmd={cmd}")
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
                    "message": stderr.decode(errors="replace").strip() or f"退出码 {process.returncode}",
                }
            logger.info(f"{operation} 结果: success={result['success']} message={result['message']!r}")
            return result
        except asyncio.TimeoutError:
            if power_action:
                # 电源操作超时视为成功（系统可能已开始关机）
                logger.info(f"{operation}: 超时，视为成功（电源操作）")
                return {"success": True, "message": "命令已发送（超时，视为成功）"}
            logger.warning(f"{operation}: 执行超时")
            return {"success": False, "message": f"{operation} 执行超时"}
    except Exception as e:
        if power_action:
            logger.info(f"{operation}: 异常 ({e})，视为成功（电源操作）")
            return {"success": True, "message": f"命令已发送（{e}，视为成功）"}
        logger.warning(f"{operation}: 异常: {e}")
        return {"success": False, "message": str(e)}


async def _shutdown(params: Dict[str, Any]) -> Dict[str, Any]:
    """执行关机命令"""
    delay = int(params.get("delay", 60))
    message = params.get("message", "UPS 电量不足")
    force = params.get("force", False)
    logger.info(f"关机: delay={delay} message={message!r} force={force}")
    sys = platform.system()
    if sys == "Windows":
        # 默认不加 /f，让预关机命令优雅关闭应用后由 Windows 正常关机
        # 仅在 force=True（紧急关机，续航过短）时强制关闭残留应用
        cmd = ["shutdown", "/s", "/t", str(delay), "/c", message]
        if force:
            cmd.insert(4, "/f")
    elif sys == "Darwin":
        cmd = ["sudo", "shutdown", "-h", f"+{delay // 60}"]
    else:
        cmd = ["sudo", "shutdown", "-h", f"+{delay // 60}"]
    return await _run(cmd, "关机", power_action=True)


async def _reboot(params: Dict[str, Any]) -> Dict[str, Any]:
    """执行重启命令"""
    delay = int(params.get("delay", 0))
    logger.info(f"重启: delay={delay}")
    sys = platform.system()
    if sys == "Windows":
        cmd = ["shutdown", "/r", "/t", str(delay), "/f"]
    elif sys == "Darwin":
        cmd = ["sudo", "shutdown", "-r", "now"]
    else:
        cmd = ["sudo", "reboot"]
    return await _run(cmd, "重启", power_action=True)


async def _sleep(_params: Dict[str, Any]) -> Dict[str, Any]:
    """执行睡眠命令"""
    logger.info("收到睡眠请求")
    sys = platform.system()
    if sys == "Windows":
        cmd = ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"]
    elif sys == "Darwin":
        cmd = ["pmset", "sleepnow"]
    else:
        cmd = ["systemctl", "suspend"]
    return await _run(cmd, "睡眠", power_action=True)


async def _hibernate(_params: Dict[str, Any]) -> Dict[str, Any]:
    """执行休眠命令"""
    logger.info("收到休眠请求")
    sys = platform.system()
    if sys == "Windows":
        cmd = ["shutdown", "/h"]
    elif sys == "Darwin":
        cmd = ["pmset", "sleepnow"]
    else:
        cmd = ["systemctl", "hibernate"]
    return await _run(cmd, "休眠", power_action=True)


async def _cancel_shutdown(_params: Dict[str, Any]) -> Dict[str, Any]:
    """取消关机"""
    logger.info("收到取消关机请求")
    sys = platform.system()
    if sys == "Windows":
        cmd = ["shutdown", "/a"]
    else:
        cmd = ["sudo", "shutdown", "-c"]
    return await _run(cmd, "取消关机")


async def _execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """执行自定义命令"""
    import shlex
    command = params.get("command", "")
    if not command:
        return {"success": False, "message": "未提供命令"}

    # 安全检查：拦截危险命令
    for pattern in _DANGEROUS_PATTERNS:
        if pattern.lower() in command.lower():
            logger.warning(f"已拦截危险命令: {command}")
            return {"success": False, "message": f"命令因安全原因被拦截: {pattern}"}

    try:
        cmd = shlex.split(command)
    except ValueError as e:
        return {"success": False, "message": f"命令语法错误: {e}"}
    return await _run(cmd, "自定义命令")


async def handle_command(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """命令分发入口"""
    logger.info(f"分发命令: action={action} params={params}")
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
        logger.warning(f"未知命令: {action}")
        return {"success": False, "message": f"未知命令: {action}"}
    result = await handler(params)
    logger.info(f"命令 {action} 完成: success={result.get('success')} message={result.get('message', '')!r}")
    return result
