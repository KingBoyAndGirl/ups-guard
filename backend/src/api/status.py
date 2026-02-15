"""状态 API"""
from fastapi import APIRouter, HTTPException
from services.monitor import get_monitor
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status")
async def get_status():
    """获取 UPS 实时状态"""
    monitor = get_monitor()
    
    if monitor is None:
        raise HTTPException(status_code=503, detail="Monitor not initialized")
    
    data = monitor.get_current_data()
    
    if data is None:
        raise HTTPException(status_code=503, detail="UPS data not available")
    
    # 获取关机状态
    shutdown_status = monitor.shutdown_manager.get_status()
    
    # 使用 Pydantic 的 model_dump() 自动序列化所有字段（包括 Phase 1-4 新增字段）
    response = data.model_dump(mode='json')
    response["shutdown"] = shutdown_status
    

    return response
