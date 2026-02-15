"""通知服务"""
import asyncio
import logging
from typing import List, Set, Dict, Tuple, Optional
from datetime import datetime
from models import EventType, NotifierConfig
from plugins.registry import get_registry

logger = logging.getLogger(__name__)


class NotifierService:
    """通知服务"""
    
    def __init__(self):
        self.registry = get_registry()
        self._notifiers = []
        self._enabled_events: Set[str] = set()  # 启用的事件类型
        self._notification_enabled: bool = True  # 通知总开关
        self._channel_errors: Dict[str, str] = {}  # 渠道错误状态 {渠道ID: 错误信息}

    def configure(self, channels: List[NotifierConfig], notify_events: List[str] = None, notification_enabled: bool = True):
        """
        配置通知渠道
        
        Args:
            channels: 通知渠道配置列表
            notify_events: 启用通知的事件类型列表
            notification_enabled: 通知总开关
        """
        self._notifiers = []
        self._enabled_events = set(notify_events) if notify_events else set()
        self._notification_enabled = notification_enabled

        # 保留当前存在渠道的错误状态，删除已不存在的渠道错误
        current_channel_ids = set()

        for index, channel_config in enumerate(channels):
            # 使用渠道的 id 字段作为唯一标识符
            channel_id = channel_config.id or f"legacy_{index}"
            current_channel_ids.add(channel_id)

            if not channel_config.enabled:
                # # 禁用的渠道也清除错误状态
                # if channel_id in self._channel_errors:
                #     del self._channel_errors[channel_id]
                continue
            
            try:
                notifier = self.registry.create_instance(
                    channel_config.plugin_id,
                    channel_config.config
                )
                self._notifiers.append({
                    "index": index,
                    "channel_id": channel_id,
                    "name": channel_config.name,
                    "plugin_id": channel_config.plugin_id,
                    "notifier": notifier
                })
                # 成功创建时清除该渠道的错误状态
                if channel_id in self._channel_errors:
                    del self._channel_errors[channel_id]
            except Exception as e:
                logger.error(f"Failed to configure notifier {channel_config.name}: {e}")
                self._channel_errors[channel_id] = str(e)

        # 清除已删除渠道的错误状态
        self._channel_errors = {k: v for k, v in self._channel_errors.items() if k in current_channel_ids}

        status = "enabled" if notification_enabled else "disabled"
    
    async def _send_with_retry(self, notifier_info: dict, title: str, content: str, 
                               level: str, timestamp: str, max_retries: int = 2) -> Tuple[bool, Optional[str]]:
        """带重试的通知发送
        
        使用线性退避策略（1s, 2s），适合网络请求场景，避免洪泛第三方服务。
        max_retries=2 表示：1次初始尝试 + 最多2次重试 = 最多3次尝试
        """
        last_error = None
        
        # 初始尝试 + max_retries 次重试 = max_retries + 1 次总尝试
        for attempt in range(1, max_retries + 2):
            try:
                success, error_msg = await notifier_info["notifier"].send(title, content, level, timestamp)
                if success:
                    if attempt > 1:
                        logger.info(
                            f"Notification sent via {notifier_info['name']} "
                            f"after {attempt} attempts"
                        )
                    return True, None
                last_error = error_msg
            except Exception as e:
                last_error = str(e)
            
            if attempt <= max_retries:
                # 线性退避：attempt=1→1s, attempt=2→2s, attempt=3→3s...，上限5s
                delay = min(1.0 * attempt, 5.0)
                logger.warning(
                    f"Notification via {notifier_info['name']} failed "
                    f"(attempt {attempt}/{max_retries + 1}), retrying in {delay:.0f}s: {last_error}"
                )
                await asyncio.sleep(delay)
        
        return False, last_error

    def _format_diagnostic_info(self, metadata: dict) -> str:
        """
        格式化诊断信息
        
        Args:
            metadata: 包含 UPS 状态快照的元数据字典
            
        Returns:
            格式化的诊断信息字符串
        """
        if not metadata:
            return ""
        
        lines = []
        
        # UPS 状态翻译
        status_map = {
            "ONLINE": "在线供电 (市电)",
            "ON_BATTERY": "电池供电",
            "LOW_BATTERY": "低电量",
            "SHUTTING_DOWN": "关机中",
            "POWER_OFF": "关闭",
            "OFFLINE": "离线"
        }
        
        # 添加触发原因（如果有）
        if metadata.get("trigger_reason"):
            lines.append(f"  触发原因: {metadata['trigger_reason']}")
        
        # 添加 UPS 状态
        if metadata.get("ups_status"):
            status_text = status_map.get(metadata["ups_status"], metadata["ups_status"])
            lines.append(f"  UPS 状态: {status_text}")
        
        # 添加电池电量
        if metadata.get("battery_charge") is not None:
            lines.append(f"  当前电量: {metadata['battery_charge']}%")
        
        # 添加剩余续航
        if metadata.get("battery_runtime") is not None:
            runtime_seconds = metadata["battery_runtime"]
            runtime_minutes = runtime_seconds // 60
            lines.append(f"  剩余续航: {runtime_seconds} 秒 (约 {runtime_minutes} 分钟)")
        
        # 添加输入电压
        if metadata.get("input_voltage") is not None:
            voltage = metadata["input_voltage"]
            voltage_status = "市电中断" if voltage == 0 else "正常"
            lines.append(f"  输入电压: {voltage}V ({voltage_status})")
        
        # 添加负载百分比
        if metadata.get("load_percent") is not None:
            lines.append(f"  负载: {metadata['load_percent']}%")
        
        # 添加断电持续时间（如果有）
        if metadata.get("power_lost_duration") is not None:
            duration = metadata["power_lost_duration"]
            lines.append(f"  断电时长: {duration} 秒")
        
        return "\n".join(lines)

    async def notify(self, event_type: EventType, title: str, content: str, level: str = None, metadata: dict = None):
        """
        发送通知到所有已配置的渠道
        
        Args:
            event_type: 事件类型
            title: 标题
            content: 内容
            level: 通知级别 (可选，如果不提供则根据事件类型自动确定)
            metadata: 元数据字典 (可选，用于 error/warning 级别的诊断信息)
        """
        # 检查通知总开关
        if not self._notification_enabled:
            logger.debug("Notifications disabled globally, skipping notification")
            return

        if not self._notifiers:
            logger.debug("No notifiers configured, skipping notification")
            return
        
        # 检查事件类型是否启用
        event_name = event_type.value if hasattr(event_type, 'value') else str(event_type)
        if self._enabled_events and event_name not in self._enabled_events:
            logger.debug(f"Event type {event_name} not in enabled events, skipping notification")
            return

        # 根据事件类型确定级别（如果没有显式提供）
        if level is None:
            level_map = {
                EventType.POWER_LOST: "warning",
                EventType.LOW_BATTERY: "error",
                EventType.SHUTDOWN: "error",
                EventType.POWER_RESTORED: "info",
                EventType.STARTUP: "info",
                EventType.SHUTDOWN_CANCELLED: "info",
                # 设备操作事件
                EventType.DEVICE_SHUTDOWN: "warning",
                EventType.DEVICE_WAKE: "info",
                EventType.DEVICE_REBOOT: "warning",
                EventType.DEVICE_SLEEP: "info",
                EventType.DEVICE_HIBERNATE: "info",
                EventType.DEVICE_TEST_CONNECTION: "info",
                # NUT 连接事件
                EventType.NUT_DISCONNECTED: "warning",
                EventType.NUT_RECONNECTED: "info",
                # 诊断事件 - 后端服务
                EventType.BACKEND_ERROR: "error",
                EventType.BACKEND_RESTORED: "info",
                # 诊断事件 - NUT 服务器
                EventType.NUT_SERVER_DISCONNECTED: "error",
                EventType.NUT_SERVER_CONNECTED: "info",
                # 诊断事件 - UPS 驱动
                EventType.UPS_DRIVER_ERROR: "error",
                EventType.UPS_DRIVER_DUMMY: "warning",
                EventType.UPS_DRIVER_CONNECTED: "info",
                # UPS 参数配置事件
                EventType.UPS_PARAM_CHANGED: "info",
                # 电池维护事件
                EventType.BATTERY_REPLACED: "info",
                # 兼容旧事件
                EventType.CONNECTION_ISSUE: "warning",
                EventType.CONNECTION_RESTORED: "info",
            }
            level = level_map.get(event_type, "info")
        
        # 为 error 和 warning 级别附加诊断信息
        if metadata and level in ("error", "warning"):
            diag_info = self._format_diagnostic_info(metadata)
            if diag_info:
                content = f"{content}\n\n📋 诊断信息:\n{diag_info}"
        
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        

        # 并发发送到所有渠道
        for notifier_info in self._notifiers:
            channel_id = notifier_info['channel_id']
            channel_name = notifier_info['name']
            try:
                success, error_msg = await self._send_with_retry(notifier_info, title, content, level, timestamp)
                if success:
                    # 成功时清除错误状态
                    if channel_id in self._channel_errors:
                        del self._channel_errors[channel_id]
                else:
                    error_detail = error_msg or "未知错误"
                    logger.warning(f"Failed to send notification via {channel_name}: {error_detail}")
                    # 保存错误状态（使用唯一标识符）
                    self._channel_errors[channel_id] = error_detail
                    # 记录到事件日志
                    await self._record_notification_failure(channel_name, error_detail)
            except Exception as e:
                error_detail = str(e)
                logger.error(f"Error sending notification via {channel_name}: {error_detail}")
                # 保存错误状态（使用唯一标识符）
                self._channel_errors[channel_id] = error_detail
                # 记录到事件日志
                await self._record_notification_failure(channel_name, error_detail)

    async def _record_notification_failure(self, channel_name: str, error: str):
        """记录通知发送失败到事件日志"""
        try:
            from services.history import get_history_service
            history_service = await get_history_service()
            await history_service.add_event(
                EventType.STARTUP,  # 使用 STARTUP 类型作为系统事件
                f"通知发送失败 [{channel_name}]: {error}",
                {"channel": channel_name, "error": error, "type": "notification_error"}
            )
        except Exception as e:
            logger.error(f"Failed to record notification failure: {e}")

    async def test_notifier(self, plugin_id: str, config: dict) -> bool:
        """
        测试通知渠道配置
        
        Args:
            plugin_id: 插件 ID
            config: 配置
        
        Returns:
            测试是否成功
        """
        try:
            notifier = self.registry.create_instance(plugin_id, config)
            success, error_msg = await notifier.test()
            return success
        except Exception as e:
            logger.error(f"Error testing notifier {plugin_id}: {e}")
            return False
    
    def list_available_plugins(self):
        """列出所有可用的通知插件"""
        return self.registry.list_plugins()

    def get_channel_errors(self) -> Dict[str, str]:
        """获取所有渠道的错误状态"""
        return self._channel_errors.copy()

    def clear_channel_error(self, channel_name: str):
        """清除指定渠道的错误状态"""
        if channel_name in self._channel_errors:
            del self._channel_errors[channel_name]


# 全局通知服务实例
notifier_service = NotifierService()


def get_notifier_service() -> NotifierService:
    """获取通知服务实例"""
    return notifier_service
