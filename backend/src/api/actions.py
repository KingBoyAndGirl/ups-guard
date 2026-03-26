"""操作 API"""
import logging
from fastapi import APIRouter, HTTPException
from services.monitor import get_monitor
from services.history import get_history_service
from services.notifier import get_notifier_service
from models import EventType
from config import settings, get_config_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/actions/cancel-shutdown")
async def cancel_shutdown():
    """手动取消关机"""
    logger.info("Received cancel shutdown request")
    monitor = get_monitor()
    
    if monitor is None:
        logger.error("Monitor not initialized")
        raise HTTPException(status_code=503, detail="Monitor not initialized")
    
    logger.info(f"Current shutdown status: {monitor.shutdown_manager.get_status()}")
    success = await monitor.shutdown_manager.cancel_shutdown()
    logger.info(f"Cancel shutdown result: {success}")
    
    if success:
        return {"success": True, "message": "关机已取消"}
    else:
        return {"success": False, "message": "没有正在进行的关机操作"}


@router.post("/actions/shutdown")
async def manual_shutdown():
    """手动触发关机"""
    monitor = get_monitor()

    if monitor is None:
        raise HTTPException(status_code=503, detail="Monitor not initialized")

    # 记录事件
    history_service = await get_history_service()
    await history_service.add_event(
        EventType.SHUTDOWN,
        "用户手动触发关机"
    )

    # 发送通知
    notifier_service = get_notifier_service()
    await notifier_service.notify(
        EventType.SHUTDOWN,
        "系统即将关机",
        "用户手动触发关机操作"
    )

    # 执行完整关机流程（包括 pre-shutdown hooks）
    success = await monitor.shutdown_manager.immediate_shutdown()

    if success:
        return {"success": True, "message": "关机流程已启动"}
    else:
        raise HTTPException(status_code=500, detail="关机流程启动失败")


@router.post("/actions/cleanup-history")
async def cleanup_history():
    """手动清理历史数据（按保留期）"""
    try:
        config_manager = await get_config_manager()
        config = await config_manager.get_config()
        history_service = await get_history_service()
        
        result = await history_service.cleanup_old_data(config.history_retention_days)
        
        return {
            "success": True,
            "message": "历史数据清理完成",
            "events_deleted": result["events_deleted"],
            "metrics_deleted": result["metrics_deleted"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@router.post("/actions/cleanup-all")
async def cleanup_all():
    """清空所有历史数据"""
    try:
        history_service = await get_history_service()

        # 清理所有数据（保留期设为 0 天）
        result = await history_service.cleanup_all_data()

        return {
            "success": True,
            "message": "所有历史数据已清空",
            "events_deleted": result["events_deleted"],
            "metrics_deleted": result["metrics_deleted"],
            "reports_deleted": result["reports_deleted"],
            "stats_deleted": result["stats_deleted"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空失败: {str(e)}")


@router.post("/actions/dry-run-shutdown")
async def dry_run_shutdown():
    """手动触发一次 dry-run 完整关机流程"""
    monitor = get_monitor()

    if monitor is None:
        raise HTTPException(status_code=503, detail="Monitor not initialized")

    # 记录事件
    history_service = await get_history_service()
    await history_service.add_event(
        EventType.SHUTDOWN,
        "用户触发 Dry-Run 关机测试"
    )

    # 执行 dry-run 关机流程
    try:
        # 使用 shutdown manager 的 hook executor 进行 dry-run
        from services.hook_executor import HookExecutor
        
        config_manager = await get_config_manager()
        config = await config_manager.get_config()
        
        # 创建临时 HookExecutor
        executor = HookExecutor(
            config.pre_shutdown_hooks,
            default_timeout=120,
            test_mode="dry_run"
        )
        
        # 执行所有 hook 的 dry-run
        success = await executor.execute_all()
        
        return {
            "success": True,
            "message": "Dry-Run 关机测试完成",
            "hooks_executed": len(config.pre_shutdown_hooks),
            "all_hooks_success": success
        }
    
    except Exception as e:
        logger.error(f"Dry-run shutdown failed: {e}")
        raise HTTPException(status_code=500, detail=f"Dry-Run 失败: {str(e)}")


# Mock 调试 API（仅开发模式）
if settings.mock_mode:
    @router.post("/dev/mock/power-lost")
    async def mock_power_lost():
        """模拟断电"""
        from services.nut_client import MockNutClient
        monitor = get_monitor()
        
        if monitor and isinstance(monitor.nut_client, MockNutClient):
            monitor.nut_client.set_power_lost()
            # 立即触发状态更新
            await monitor.force_update()
            return {"success": True, "message": "已模拟断电"}
        
        raise HTTPException(status_code=400, detail="Not in mock mode or monitor not initialized")
    
    @router.post("/dev/mock/power-restored")
    async def mock_power_restored():
        """模拟恢复供电"""
        from services.nut_client import MockNutClient
        monitor = get_monitor()
        
        if monitor and isinstance(monitor.nut_client, MockNutClient):
            monitor.nut_client.set_power_restored()
            # 立即触发状态更新
            await monitor.force_update()
            return {"success": True, "message": "已模拟恢复供电"}
        
        raise HTTPException(status_code=400, detail="Not in mock mode or monitor not initialized")
    
    @router.post("/dev/mock/low-battery")
    async def mock_low_battery(charge: int = 15):
        """模拟低电量"""
        from services.nut_client import MockNutClient
        monitor = get_monitor()
        
        if monitor and isinstance(monitor.nut_client, MockNutClient):
            monitor.nut_client.set_low_battery(charge)
            # 立即触发状态更新
            await monitor.force_update()
            return {"success": True, "message": f"已模拟低电量 ({charge}%)"}
        
        raise HTTPException(status_code=400, detail="Not in mock mode or monitor not initialized")
