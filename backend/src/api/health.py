"""健康检查 API"""
from fastapi import APIRouter
from services.monitor import get_monitor
from services.nut_client import RealNutClient, MockNutClient
from datetime import datetime

router = APIRouter()


@router.get("/health/nut")
async def nut_connection_health():
    """NUT 连接健康检查
    
    返回 NUT 连接的详细状态信息，包括：
    - 连接状态
    - 重连尝试次数
    - 最后错误信息
    - 连接类型（Real/Mock）
    
    Returns:
        dict: 包含连接状态信息的字典
    """
    monitor = get_monitor()
    if not monitor:
        return {
            "status": "unavailable",
            "reason": "Monitor service not initialized",
            "connected": False
        }
    
    client = monitor.nut_client
    status_info = {
        "status": "unknown",
        "connected": False,
        "connection_type": type(client).__name__
    }
    
    if isinstance(client, RealNutClient):
        # 真实 NUT 客户端
        conn_status = client.get_connection_status()
        status_info.update({
            "connected": conn_status.get("connected", False),
            "host": client.host,
            "port": client.port,
            "ups_name": client.ups_name,
            "reconnect_attempts": conn_status.get("reconnect_attempts", 0),
            "last_error": conn_status.get("last_error")
        })
        status_info["status"] = "connected" if status_info["connected"] else "disconnected"
    elif isinstance(client, MockNutClient):
        # Mock 模式
        status_info.update({
            "connected": True,
            "status": "mock_mode"
        })
    
    return status_info


@router.get("/health/detailed")
async def detailed_health():
    """详细健康检查
    
    返回系统各组件的详细健康状态，包括：
    - Monitor 运行状态
    - UPS 当前状态
    - NUT 连接状态（包括重连统计）
    - 重试统计信息
    
    Returns:
        dict: 详细的系统健康状态
    """
    monitor = get_monitor()
    
    if not monitor:
        return {
            "status": "error",
            "reason": "Monitor service not initialized",
            "timestamp": datetime.now().isoformat()
        }
    
    # 获取 Monitor 状态
    monitor_info = {
        "running": monitor._running,
        "current_status": monitor._current_status.value if monitor._current_status else "unknown",
        "poll_interval": monitor.poll_interval,
        "sample_interval": monitor.sample_interval,
    }
    
    # 获取 NUT 连接状态
    client = monitor.nut_client
    nut_info = {
        "connection_type": type(client).__name__,
        "connected": False,
        "reconnect_count": monitor._reconnect_count
    }
    
    if isinstance(client, RealNutClient):
        conn_status = client.get_connection_status()
        nut_info.update({
            "connected": conn_status.get("connected", False),
            "host": client.host,
            "port": client.port,
            "ups_name": client.ups_name,
            "last_error": conn_status.get("last_error")
        })
    elif isinstance(client, MockNutClient):
        nut_info["connected"] = True
        nut_info["mock_mode"] = True
    
    # 获取当前 UPS 数据（如果有）
    ups_info = None
    if monitor._current_data:
        ups_info = {
            "status": monitor._current_data.status.value,
            "battery_charge": monitor._current_data.battery_charge,
            "battery_runtime": monitor._current_data.battery_runtime,
            "input_voltage": monitor._current_data.input_voltage,
            "load_percent": monitor._current_data.load_percent,
            "last_update": monitor._current_data.last_update.isoformat()
        }
    
    # 组装结果
    result = {
        "status": "healthy" if monitor._running and nut_info["connected"] else "degraded",
        "timestamp": datetime.now().isoformat(),
        "monitor": monitor_info,
        "nut": nut_info,
        "ups": ups_info,
        "retry_stats": {
            "nut_reconnect_count": monitor._reconnect_count,
            "nut_connection_notified": monitor._connection_notified
        }
    }
    
    return result
