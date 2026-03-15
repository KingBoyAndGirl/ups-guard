"""快捷操作 API - 移动端友好"""
from fastapi import APIRouter, HTTPException
from typing import Optional
import logging

from services.nut_client import create_nut_client
from config import get_settings

router = APIRouter(prefix="/api/quick", tags=["quick-actions"])
logger = logging.getLogger(__name__)
settings = get_settings()


def _get_nut_client():
    """获取 NUT 客户端"""
    return create_nut_client(
        host=settings.nut_host,
        port=settings.nut_port,
        username=settings.nut_username,
        password=settings.nut_password,
        ups_name=settings.ups_name or "ups",
        mock_mode=settings.mock_mode,
    )


@router.post("/mute-beeper")
async def mute_beeper():
    """静音蜂鸣器"""
    client = _get_nut_client()
    try:
        await client.connect()
        success = await client.run_command("beeper.mute")
        await client.disconnect()
        if success:
            return {"success": True, "message": "蜂鸣器已静音"}
        else:
            raise HTTPException(500, "静音命令执行失败")
    except Exception as e:
        logger.error(f"Failed to mute beeper: {e}")
        raise HTTPException(500, str(e))


@router.post("/test-battery")
async def test_battery(deep: bool = False):
    """触发电池自检"""
    client = _get_nut_client()
    try:
        await client.connect()
        cmd = "test.battery.start.deep" if deep else "test.battery.start.quick"
        success = await client.run_command(cmd)
        await client.disconnect()
        if success:
            test_type = "深度" if deep else "快速"
            return {"success": True, "message": f"{test_type}自检已启动"}
        else:
            raise HTTPException(500, "自检命令执行失败")
    except Exception as e:
        logger.error(f"Failed to start battery test: {e}")
        raise HTTPException(500, str(e))


@router.post("/cancel-shutdown")
async def cancel_shutdown():
    """取消待执行的关机"""
    from services.shutdown_manager import get_shutdown_manager
    sm = get_shutdown_manager()
    if sm:
        sm.cancel_shutdown()
        return {"success": True, "message": "关机已取消"}
    return {"success": False, "message": "关机管理器未初始化"}


@router.get("/status-summary")
async def status_summary():
    """获取状态摘要（移动端优化）"""
    from services.monitor import get_monitor
    monitor = get_monitor()
    if not monitor:
        raise HTTPException(503, "监控服务未启动")
    
    data = monitor.get_current_data()
    if not data:
        raise HTTPException(503, "无 UPS 数据")
    
    return {
        "status": data.status.value,
        "battery_charge": data.battery_charge,
        "battery_runtime_minutes": data.battery_runtime // 60 if data.battery_runtime else None,
        "input_voltage": data.input_voltage,
        "output_voltage": data.output_voltage,
        "output_voltage_estimated": data.output_voltage_estimated,
        "load_percent": data.load_percent,
        "voltage_quality_grade": data.voltage_quality_grade,
        "ups_test_result": data.ups_test_result,
        "last_update": data.last_update.isoformat() if data.last_update else None,
    }
