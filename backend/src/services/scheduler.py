"""设备定时任务调度器"""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ScheduleAction(str, Enum):
    """定时操作类型"""
    SHUTDOWN = "shutdown"
    WAKE = "wake"
    REBOOT = "reboot"
    SLEEP = "sleep"
    HIBERNATE = "hibernate"


class ScheduleRepeat(str, Enum):
    """重复类型"""
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass
class ScheduledTask:
    """定时任务"""
    schedule_id: str
    device_index: int
    device_name: str
    action: ScheduleAction
    scheduled_time: datetime
    repeat: ScheduleRepeat
    created_at: datetime
    enabled: bool = True
    last_executed: Optional[datetime] = None
    next_execution: Optional[datetime] = None


class DeviceScheduler:
    """设备定时任务调度器"""
    
    def __init__(self):
        self._schedules: Dict[str, ScheduledTask] = {}
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("Scheduler is already running")
            return
        
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self):
        """停止调度器"""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
            self._scheduler_task = None

    async def add_schedule(
        self,
        device_index: int,
        device_name: str,
        action: str,
        scheduled_time: datetime,
        repeat: str = "once"
    ) -> str:
        """
        添加定时任务
        
        Args:
            device_index: 设备索引
            device_name: 设备名称
            action: 操作类型
            scheduled_time: 计划执行时间
            repeat: 重复类型
        
        Returns:
            schedule_id: 任务ID
        """
        try:
            schedule_action = ScheduleAction(action)
            schedule_repeat = ScheduleRepeat(repeat)
        except ValueError as e:
            raise ValueError(f"Invalid action or repeat type: {e}")
        
        schedule_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Calculate next execution time
        next_execution = scheduled_time
        if next_execution <= now:
            if schedule_repeat == ScheduleRepeat.ONCE:
                raise ValueError("Scheduled time must be in the future for one-time tasks")
            else:
                # For repeating tasks, calculate next occurrence
                next_execution = self._calculate_next_execution(
                    scheduled_time, schedule_repeat, now
                )
        
        task = ScheduledTask(
            schedule_id=schedule_id,
            device_index=device_index,
            device_name=device_name,
            action=schedule_action,
            scheduled_time=scheduled_time,
            repeat=schedule_repeat,
            created_at=now,
            enabled=True,
            last_executed=None,
            next_execution=next_execution
        )
        
        self._schedules[schedule_id] = task

        return schedule_id
    
    async def remove_schedule(self, schedule_id: str) -> bool:
        """
        移除定时任务
        
        Args:
            schedule_id: 任务ID
        
        Returns:
            是否成功移除
        """
        if schedule_id in self._schedules:
            task = self._schedules.pop(schedule_id)
            return True
        return False
    
    async def get_schedules(self, device_index: Optional[int] = None) -> List[Dict]:
        """
        获取定时任务列表
        
        Args:
            device_index: 可选，只获取指定设备的任务
        
        Returns:
            任务列表
        """
        schedules = []
        for task in self._schedules.values():
            if device_index is None or task.device_index == device_index:
                task_dict = asdict(task)
                # Convert datetime to ISO string
                task_dict['scheduled_time'] = task.scheduled_time.isoformat()
                task_dict['created_at'] = task.created_at.isoformat()
                if task.last_executed:
                    task_dict['last_executed'] = task.last_executed.isoformat()
                if task.next_execution:
                    task_dict['next_execution'] = task.next_execution.isoformat()
                schedules.append(task_dict)
        
        # Sort by next execution time
        schedules.sort(key=lambda x: x.get('next_execution', '9999-12-31'))
        return schedules
    
    async def _scheduler_loop(self):
        """调度循环，每分钟检查一次是否有到期任务"""

        while self._running:
            try:
                await self._check_and_execute_tasks()
                # Sleep for 30 seconds before next check
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(30)
        

    async def _check_and_execute_tasks(self):
        """检查并执行到期的任务"""
        now = datetime.now()
        tasks_to_execute = []
        
        for schedule_id, task in self._schedules.items():
            if not task.enabled:
                continue
            
            if task.next_execution and task.next_execution <= now:
                tasks_to_execute.append((schedule_id, task))
        
        for schedule_id, task in tasks_to_execute:
            try:
                await self._execute_task(task)
                
                # Update task
                task.last_executed = now
                
                # Calculate next execution or remove if one-time
                if task.repeat == ScheduleRepeat.ONCE:
                    self._schedules.pop(schedule_id, None)
                else:
                    task.next_execution = self._calculate_next_execution(
                        task.scheduled_time, task.repeat, now
                    )

            
            except Exception as e:
                logger.error(f"Failed to execute scheduled task {schedule_id}: {e}")
                # Keep the task in schedule for retry
    
    async def _execute_task(self, task: ScheduledTask):
        """执行定时任务"""

        # Import here to avoid circular dependency
        from api.devices import (
            shutdown_device, wake_device, reboot_device,
            sleep_device, hibernate_device
        )
        
        try:
            # Call the appropriate API endpoint
            if task.action == ScheduleAction.SHUTDOWN:
                result = await shutdown_device(task.device_index)
            elif task.action == ScheduleAction.WAKE:
                result = await wake_device(task.device_index)
            elif task.action == ScheduleAction.REBOOT:
                result = await reboot_device(task.device_index)
            elif task.action == ScheduleAction.SLEEP:
                result = await sleep_device(task.device_index)
            elif task.action == ScheduleAction.HIBERNATE:
                result = await hibernate_device(task.device_index)
            else:
                logger.error(f"Unknown action: {task.action}")
                return
            
            if not result.get("success"):
                logger.warning(
                    f"Scheduled task failed: {task.device_name} {task.action} - "
                    f"{result.get('message', 'Unknown error')}"
                )
        
        except Exception as e:
            logger.error(
                f"Error executing scheduled task {task.device_name} {task.action}: {e}"
            )
    
    def _calculate_next_execution(
        self,
        scheduled_time: datetime,
        repeat: ScheduleRepeat,
        from_time: datetime
    ) -> datetime:
        """计算下次执行时间"""
        if repeat == ScheduleRepeat.DAILY:
            # Same time tomorrow
            next_time = scheduled_time.replace(
                year=from_time.year,
                month=from_time.month,
                day=from_time.day
            )
            if next_time <= from_time:
                next_time += timedelta(days=1)
            return next_time
        
        elif repeat == ScheduleRepeat.WEEKLY:
            # Same day and time next week
            next_time = scheduled_time.replace(
                year=from_time.year,
                month=from_time.month,
                day=from_time.day
            )
            # Find the next occurrence of the same weekday
            days_ahead = (scheduled_time.weekday() - from_time.weekday()) % 7
            if days_ahead == 0 and next_time <= from_time:
                days_ahead = 7
            next_time = from_time + timedelta(days=days_ahead)
            next_time = next_time.replace(
                hour=scheduled_time.hour,
                minute=scheduled_time.minute,
                second=scheduled_time.second
            )
            return next_time
        
        else:
            # ONCE - should not be called
            return scheduled_time


# Global scheduler instance
_scheduler: Optional[DeviceScheduler] = None


def get_scheduler() -> DeviceScheduler:
    """获取调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = DeviceScheduler()
    return _scheduler
