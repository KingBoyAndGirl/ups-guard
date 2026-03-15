"""分析报告 API"""
from fastapi import APIRouter, HTTPException
from typing import Optional
import logging

from services.monitor import get_monitor
from services.battery_analytics import analyze_battery
from models import UpsData

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
logger = logging.getLogger(__name__)


@router.get("/battery")
async def get_battery_analytics():
    """获取电池分析报告"""
    monitor = get_monitor()
    if not monitor:
        raise HTTPException(503, "监控服务未启动")
    
    data = monitor.get_current_data()
    if not data:
        # Monitor 还没数据，直接从 NUT 读取并返回简单分析
        try:
            from config import settings
            from services.nut_client import create_nut_client
            client = create_nut_client(
                host=settings.nut_host, port=settings.nut_port,
                username=settings.nut_username, password=settings.nut_password,
                ups_name=settings.ups_name or "ups", mock_mode=settings.mock_mode,
            )
            await client.connect()
            vars_dict = await client.list_vars()
            await client.disconnect()
            
            if not vars_dict:
                return {"error": "无法读取 UPS 数据"}
            
            battery_runtime = int(float(vars_dict.get("battery.runtime", "0") or "0"))
            load_percent = float(vars_dict.get("ups.load", "0") or "0")
            battery_voltage = float(vars_dict.get("battery.voltage", "0") or "0")
            ups_status = vars_dict.get("ups.status", "")
            
            # 简单负载修正
            if load_percent < 10: factor = 1.2
            elif load_percent < 30: factor = 1.0
            elif load_percent < 60: factor = 0.95
            else: factor = 0.85
            
            predicted_runtime = int(battery_runtime / 60 * factor) if battery_runtime else None
            
            return {
                "estimated_resistance_mohm": None,
                "resistance_trend": None,
                "needs_self_test": "No test" in (vars_dict.get("ups.test.result", "") or ""),
                "days_since_last_test": None,
                "recommended_test": "quick",
                "predicted_runtime_minutes": predicted_runtime,
                "prediction_confidence": "medium" if predicted_runtime else None,
                "prediction_factors": [f"负载 {load_percent}%"] if load_percent else [],
            }
        except Exception as e:
            logger.error(f"Failed to read UPS directly: {e}")
            return {"error": str(e)}
    
    history_voltages = None
    
    result = analyze_battery(
        battery_voltage=data.battery_voltage,
        battery_charge=data.battery_charge,
        battery_runtime=data.battery_runtime,
        load_percent=data.load_percent,
        input_voltage=data.input_voltage,
        input_voltage_nominal=data.input_voltage_nominal,
        ups_test_result=data.ups_test_result,
        ups_mfr_date=data.ups_mfr_date,
        battery_mfr_date=data.battery_mfr_date,
        status_flags=data.status_flags or [],
        history_voltages=history_voltages,
    )
    
    return {
        "estimated_resistance_mohm": result.estimated_resistance_mohm,
        "resistance_trend": result.resistance_trend,
        "needs_self_test": result.needs_self_test,
        "days_since_last_test": result.days_since_last_test,
        "recommended_test": result.recommended_test,
        "predicted_runtime_minutes": result.predicted_runtime_minutes,
        "prediction_confidence": result.prediction_confidence,
        "prediction_factors": result.prediction_factors,
    }
