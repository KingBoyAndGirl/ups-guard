"""设备管理 API"""
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from hooks.registry import get_registry
from config import get_config_manager
from services.wol import send_wol
from services.history import HistoryService
from services.notifier import get_notifier_service
from db.database import get_db
from models import EventType

logger = logging.getLogger(__name__)

# 设备操作超时时间（秒）
DEVICE_OPERATION_TIMEOUT = 30.0
SSH_COMMAND_TIMEOUT = 30.0
MAX_COMMAND_LENGTH = 1024

# SSH 命令注入防护 - 黑名单字符
FORBIDDEN_CHARS = [';', '&&', '||', '|', '`', '$', '(', ')', '<', '>', '&', '\n', '\r', '{', '}', '[', ']', '*', '?', '\\', '"', "'"]

router = APIRouter()


class CommandExecuteRequest(BaseModel):
    """命令执行请求"""
    command: str


class CommandExecuteResponse(BaseModel):
    """命令执行响应"""
    success: bool
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    exit_code: Optional[int] = None
    error: Optional[str] = None


class DeviceCheckResponse(BaseModel):
    """设备检查响应"""
    online: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    system_info: Optional[str] = None


class DeviceShutdownRequest(BaseModel):
    """设备关机请求"""
    dry_run: bool = False


class WOLSendRequest(BaseModel):
    """WOL 发送请求"""
    mac_address: str
    broadcast_address: str = "255.255.255.255"


def validate_command(command: str) -> None:
    """
    验证命令安全性
    
    Args:
        command: 要执行的命令
    
    Raises:
        ValueError: 命令不安全
    """
    if len(command) > MAX_COMMAND_LENGTH:
        raise ValueError(f"命令长度超过限制 {MAX_COMMAND_LENGTH} 字符")
    
    # 检查黑名单字符
    for char in FORBIDDEN_CHARS:
        if char in command:
            raise ValueError(f"命令包含禁止字符: {repr(char)}")


async def get_device_by_index(device_index: int) -> tuple:
    """
    根据索引获取设备配置
    
    Returns:
        (hook_config, hook_instance)
    """
    config_manager = await get_config_manager()
    config = await config_manager.get_config()
    hooks_config = config.pre_shutdown_hooks
    
    # 仅在测试模式为 "mock" 时且没有配置纳管设备时，注入两台模拟设备
    # 生产模式(production)和演练模式(dry_run)不应显示假数据
    if config.test_mode == "mock" and (not hooks_config or len(hooks_config) == 0):
        hooks_config = [
            {
                "name": "Mock Linux Server",
                "hook_id": "ssh_shutdown",
                "enabled": True,
                "priority": 1,
                "config": {
                    "host": "192.168.1.100",
                    "port": 22,
                    "username": "admin",
                    "auth_type": "password",
                    "password": "mock_password",
                    "mac_address": "AA:BB:CC:DD:EE:01",
                    "broadcast_address": "255.255.255.255"
                }
            },
            {
                "name": "Mock NAS",
                "hook_id": "synology_shutdown",
                "enabled": True,
                "priority": 2,
                "config": {
                    "host": "192.168.1.200",
                    "port": 22,
                    "username": "admin",
                    "auth_type": "password",
                    "password": "mock_password",
                    "mac_address": "AA:BB:CC:DD:EE:02",
                    "broadcast_address": "255.255.255.255"
                }
            }
        ]
    
    if not hooks_config or device_index >= len(hooks_config):
        raise HTTPException(status_code=404, detail="设备不存在")
    
    hook_config = hooks_config[device_index]
    
    # 创建 hook 实例
    registry = get_registry()
    try:
        hook_instance = registry.create_instance(
            hook_config.get("hook_id"),
            hook_config.get("config", {})
        )
        return hook_config, hook_instance
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"设备配置错误: {str(e)}")


@router.get("/devices")
async def list_devices():
    """
    获取所有纳管设备列表
    
    Returns:
        {
            "devices": [
                {
                    "index": 0,
                    "name": "Ubuntu Server",
                    "hook_id": "ssh_shutdown",
                    "enabled": true,
                    "priority": 1,
                    "config": {...}
                }
            ]
        }
    """
    config_manager = await get_config_manager()
    config = await config_manager.get_config()
    hooks_config = config.pre_shutdown_hooks
    
    # 仅在测试模式为 "mock" 时且没有配置纳管设备时，注入两台模拟设备
    # 生产模式(production)和演练模式(dry_run)不应显示假数据
    if config.test_mode == "mock" and (not hooks_config or len(hooks_config) == 0):
        hooks_config = [
            {
                "name": "Mock Linux Server",
                "hook_id": "ssh_shutdown",
                "enabled": True,
                "priority": 1,
                "config": {
                    "host": "192.168.1.100",
                    "port": 22,
                    "username": "admin",
                    "auth_type": "password",
                    "password": "mock_password",
                    "mac_address": "AA:BB:CC:DD:EE:01",
                    "broadcast_address": "255.255.255.255"
                }
            },
            {
                "name": "Mock NAS",
                "hook_id": "synology_shutdown",
                "enabled": True,
                "priority": 2,
                "config": {
                    "host": "192.168.1.200",
                    "port": 22,
                    "username": "admin",
                    "auth_type": "password",
                    "password": "mock_password",
                    "mac_address": "AA:BB:CC:DD:EE:02",
                    "broadcast_address": "255.255.255.255"
                }
            }
        ]
    
    devices = []
    registry = get_registry()
    for index, hook_config in enumerate(hooks_config):
        # Get hook class to retrieve supported_actions
        hook_id = hook_config.get("hook_id")
        supported_actions = ["shutdown"]  # Default
        try:
            hook_class = registry.get_hook(hook_id)
            if hasattr(hook_class, 'supported_actions'):
                supported_actions = hook_class.supported_actions
        except Exception:
            pass  # Use default if hook class not found
        
        devices.append({
            "index": index,
            "name": hook_config.get("name", "Unknown"),
            "hook_id": hook_config.get("hook_id"),
            "enabled": hook_config.get("enabled", True),
            "priority": hook_config.get("priority", 99),
            "config": hook_config.get("config", {}),
            "supported_actions": supported_actions
        })
    
    return {"devices": devices}


@router.get("/devices/status")
async def get_devices_status():
    """
    批量检查所有设备连通性
    
    Returns:
        {
            "devices": [
                {
                    "index": 0,
                    "name": "Ubuntu Server",
                    "hook_id": "ssh_shutdown",
                    "online": true,
                    "last_check": "2026-02-11T12:00:00",
                    "error": null
                }
            ]
        }
    """
    config_manager = await get_config_manager()
    config = await config_manager.get_config()
    hooks_config = config.pre_shutdown_hooks
    
    # 仅在测试模式为 "mock" 时且没有配置纳管设备时，注入两台模拟设备
    # 生产模式(production)和演练模式(dry_run)不应显示假数据
    if config.test_mode == "mock" and (not hooks_config or len(hooks_config) == 0):
        hooks_config = [
            {
                "name": "Mock Linux Server",
                "hook_id": "ssh_shutdown",
                "enabled": True,
                "priority": 1,
                "config": {
                    "host": "192.168.1.100",
                    "port": 22,
                    "username": "admin",
                    "auth_type": "password",
                    "password": "mock_password",
                    "mac_address": "AA:BB:CC:DD:EE:01",
                    "broadcast_address": "255.255.255.255"
                }
            },
            {
                "name": "Mock NAS",
                "hook_id": "synology_shutdown",
                "enabled": True,
                "priority": 2,
                "config": {
                    "host": "192.168.1.200",
                    "port": 22,
                    "username": "admin",
                    "auth_type": "password",
                    "password": "mock_password",
                    "mac_address": "AA:BB:CC:DD:EE:02",
                    "broadcast_address": "255.255.255.255"
                }
            }
        ]
    
    if not hooks_config:
        return {"devices": []}
    
    registry = get_registry()
    devices = []
    
    # 并行检测所有设备状态
    async def check_device(index: int, hook_config: dict) -> dict:
        """检测单个设备状态"""
        hook_id = hook_config.get("hook_id")
        hook_name = hook_config.get("name", "Unknown")
        
        # Get supported_actions from hook class
        supported_actions = ["shutdown"]  # Default
        try:
            hook_class = registry.get_hook(hook_id)
            if hasattr(hook_class, 'supported_actions'):
                supported_actions = hook_class.supported_actions
        except Exception:
            pass
        
        device_status = {
            "index": index,
            "name": hook_name,
            "hook_id": hook_id,
            "online": False,
            "last_check": datetime.now().isoformat(),
            "error": None,
            "supported_actions": supported_actions
        }
        
        if not hook_config.get("enabled", True):
            device_status["error"] = "设备已禁用"
            return device_status
        
        try:
            # 创建 hook 实例
            hook_instance = registry.create_instance(hook_id, hook_config.get("config", {}))
            
            # 测试连接（带超时）
            success = await asyncio.wait_for(
                hook_instance.test_connection(),
                timeout=5.0
            )
            
            device_status["online"] = success
            if not success:
                device_status["error"] = "连接测试失败"
        
        except asyncio.TimeoutError:
            device_status["error"] = "连接超时"
        except ValueError as e:
            device_status["error"] = f"配置错误: {str(e)}"
        except Exception as e:
            device_status["error"] = str(e)
        
        return device_status
    
    # 并行检测所有设备
    tasks = [check_device(i, hook_config) for i, hook_config in enumerate(hooks_config)]
    devices = await asyncio.gather(*tasks, return_exceptions=False)
    
    return {"devices": devices}


@router.post("/devices/{device_index}/execute")
async def execute_device_command(
    device_index: int = Path(..., ge=0),
    request: CommandExecuteRequest = None
) -> CommandExecuteResponse:
    """
    对指定设备执行 SSH 命令
    
    Args:
        device_index: 设备索引
        request: 命令执行请求
    
    Returns:
        命令执行结果
    """
    try:
        # 验证命令安全性
        validate_command(request.command)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    hook_config, hook_instance = await get_device_by_index(device_index)
    
    # 检查是否为 SSH 类设备
    hook_id = hook_config.get("hook_id")
    if hook_id not in ["ssh_shutdown", "windows_shutdown", "synology_shutdown", "qnap_shutdown", "lazycat_shutdown"]:
        raise HTTPException(status_code=400, detail="只有 SSH 类设备支持命令执行")
    
    # 执行命令
    try:
        import asyncssh
        
        config = hook_config.get("config", {})
        host = config.get("host")
        port = config.get("port", 22)
        username = config.get("username")
        auth_type = config.get("auth_type", "password")
        
        # 准备 SSH 连接参数
        connect_kwargs = {
            "host": host,
            "port": port,
            "username": username,
            "known_hosts": None
        }
        
        if auth_type == "password":
            connect_kwargs["password"] = config.get("password")
        else:
            connect_kwargs["client_keys"] = [config.get("private_key")]
        
        # 连接并执行命令
        try:
            async with asyncssh.connect(**connect_kwargs) as conn:
                result = await asyncio.wait_for(
                    conn.run(request.command, check=False),
                    timeout=SSH_COMMAND_TIMEOUT
                )
                
                return CommandExecuteResponse(
                    success=result.exit_status == 0,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.exit_status
                )
        except asyncio.TimeoutError:
            return CommandExecuteResponse(
                success=False,
                error=f"命令执行超时（{SSH_COMMAND_TIMEOUT}秒）"
            )
    
    except asyncio.TimeoutError:
        return CommandExecuteResponse(
            success=False,
            error=f"命令执行超时（{SSH_COMMAND_TIMEOUT}秒）"
        )
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        return CommandExecuteResponse(
            success=False,
            error=str(e)
        )


@router.post("/devices/{device_index}/check")
async def check_device(device_index: int = Path(..., ge=0)) -> DeviceCheckResponse:
    """
    对设备执行连通性检查
    
    Args:
        device_index: 设备索引
    
    Returns:
        连通性检查结果
    """
    hook_config, hook_instance = await get_device_by_index(device_index)
    
    device_name = hook_config.get("name", "Unknown")
    hook_id = hook_config.get("hook_id", "Unknown")
    start_time = datetime.now()
    
    try:
        # 测试连接
        success = await asyncio.wait_for(
            hook_instance.test_connection(),
            timeout=5.0
        )
        
        end_time = datetime.now()
        latency_ms = (end_time - start_time).total_seconds() * 1000
        
        # 记录测试连接事件
        db = await get_db()
        history_service = HistoryService(db)
        status_text = "在线" if success else "离线"
        await history_service.add_event(
            EventType.DEVICE_TEST_CONNECTION,
            f"设备 {device_name} 连接测试: {status_text}",
            metadata={
                "device_index": device_index,
                "device_name": device_name,
                "hook_id": hook_id,
                "online": success,
                "latency_ms": latency_ms if success else None
            }
        )
        
        # 发送通知（仅在配置了该事件时发送）
        notifier = get_notifier_service()
        if success:
            await notifier.notify(
                EventType.DEVICE_TEST_CONNECTION,
                f"设备连接测试",
                f"设备 {device_name} 在线，延迟 {latency_ms:.0f}ms"
            )
        else:
            await notifier.notify(
                EventType.DEVICE_TEST_CONNECTION,
                f"设备连接测试",
                f"设备 {device_name} 离线或无法连接"
            )
        
        # 对于 SSH 类设备，尝试获取系统信息
        system_info = None
        if success and hook_id in ["ssh_shutdown", "lazycat_shutdown", "synology_shutdown", "qnap_shutdown"]:
            try:
                import asyncssh
                config = hook_config.get("config", {})
                
                connect_kwargs = {
                    "host": config.get("host"),
                    "port": config.get("port", 22),
                    "username": config.get("username"),
                    "known_hosts": None
                }
                
                if config.get("auth_type", "password") == "password":
                    connect_kwargs["password"] = config.get("password")
                else:
                    connect_kwargs["client_keys"] = [config.get("private_key")]
                
                try:
                    async with asyncssh.connect(**connect_kwargs) as conn:
                        result = await asyncio.wait_for(
                            conn.run("uname -a || hostname", check=False),
                            timeout=3.0
                        )
                        if result.exit_status == 0:
                            system_info = result.stdout.strip()
                except asyncio.TimeoutError:
                    pass
            except:
                pass  # 忽略获取系统信息的失败
        
        return DeviceCheckResponse(
            online=success,
            latency_ms=latency_ms if success else None,
            error=None if success else "连接测试失败",
            system_info=system_info
        )
    
    except asyncio.TimeoutError:
        return DeviceCheckResponse(
            online=False,
            error="连接超时"
        )
    except Exception as e:
        return DeviceCheckResponse(
            online=False,
            error=str(e)
        )


@router.post("/devices/{device_index}/shutdown")
async def shutdown_device(
    device_index: int = Path(..., ge=0),
    request: DeviceShutdownRequest = None
):
    """
    单独关闭指定设备
    
    Args:
        device_index: 设备索引
        request: 关机请求（包含 dry_run 参数）
    
    Returns:
        关机结果
    """
    hook_config, hook_instance = await get_device_by_index(device_index)
    
    device_name = hook_config.get("name", "Unknown")
    hook_id = hook_config.get("hook_id", "Unknown")
    
    # 获取history service
    db = await get_db()
    history_service = HistoryService(db)
    
    if request and request.dry_run:
        # Dry-run 模式：只检查连通性
        try:
            success = await asyncio.wait_for(
                hook_instance.test_connection(),
                timeout=5.0
            )
            
            if success:
                return {
                    "success": True,
                    "message": f"[DRY-RUN] 设备 {device_name} 连接正常，未执行实际关机"
                }
            else:
                return {
                    "success": False,
                    "message": f"[DRY-RUN] 设备 {device_name} 连接失败"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"[DRY-RUN] 设备 {device_name} 检查失败: {str(e)}"
            }
    else:
        # 实际执行关机
        try:
            success = await asyncio.wait_for(
                hook_instance.execute(),
                timeout=DEVICE_OPERATION_TIMEOUT
            )
            
            if success:
                # 记录设备关机事件
                await history_service.add_event(
                    EventType.DEVICE_SHUTDOWN,
                    f"设备 {device_name} 关机命令已发送",
                    metadata={"device_index": device_index, "device_name": device_name, "hook_id": hook_id}
                )
                # 发送通知
                notifier = get_notifier_service()
                await notifier.notify(
                    EventType.DEVICE_SHUTDOWN,
                    f"设备关机",
                    f"设备 {device_name} 关机命令已发送"
                )
                return {
                    "success": True,
                    "message": f"设备 {device_name} 关机命令已发送"
                }
            else:
                return {
                    "success": False,
                    "message": f"设备 {device_name} 关机失败"
                }
        
        except asyncio.TimeoutError:
            return {
                "success": False,
                "message": f"设备 {device_name} 关机超时"
            }
        except Exception as e:
            logger.error(f"Device {device_name} shutdown failed: {e}")
            return {
                "success": False,
                "message": f"设备 {device_name} 关机失败: {str(e)}"
            }


@router.post("/devices/{device_index}/wake")
async def wake_device(device_index: int = Path(..., ge=0)):
    """
    发送 WOL 魔术包唤醒设备
    
    Args:
        device_index: 设备索引
    
    Returns:
        唤醒结果
    """
    hook_config, _ = await get_device_by_index(device_index)
    
    device_name = hook_config.get("name", "Unknown")
    hook_id = hook_config.get("hook_id", "Unknown")
    config = hook_config.get("config", {})
    mac_address = config.get("mac_address")
    
    if not mac_address:
        raise HTTPException(status_code=400, detail="设备未配置 MAC 地址")
    
    broadcast_address = config.get("broadcast_address", "255.255.255.255")
    
    # 发送 WOL
    success = await send_wol(mac_address, broadcast_address)
    
    if success:
        # 记录设备唤醒事件
        db = await get_db()
        history_service = HistoryService(db)
        await history_service.add_event(
            EventType.DEVICE_WAKE,
            f"设备 {device_name} WOL 唤醒包已发送",
            metadata={"device_index": device_index, "device_name": device_name, "hook_id": hook_id, "mac_address": mac_address}
        )
        # 发送通知
        notifier = get_notifier_service()
        await notifier.notify(
            EventType.DEVICE_WAKE,
            f"设备唤醒",
            f"设备 {device_name} WOL 唤醒包已发送"
        )
        return {
            "success": True,
            "message": f"WOL 魔术包已发送到设备 {device_name} ({mac_address})"
        }
    else:
        raise HTTPException(status_code=500, detail="WOL 发送失败")


@router.post("/wol/send")
async def send_wol_manual(request: WOLSendRequest):
    """
    手动发送 WOL 包
    
    Args:
        request: WOL 请求（mac_address + broadcast_address）
    
    Returns:
        发送结果
    """
    success = await send_wol(request.mac_address, request.broadcast_address)
    
    if success:
        return {
            "success": True,
            "message": f"WOL 魔术包已发送到 {request.mac_address}"
        }
    else:
        raise HTTPException(status_code=500, detail="WOL 发送失败")


@router.post("/devices/{device_index}/logs")
async def get_device_logs(device_index: int = Path(..., ge=0)):
    """
    获取设备日志
    
    根据设备类型自动选择合适的日志查看命令：
    - Linux (SSH): journalctl --no-pager -n 100 --since '1 hour ago'
    - Windows (SSH): powershell.exe -Command "Get-EventLog -LogName System -Newest 50 | Format-List"
    - Synology: cat /var/log/messages | tail -100
    - QNAP: cat /var/log/event_log.csv | tail -100
    - 其他: dmesg | tail -100
    
    用户可在配置中自定义日志查看命令（config.log_command）
    
    Args:
        device_index: 设备索引
    
    Returns:
        日志内容
    """
    hook_config, hook_instance = await get_device_by_index(device_index)
    
    # 检查是否为 SSH 类设备
    hook_id = hook_config.get("hook_id")
    if hook_id not in ["ssh_shutdown", "windows_shutdown", "synology_shutdown", "qnap_shutdown", "lazycat_shutdown"]:
        raise HTTPException(status_code=400, detail="只有 SSH 类设备支持日志查看")
    
    # 获取配置
    config = hook_config.get("config", {})
    
    # 优先使用用户自定义的日志命令
    log_command = config.get("log_command")
    
    if not log_command:
        # 根据设备类型选择默认日志命令
        if hook_id == "ssh_shutdown":
            # Linux/macOS
            log_command = "journalctl --no-pager -n 100 --since '1 hour ago' 2>/dev/null || dmesg | tail -100"
        elif hook_id == "windows_shutdown":
            # Windows
            log_command = 'powershell.exe -Command "Get-EventLog -LogName System -Newest 50 | Format-List"'
        elif hook_id == "synology_shutdown":
            # Synology
            log_command = "cat /var/log/messages | tail -100"
        elif hook_id == "qnap_shutdown":
            # QNAP
            log_command = "cat /var/log/event_log.csv | tail -100 2>/dev/null || cat /var/log/messages | tail -100"
        elif hook_id == "lazycat_shutdown":
            # 懒猫（Linux）
            log_command = "journalctl --no-pager -n 100 --since '1 hour ago' 2>/dev/null || dmesg | tail -100"
        else:
            # 回退选项
            log_command = "dmesg | tail -100"
    
    # 执行日志查看命令
    try:
        import asyncssh
        
        host = config.get("host")
        port = config.get("port", 22)
        username = config.get("username")
        auth_type = config.get("auth_type", "password")
        
        # 准备 SSH 连接参数
        connect_kwargs = {
            "host": host,
            "port": port,
            "username": username,
            "known_hosts": None
        }
        
        if auth_type == "password":
            connect_kwargs["password"] = config.get("password")
        else:
            connect_kwargs["client_keys"] = [config.get("private_key")]
        
        # 连接并执行日志命令
        try:
            async with asyncssh.connect(**connect_kwargs) as conn:
                result = await asyncio.wait_for(
                    conn.run(log_command, check=False),
                    timeout=30.0
                )
                
                if result.exit_status == 0:
                    return {
                        "success": True,
                        "logs": result.stdout,
                        "command": log_command
                    }
                else:
                    return {
                        "success": False,
                        "error": f"命令执行失败 (退出码: {result.exit_status})",
                        "stderr": result.stderr,
                        "command": log_command
                    }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "日志查询超时（30秒）",
                "command": log_command
            }
    
    except Exception as e:
        logger.error(f"Failed to get device logs: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/devices/{device_index}/reboot")
async def reboot_device(device_index: int = Path(..., ge=0)):
    """
    重启指定设备
    
    Args:
        device_index: 设备索引
    
    Returns:
        重启结果
    """
    hook_config, hook_instance = await get_device_by_index(device_index)
    
    device_name = hook_config.get("name", "Unknown")
    hook_id = hook_config.get("hook_id", "Unknown")
    
    # Check if device supports reboot
    if not hasattr(hook_instance, 'reboot'):
        raise HTTPException(status_code=400, detail=f"设备 {device_name} 不支持重启操作")
    
    try:
        success = await asyncio.wait_for(
            hook_instance.reboot(),
            timeout=DEVICE_OPERATION_TIMEOUT
        )
        
        if success:
            # 记录设备重启事件
            db = await get_db()
            history_service = HistoryService(db)
            await history_service.add_event(
                EventType.DEVICE_REBOOT,
                f"设备 {device_name} 重启命令已发送",
                metadata={"device_index": device_index, "device_name": device_name, "hook_id": hook_id}
            )
            # 发送通知
            notifier = get_notifier_service()
            await notifier.notify(
                EventType.DEVICE_REBOOT,
                f"设备重启",
                f"设备 {device_name} 重启命令已发送"
            )
            return {
                "success": True,
                "message": f"设备 {device_name} 重启命令已发送"
            }
        else:
            return {
                "success": False,
                "message": f"设备 {device_name} 重启失败"
            }
    
    except asyncio.TimeoutError:
        return {
            "success": False,
            "message": f"设备 {device_name} 重启超时"
        }
    except Exception as e:
        logger.error(f"Device {device_name} reboot failed: {e}")
        return {
            "success": False,
            "message": f"设备 {device_name} 重启失败: {str(e)}"
        }


@router.post("/devices/{device_index}/sleep")
async def sleep_device(device_index: int = Path(..., ge=0)):
    """
    睡眠指定设备（挂起到内存）
    
    Args:
        device_index: 设备索引
    
    Returns:
        睡眠结果
    """
    hook_config, hook_instance = await get_device_by_index(device_index)
    
    device_name = hook_config.get("name", "Unknown")
    hook_id = hook_config.get("hook_id", "Unknown")
    
    # Check if device supports sleep
    if not hasattr(hook_instance, 'sleep'):
        raise HTTPException(status_code=400, detail=f"设备 {device_name} 不支持睡眠操作")
    
    try:
        success = await asyncio.wait_for(
            hook_instance.sleep(),
            timeout=DEVICE_OPERATION_TIMEOUT
        )
        
        if success:
            # 记录设备睡眠事件
            db = await get_db()
            history_service = HistoryService(db)
            await history_service.add_event(
                EventType.DEVICE_SLEEP,
                f"设备 {device_name} 睡眠命令已发送",
                metadata={"device_index": device_index, "device_name": device_name, "hook_id": hook_id}
            )
            # 发送通知
            notifier = get_notifier_service()
            await notifier.notify(
                EventType.DEVICE_SLEEP,
                f"设备睡眠",
                f"设备 {device_name} 睡眠命令已发送"
            )
            return {
                "success": True,
                "message": f"设备 {device_name} 睡眠命令已发送"
            }
        else:
            return {
                "success": False,
                "message": f"设备 {device_name} 睡眠失败"
            }
    
    except asyncio.TimeoutError:
        return {
            "success": False,
            "message": f"设备 {device_name} 睡眠超时"
        }
    except Exception as e:
        logger.error(f"Device {device_name} sleep failed: {e}")
        return {
            "success": False,
            "message": f"设备 {device_name} 睡眠失败: {str(e)}"
        }


@router.post("/devices/{device_index}/hibernate")
async def hibernate_device(device_index: int = Path(..., ge=0)):
    """
    休眠指定设备（挂起到磁盘）
    
    Args:
        device_index: 设备索引
    
    Returns:
        休眠结果
    """
    hook_config, hook_instance = await get_device_by_index(device_index)
    
    device_name = hook_config.get("name", "Unknown")
    hook_id = hook_config.get("hook_id", "Unknown")
    
    # Check if device supports hibernate
    if not hasattr(hook_instance, 'hibernate'):
        raise HTTPException(status_code=400, detail=f"设备 {device_name} 不支持休眠操作")
    
    try:
        success = await asyncio.wait_for(
            hook_instance.hibernate(),
            timeout=DEVICE_OPERATION_TIMEOUT
        )
        
        if success:
            # 记录设备休眠事件
            db = await get_db()
            history_service = HistoryService(db)
            await history_service.add_event(
                EventType.DEVICE_HIBERNATE,
                f"设备 {device_name} 休眠命令已发送",
                metadata={"device_index": device_index, "device_name": device_name, "hook_id": hook_id}
            )
            # 发送通知
            notifier = get_notifier_service()
            await notifier.notify(
                EventType.DEVICE_HIBERNATE,
                f"设备休眠",
                f"设备 {device_name} 休眠命令已发送"
            )
            return {
                "success": True,
                "message": f"设备 {device_name} 休眠命令已发送"
            }
        else:
            return {
                "success": False,
                "message": f"设备 {device_name} 休眠失败"
            }
    
    except asyncio.TimeoutError:
        return {
            "success": False,
            "message": f"设备 {device_name} 休眠超时"
        }
    except Exception as e:
        logger.error(f"Device {device_name} hibernate failed: {e}")
        return {
            "success": False,
            "message": f"设备 {device_name} 休眠失败: {str(e)}"
        }


class ScheduledActionRequest(BaseModel):
    """定时操作请求"""
    action: str  # shutdown, wake, sleep, hibernate, reboot
    scheduled_time: str  # ISO 格式的计划执行时间
    repeat: str = "once"  # once, daily, weekly


@router.post("/devices/{device_index}/schedule")
async def schedule_device_action(
    device_index: int = Path(..., ge=0),
    request: ScheduledActionRequest = ...
):
    """
    创建设备定时操作
    
    Args:
        device_index: 设备索引
        request: 定时操作请求
    
    Returns:
        创建结果，包含 schedule_id
    """
    from services.scheduler import get_scheduler
    
    hook_config, _ = await get_device_by_index(device_index)
    device_name = hook_config.get("name", "Unknown")
    
    # Validate action
    valid_actions = ["shutdown", "wake", "reboot", "sleep", "hibernate"]
    if request.action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action. Must be one of: {', '.join(valid_actions)}"
        )
    
    # Parse scheduled time
    try:
        scheduled_time = datetime.fromisoformat(request.scheduled_time.replace('Z', '+00:00'))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid scheduled_time format: {e}")
    
    # Validate repeat
    valid_repeats = ["once", "daily", "weekly"]
    if request.repeat not in valid_repeats:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid repeat. Must be one of: {', '.join(valid_repeats)}"
        )
    
    try:
        scheduler = get_scheduler()
        schedule_id = await scheduler.add_schedule(
            device_index=device_index,
            device_name=device_name,
            action=request.action,
            scheduled_time=scheduled_time,
            repeat=request.repeat
        )
        
        return {
            "success": True,
            "schedule_id": schedule_id,
            "message": f"定时任务已创建：{device_name} {request.action} at {scheduled_time}"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create schedule: {e}")
        raise HTTPException(status_code=500, detail=f"创建定时任务失败: {str(e)}")


@router.get("/devices/{device_index}/schedules")
async def get_device_schedules(device_index: int = Path(..., ge=0)):
    """
    获取设备的定时任务列表
    
    Args:
        device_index: 设备索引
    
    Returns:
        定时任务列表
    """
    from services.scheduler import get_scheduler
    
    # Verify device exists
    await get_device_by_index(device_index)
    
    scheduler = get_scheduler()
    schedules = await scheduler.get_schedules(device_index=device_index)
    
    return {"schedules": schedules}


@router.delete("/devices/{device_index}/schedules/{schedule_id}")
async def delete_device_schedule(
    device_index: int = Path(..., ge=0),
    schedule_id: str = Path(...)
):
    """
    删除定时任务
    
    Args:
        device_index: 设备索引
        schedule_id: 定时任务ID
    
    Returns:
        删除结果
    """
    from services.scheduler import get_scheduler
    
    # Verify device exists
    await get_device_by_index(device_index)
    
    scheduler = get_scheduler()
    success = await scheduler.remove_schedule(schedule_id)
    
    if success:
        return {
            "success": True,
            "message": f"定时任务 {schedule_id} 已删除"
        }
    else:
        raise HTTPException(status_code=404, detail="定时任务不存在")


@router.get("/schedules/all")
async def get_all_schedules():
    """
    获取所有定时任务列表
    
    Returns:
        所有定时任务
    """
    from services.scheduler import get_scheduler
    
    scheduler = get_scheduler()
    schedules = await scheduler.get_schedules()
    
    return {"schedules": schedules}
