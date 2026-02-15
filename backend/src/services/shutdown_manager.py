"""关机管理器 - 实现安全关机策略"""
import asyncio
import logging
from datetime import datetime
from typing import Optional
from models import EventType
from services.lzc_shutdown import ShutdownInterface
from services.history import get_history_service
from services.notifier import get_notifier_service

logger = logging.getLogger(__name__)


class ShutdownManager:
    """关机管理器"""
    
    def __init__(
        self,
        shutdown_client: ShutdownInterface,
        wait_minutes: int = 5,
        battery_percent: int = 20,
        final_wait_seconds: int = 30,
        estimated_runtime_threshold: int = 3,
        test_mode: str = "production"
    ):
        """
        初始化关机管理器
        
        Args:
            shutdown_client: 关机客户端
            wait_minutes: 停电后等待分钟数
            battery_percent: 最低电量百分比
            final_wait_seconds: 最终等待秒数
            estimated_runtime_threshold: 预计续航阈值（分钟）
            test_mode: 测试模式 - production / dry_run / mock
        """
        self.shutdown_client = shutdown_client
        self.wait_minutes = wait_minutes
        self.battery_percent = battery_percent
        self.final_wait_seconds = final_wait_seconds
        self.estimated_runtime_threshold = estimated_runtime_threshold
        self.test_mode = test_mode
        
        self._shutdown_task: Optional[asyncio.Task] = None
        self._countdown_task: Optional[asyncio.Task] = None
        self._power_lost_time: Optional[datetime] = None
        self._final_countdown_start: Optional[datetime] = None  # 最终倒计时开始时间
        self._is_shutting_down = False
        self._shutdown_cancelled = False
        self._current_ups_data = None
        self._skip_reason: Optional[str] = None  # 跳过等待的原因
        self._cancelled_until_restore = False  # 取消后直到市电恢复才重新计时
        self._current_phase = "idle"  # 当前阶段：idle/waiting/final_countdown/executing_hooks/shutting_down_host/completed

    def on_power_lost(self, ups_data=None):
        """当检测到停电时调用"""
        self._current_ups_data = ups_data

        # 如果用户取消了关机且市电未恢复，不重新开始倒计时
        if self._cancelled_until_restore:
            return

        if self._power_lost_time is None:
            self._power_lost_time = datetime.now()
            self._current_phase = "waiting"
            logger.warning(f"Power lost detected. Shutdown timer started (wait {self.wait_minutes} minutes)")
            
            # 启动关机倒计时任务
            if self._shutdown_task is None or self._shutdown_task.done():
                self._shutdown_task = asyncio.create_task(self._shutdown_countdown())
    
    def on_power_restored(self):
        """当检测到恢复供电时调用"""
        # 清除取消保护标记
        self._cancelled_until_restore = False

        if self._power_lost_time is not None:
            duration = (datetime.now() - self._power_lost_time).total_seconds()

            # 取消关机任务
            self._cancel_shutdown()
            self._power_lost_time = None
            self._current_phase = "idle"
    
    def check_battery_level(self, battery_charge: float) -> bool:
        """
        检查电池电量是否低于阈值
        
        Args:
            battery_charge: 当前电池电量百分比
        
        Returns:
            是否需要立即关机
        """
        if battery_charge is not None and battery_charge <= self.battery_percent:
            logger.warning(f"Battery critically low: {battery_charge}% <= {self.battery_percent}%")
            return True
        return False
    
    def check_runtime_threshold(self, battery_runtime: Optional[int]) -> bool:
        """
        检查预计续航是否低于阈值
        
        Args:
            battery_runtime: 预计续航时间（秒）
        
        Returns:
            是否需要立即关机
        """
        if battery_runtime is not None:
            runtime_minutes = battery_runtime / 60
            if runtime_minutes <= self.estimated_runtime_threshold:
                logger.warning(f"Battery runtime critically low: {runtime_minutes:.1f} min <= {self.estimated_runtime_threshold} min")
                return True
        return False
    
    def _cancel_shutdown(self):
        """取消关机"""
        if self._shutdown_task and not self._shutdown_task.done():
            self._shutdown_cancelled = True
            self._shutdown_task.cancel()

    async def cancel_shutdown(self) -> bool:
        """
        手动取消关机（API 调用）
        
        Returns:
            是否成功取消
        """
        if self._is_shutting_down:
            # 检查当前阶段，确定是否还能取消
            phase = self._current_phase
            if phase == "shutting_down_host":
                logger.warning("Cannot cancel shutdown - host shutdown already initiated")
                return False
            
            self._cancel_shutdown()
            
            # 重置状态
            self._power_lost_time = None
            self._final_countdown_start = None
            self._is_shutting_down = False
            self._current_phase = "idle"

            # 设置保护标记，直到市电恢复才重新开始倒计时
            self._cancelled_until_restore = True

            # 记录事件和阶段信息
            cancel_message = f"用户手动取消关机（在{phase}阶段取消）"
            history_service = await get_history_service()
            await history_service.add_event(
                EventType.SHUTDOWN_CANCELLED,
                cancel_message
            )
            
            # 发送通知
            notifier_service = get_notifier_service()
            if phase == "executing_hooks":
                detail = "关机前置任务执行期间取消。市电恢复后再次断电才会重新开始倒计时。"
            else:
                detail = "用户手动取消了关机操作。市电恢复后再次断电才会重新开始倒计时。"
                
            await notifier_service.notify(
                EventType.SHUTDOWN_CANCELLED,
                "关机已取消",
                detail
            )
            
            return True
        
        logger.warning("No shutdown in progress to cancel")
        return False
    
    async def _shutdown_countdown(self):
        """关机倒计时任务"""
        try:
            self._is_shutting_down = True
            self._shutdown_cancelled = False
            
            # 启动倒计时广播任务（整个等待期间都广播）
            self._countdown_task = asyncio.create_task(self._broadcast_countdown())

            # 等待指定时间或满足其他条件
            wait_seconds = self.wait_minutes * 60

            # 分段等待，以便及时响应取消和检查其他条件
            check_interval = 5  # 每5秒检查一次
            elapsed = 0
            
            while elapsed < wait_seconds:
                await asyncio.sleep(check_interval)
                elapsed += check_interval
                
                if self._shutdown_cancelled:
                    return
                
                # 检查是否需要立即关机
                # 逻辑：续航时间低于阈值时立即关机（不管电量）
                # 电量低只是警告，不会跳过等待期（因为续航时间可能还很长）
                if self._current_ups_data:
                    runtime_low = self.check_runtime_threshold(self._current_ups_data.battery_runtime)
                    
                    if runtime_low:
                        logger.warning("Runtime critically low, skipping wait period")
                        self._skip_reason = "low_runtime"
                        break
            else:
                self._skip_reason = None  # 正常等待完成

            # 二次确认：重新检查市电状态
            await asyncio.sleep(2)  # 短暂等待以获取最新状态
            
            # 如果在这个时间窗口内取消了，直接返回
            if self._shutdown_cancelled:
                return
            
            # 进入30秒最终等待窗口
            logger.warning(f"Initiating shutdown sequence. Final wait: {self.final_wait_seconds} seconds")
            self._final_countdown_start = datetime.now()  # 记录最终倒计时开始时间
            self._current_phase = "final_countdown"

            # 根据触发原因生成不同的消息
            if hasattr(self, '_skip_reason') and self._skip_reason == "low_runtime":
                runtime_min = self._current_ups_data.battery_runtime / 60 if self._current_ups_data.battery_runtime else 0
                shutdown_reason = f"UPS 预计续航时间过短（{runtime_min:.1f} 分钟）"
            else:
                shutdown_reason = f"UPS 电池供电已超过 {self.wait_minutes} 分钟"

            # 记录即将关机事件
            history_service = await get_history_service()
            await history_service.add_event(
                EventType.SHUTDOWN,
                f"{shutdown_reason}，系统将在 {self.final_wait_seconds} 秒后关机"
            )
            
            # 发送通知
            notifier_service = get_notifier_service()
            await notifier_service.notify(
                EventType.SHUTDOWN,
                "系统即将关机",
                f"{shutdown_reason}，系统将在 {self.final_wait_seconds} 秒后关机。"
            )
            
            # 最终等待（每秒检查一次取消状态）
            for remaining in range(self.final_wait_seconds, 0, -1):
                if self._shutdown_cancelled:
                    if self._countdown_task:
                        self._countdown_task.cancel()
                    return
                await asyncio.sleep(1)
            
            if self._countdown_task:
                self._countdown_task.cancel()
            
            if self._shutdown_cancelled:
                return
            
            # 执行 Pre-Shutdown Hooks
            self._current_phase = "executing_hooks"
            try:
                from services.hook_executor import HookExecutor
                from config import get_config_manager
                from api.websocket import broadcast_hook_progress
                
                config_manager = await get_config_manager()
                config = await config_manager.get_config()
                
                if config.pre_shutdown_hooks:
                    executor = HookExecutor(
                        hooks_config=config.pre_shutdown_hooks,
                        default_timeout=120,
                        test_mode=self.test_mode,
                        progress_callback=broadcast_hook_progress,
                        cancellation_callback=lambda: self._shutdown_cancelled
                    )
                    hook_result = await executor.execute_all()

                    # 记录 hook 执行结果到事件
                    history_service = await get_history_service()
                    await history_service.add_event(
                        EventType.SHUTDOWN,
                        f"关机前置任务执行完成：{hook_result['success']}/{hook_result['total']} 成功，"
                        f"{hook_result['failed']} 失败，{hook_result['skipped']} 跳过"
                    )
            except Exception as e:
                logger.error(f"Error executing pre-shutdown hooks: {e}")
                # 继续执行关机，即使 hook 失败
            
            # 执行关机
            self._current_phase = "shutting_down_host"
            if self.test_mode == "dry_run":
                logger.critical("[DRY-RUN] Would execute system shutdown now (skipped in dry-run mode)")
                # Dry-run 模式：不执行实际关机
                self._current_phase = "completed"
            else:
                logger.critical("Executing system shutdown NOW!")
                success = await self.shutdown_client.shutdown()
                
                # 记录关机执行结果
                history_service = await get_history_service()
                notifier_service = get_notifier_service()

                if success:
                    self._current_phase = "completed"
                    # 关机成功通知（注意：如果真的关机了，这条消息可能发不出去）
                    await history_service.add_event(
                        EventType.SHUTDOWN,
                        "系统关机命令已执行"
                    )
                    await notifier_service.notify(
                        EventType.SHUTDOWN,
                        "系统关机中",
                        "关机命令已成功执行，系统正在关闭。"
                    )
                else:
                    logger.error("Failed to execute shutdown command")
                    self._current_phase = "idle"
                    # 关机失败通知
                    await history_service.add_event(
                        EventType.SHUTDOWN,
                        "系统关机命令执行失败"
                    )
                    await notifier_service.notify(
                        EventType.SHUTDOWN,
                        "关机执行失败",
                        "关机命令执行失败，请检查系统状态。"
                    )

        except asyncio.CancelledError:
            self._current_phase = "idle"
            if self._countdown_task:
                self._countdown_task.cancel()
        except Exception as e:
            logger.error(f"Error in shutdown countdown: {e}")
            self._current_phase = "idle"
        finally:
            self._is_shutting_down = False
            self._final_countdown_start = None
            if self._countdown_task:
                try:
                    self._countdown_task.cancel()
                except Exception:
                    pass
    
    async def _broadcast_countdown(self):
        """广播关机倒计时"""
        try:
            while True:
                if self._is_shutting_down:
                    # 使用 get_status 来获取正确的剩余时间
                    status = self.get_status()
                    remaining = status.get("remaining_seconds", 0)

                    # 通过 WebSocket 广播倒计时
                    try:
                        from api.websocket import manager
                        await manager.broadcast({
                            "type": "shutdown_countdown",
                            "data": {
                                "remaining_seconds": remaining,
                                "in_final_countdown": status.get("in_final_countdown", False)
                            }
                        })
                    except Exception as e:
                        logger.debug(f"Failed to broadcast countdown: {e}")
                
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.debug("Countdown broadcast cancelled")
    
    def is_shutting_down(self) -> bool:
        """检查是否正在关机"""
        return self._is_shutting_down
    
    def get_status(self) -> dict:
        """获取关机管理器状态"""
        if self._is_shutting_down:
            # 如果已进入最终倒计时阶段
            if self._final_countdown_start:
                elapsed = (datetime.now() - self._final_countdown_start).total_seconds()
                remaining = max(0, self.final_wait_seconds - elapsed)
                return {
                    "shutting_down": True,
                    "power_lost_time": self._power_lost_time.isoformat() if self._power_lost_time else None,
                    "elapsed_seconds": int(elapsed),
                    "remaining_seconds": int(remaining),
                    "in_final_countdown": True,
                    "phase": self._current_phase
                }
            # 还在等待阶段
            elif self._power_lost_time:
                elapsed = (datetime.now() - self._power_lost_time).total_seconds()
                total = self.wait_minutes * 60 + self.final_wait_seconds
                remaining = max(0, total - elapsed)
                return {
                    "shutting_down": True,
                    "power_lost_time": self._power_lost_time.isoformat(),
                    "elapsed_seconds": int(elapsed),
                    "remaining_seconds": int(remaining),
                    "in_final_countdown": False,
                    "phase": self._current_phase
                }
            else:
                # 立即关机模式（没有倒计时）
                return {
                    "shutting_down": True,
                    "power_lost_time": None,
                    "elapsed_seconds": 0,
                    "remaining_seconds": 0,
                    "in_final_countdown": False,
                    "phase": self._current_phase
                }

        return {
            "shutting_down": False,
            "phase": self._current_phase
        }
    
    async def immediate_shutdown(self) -> bool:
        """
        立即执行完整关机流程（手动触发）
        
        执行顺序：
        1. 执行 pre-shutdown hooks
        2. 关闭所有纳管设备
        3. 关闭本机（宿主机）
        
        Returns:
            是否成功触发关机流程
        """
        if self._is_shutting_down:
            logger.warning("Shutdown already in progress")
            return False
        
        try:
            self._is_shutting_down = True
            self._shutdown_cancelled = False
            self._current_phase = "executing_hooks"
            
            # 执行 Pre-Shutdown Hooks
            try:
                from services.hook_executor import HookExecutor
                from config import get_config_manager
                from api.websocket import broadcast_hook_progress
                
                config_manager = await get_config_manager()
                config = await config_manager.get_config()
                
                if config.pre_shutdown_hooks:
                    executor = HookExecutor(
                        hooks_config=config.pre_shutdown_hooks,
                        default_timeout=120,
                        test_mode=self.test_mode,
                        progress_callback=broadcast_hook_progress,
                        cancellation_callback=lambda: self._shutdown_cancelled
                    )
                    hook_result = await executor.execute_all()

                    # 检查是否被取消
                    if self._shutdown_cancelled:
                        self._current_phase = "idle"
                        return False
                    
                    # 记录 hook 执行结果到事件
                    history_service = await get_history_service()
                    await history_service.add_event(
                        EventType.SHUTDOWN,
                        f"关机前置任务执行完成：{hook_result['success']}/{hook_result['total']} 成功，"
                        f"{hook_result['failed']} 失败，{hook_result['skipped']} 跳过"
                    )
            except Exception as e:
                logger.error(f"Error executing pre-shutdown hooks: {e}")
                # 继续执行关机，即使 hook 失败
            
            # 再次检查是否被取消（在执行关机前）
            if self._shutdown_cancelled:
                self._current_phase = "idle"
                return False
            
            # 执行关机
            self._current_phase = "shutting_down_host"
            if self.test_mode == "dry_run":
                logger.critical("[DRY-RUN] Would execute system shutdown now (skipped in dry-run mode)")
                self._current_phase = "completed"
                return True
            else:
                logger.critical("Executing system shutdown NOW!")
                success = await self.shutdown_client.shutdown()
                
                if success:
                    self._current_phase = "completed"
                    return True
                else:
                    logger.error("Failed to execute shutdown command")
                    self._current_phase = "idle"
                    return False
        
        except Exception as e:
            logger.error(f"Error in immediate shutdown: {e}")
            self._current_phase = "idle"
            return False
        finally:
            self._is_shutting_down = False
            
            # Broadcast final status to frontend
            try:
                from api.websocket import broadcast_shutdown_status
                await broadcast_shutdown_status()
            except Exception as e:
                logger.error(f"Failed to broadcast shutdown status: {e}")
