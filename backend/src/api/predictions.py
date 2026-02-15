"""预测 API"""
from fastapi import APIRouter
from services.ml_predictor import get_ml_predictor
from services.history import get_history_service
from db.database import get_db
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/predictions")
async def get_all_predictions():
    """获取所有预测结果"""
    predictor = get_ml_predictor()
    history_service = await get_history_service()
    
    # 获取历史数据
    events = await history_service.get_events(days=30)
    metrics = await history_service.get_metrics(hours=24 * 30)
    
    # 获取当前 UPS 状态
    db = await get_db()
    current_data = None
    try:
        # 尝试获取最新的指标数据
        if metrics:
            latest_metric = metrics[-1]
            current_battery_charge = latest_metric.battery_charge
            current_load = latest_metric.load_percent
        else:
            current_battery_charge = None
            current_load = None
    except Exception as e:
        logger.warning(f"Failed to get current UPS data: {e}")
        current_battery_charge = None
        current_load = None
    
    # 获取各项预测
    outage_prediction = await predictor.predict_outage_duration(events)
    battery_health = await predictor.assess_battery_health(metrics, events)
    runtime_prediction = await predictor.predict_runtime(
        current_battery_charge,
        current_load,
        metrics,
        events
    )
    anomalies = await predictor.detect_anomalies(metrics)
    
    return {
        "outage_duration": outage_prediction,
        "battery_health": battery_health,
        "runtime_prediction": runtime_prediction,
        "anomalies": anomalies
    }


@router.get("/predictions/outage")
async def predict_outage_duration():
    """停电时长预测"""
    predictor = get_ml_predictor()
    history_service = await get_history_service()
    
    events = await history_service.get_events(days=90)
    result = await predictor.predict_outage_duration(events)
    
    return result


@router.get("/predictions/battery-health")
async def assess_battery_health():
    """电池健康度评估"""
    predictor = get_ml_predictor()
    history_service = await get_history_service()
    
    events = await history_service.get_events(days=90)
    metrics = await history_service.get_metrics(hours=24 * 90)
    
    result = await predictor.assess_battery_health(metrics, events)
    
    return result


@router.get("/predictions/runtime")
async def predict_runtime():
    """剩余运行时间预测"""
    predictor = get_ml_predictor()
    history_service = await get_history_service()
    
    events = await history_service.get_events(days=30)
    metrics = await history_service.get_metrics(hours=24 * 30)
    
    # 获取当前状态
    current_battery_charge = None
    current_load = None
    
    if metrics:
        latest_metric = metrics[-1]
        current_battery_charge = latest_metric.battery_charge
        current_load = latest_metric.load_percent
    
    result = await predictor.predict_runtime(
        current_battery_charge,
        current_load,
        metrics,
        events
    )
    
    return result


@router.get("/predictions/anomalies")
async def detect_anomalies():
    """异常检测"""
    predictor = get_ml_predictor()
    history_service = await get_history_service()
    
    # 获取最近7天的指标数据用于异常检测
    metrics = await history_service.get_metrics(hours=24 * 7)
    
    result = await predictor.detect_anomalies(metrics)
    
    return result
