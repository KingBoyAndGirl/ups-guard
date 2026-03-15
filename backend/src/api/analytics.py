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
        raise HTTPException(503, "无 UPS 数据")
    
    # 获取历史电压数据（需要从数据库查询，这里简化）
    history_voltages = None  # TODO: 从历史数据中获取最近电压
    
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
