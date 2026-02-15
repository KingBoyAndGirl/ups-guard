"""历史记录服务"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from models import Event, Metric, EventType
from utils.retry import async_retry

logger = logging.getLogger(__name__)


class HistoryService:
    """历史记录服务"""
    
    def __init__(self, db):
        self.db = db
    
    async def add_event(self, event_type: EventType, message: str, metadata: Optional[dict] = None, test_mode: str = None):
        """
        添加事件记录（带重试，处理 SQLite 锁定）
        
        Args:
            event_type: 事件类型
            message: 事件消息
            metadata: 元数据
            test_mode: 测试模式 (如果为None，从配置获取)
        """
        # Get test_mode from config if not provided
        if test_mode is None:
            try:
                from config import get_config_manager
                config_manager = await get_config_manager()
                config = await config_manager.get_config()
                test_mode = config.test_mode
            except Exception as e:
                logger.warning(f"Failed to get test_mode from config: {e}, defaulting to 'production'")
                test_mode = 'production'
        
        metadata_str = json.dumps(metadata) if metadata else None
        
        async def _do_insert():
            """执行数据库插入"""
            await self.db.execute(
                "INSERT INTO events (event_type, message, metadata, test_mode) VALUES (?, ?, ?, ?)",
                (event_type.value, message, metadata_str, test_mode)
            )
        
        try:
            # 使用 async_retry 处理 SQLite 锁定等临时错误
            await async_retry(
                _do_insert,
                max_retries=3,
                base_delay=0.5,
                exponential_backoff=True,
                max_delay=2.0,
                retry_exceptions=(Exception,),  # SQLite 锁定、临时错误等
                operation_name=f"Database add_event ({event_type.value})"
            )
        except Exception as e:
            logger.error(f"Failed to add event after retries: {e}")
            # 不抛出异常，避免影响主流程
        

    async def get_events(self, days: int = 7, event_type: Optional[EventType] = None, test_mode: str = None) -> List[Event]:
        """
        获取历史事件
        
        Args:
            days: 查询最近几天的事件
            event_type: 过滤事件类型
            test_mode: 测试模式过滤 (如果为None，从配置获取)
        
        Returns:
            事件列表
        """
        # Get test_mode from config if not provided
        if test_mode is None:
            try:
                from config import get_config_manager
                config_manager = await get_config_manager()
                config = await config_manager.get_config()
                test_mode = config.test_mode
            except Exception as e:
                logger.warning(f"Failed to get test_mode from config: {e}, defaulting to 'production'")
                test_mode = 'production'
        
        # Use UTC time to match SQLite's CURRENT_TIMESTAMP which stores UTC
        from datetime import timezone
        since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        
        if event_type:
            query = """
                SELECT id, event_type, message, timestamp, metadata 
                FROM events 
                WHERE timestamp >= ? AND event_type = ? AND test_mode = ?
                ORDER BY timestamp DESC
            """
            rows = await self.db.fetch_all(query, (since, event_type.value, test_mode))
        else:
            query = """
                SELECT id, event_type, message, timestamp, metadata 
                FROM events 
                WHERE timestamp >= ? AND test_mode = ?
                ORDER BY timestamp DESC
            """
            rows = await self.db.fetch_all(query, (since, test_mode))
        
        events = []
        for row in rows:
            # Parse timestamp from database (UTC stored by SQLite CURRENT_TIMESTAMP)
            timestamp = datetime.fromisoformat(row['timestamp'])
            # Explicitly mark as UTC by adding timezone info, then convert to ISO format with Z suffix
            from datetime import timezone as tz
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=tz.utc)
            
            event = Event(
                id=row['id'],
                event_type=EventType(row['event_type']),
                message=row['message'],
                timestamp=timestamp,
                metadata=json.loads(row['metadata']) if row['metadata'] else None
            )
            events.append(event)
        
        return events
    
    async def add_metric(self, metric: Metric, test_mode: str = None):
        """
        添加指标采样（带重试，处理 SQLite 锁定）
        
        Args:
            metric: 指标数据
            test_mode: 测试模式 (如果为None，从配置获取)
        """
        # Get test_mode from config if not provided
        if test_mode is None:
            try:
                from config import get_config_manager
                config_manager = await get_config_manager()
                config = await config_manager.get_config()
                test_mode = config.test_mode
            except Exception as e:
                logger.warning(f"Failed to get test_mode from config: {e}, defaulting to 'production'")
                test_mode = 'production'
        
        async def _do_insert():
            """执行数据库插入"""
            await self.db.execute(
                """
                INSERT INTO metrics 
                (battery_charge, battery_runtime, input_voltage, output_voltage, load_percent, temperature, test_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    metric.battery_charge,
                    metric.battery_runtime,
                    metric.input_voltage,
                    metric.output_voltage,
                    metric.load_percent,
                    metric.temperature,
                    test_mode
                )
            )
        
        try:
            # 使用 async_retry 处理 SQLite 锁定等临时错误
            await async_retry(
                _do_insert,
                max_retries=3,
                base_delay=0.5,
                exponential_backoff=True,
                max_delay=2.0,
                retry_exceptions=(Exception,),
                operation_name="Database add_metric"
            )
            logger.debug(f"Metric sample recorded (test_mode={test_mode})")
        except Exception as e:
            logger.error(f"Failed to add metric after retries: {e}")
            # 不抛出异常，避免影响主流程
    
    async def get_metrics(self, hours: int = 24, test_mode: str = None) -> List[Metric]:
        """
        获取历史指标
        
        Args:
            hours: 查询最近几小时的指标
            test_mode: 测试模式过滤 (如果为None，从配置获取)
        
        Returns:
            指标列表
        """
        # Get test_mode from config if not provided
        if test_mode is None:
            try:
                from config import get_config_manager
                config_manager = await get_config_manager()
                config = await config_manager.get_config()
                test_mode = config.test_mode
            except Exception as e:
                logger.warning(f"Failed to get test_mode from config: {e}, defaulting to 'production'")
                test_mode = 'production'
        
        # Use UTC time to match SQLite's CURRENT_TIMESTAMP which stores UTC
        from datetime import timezone
        since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
        
        query = """
            SELECT id, timestamp, battery_charge, battery_runtime, 
                   input_voltage, output_voltage, load_percent, temperature
            FROM metrics
            WHERE timestamp >= ? AND test_mode = ?
            ORDER BY timestamp ASC
        """
        
        rows = await self.db.fetch_all(query, (since, test_mode))
        
        metrics = []
        for row in rows:
            # Parse timestamp from database (UTC stored by SQLite CURRENT_TIMESTAMP)
            timestamp = datetime.fromisoformat(row['timestamp'])
            # Explicitly mark as UTC by adding timezone info
            from datetime import timezone as tz
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=tz.utc)
            
            metric = Metric(
                id=row['id'],
                timestamp=timestamp,
                battery_charge=row['battery_charge'],
                battery_runtime=row['battery_runtime'],
                input_voltage=row['input_voltage'],
                output_voltage=row['output_voltage'],
                load_percent=row['load_percent'],
                temperature=row['temperature']
            )
            metrics.append(metric)
        
        return metrics
    
    async def cleanup_old_data(self, retention_days: int):
        """
        清理过期数据
        
        Args:
            retention_days: 保留天数
        
        Returns:
            清理的记录数
        """
        cutoff = datetime.now() - timedelta(days=retention_days)
        
        # 清理事件
        cursor = await self.db.execute(
            "DELETE FROM events WHERE timestamp < ?",
            (cutoff,)
        )
        events_deleted = cursor.rowcount if hasattr(cursor, 'rowcount') else 0
        
        # 清理指标
        cursor = await self.db.execute(
            "DELETE FROM metrics WHERE timestamp < ?",
            (cutoff,)
        )
        metrics_deleted = cursor.rowcount if hasattr(cursor, 'rowcount') else 0
        

        return {
            "events_deleted": events_deleted,
            "metrics_deleted": metrics_deleted
        }

    async def cleanup_all_data(self):
        """
        清空所有历史数据

        Returns:
            清理的记录数
        """
        # 清理所有事件
        cursor = await self.db.execute("DELETE FROM events")
        events_deleted = cursor.rowcount if hasattr(cursor, 'rowcount') else 0

        # 清理所有指标
        cursor = await self.db.execute("DELETE FROM metrics")
        metrics_deleted = cursor.rowcount if hasattr(cursor, 'rowcount') else 0

        # 清理所有电池测试报告
        cursor = await self.db.execute("DELETE FROM battery_test_reports")
        reports_deleted = cursor.rowcount if hasattr(cursor, 'rowcount') else 0

        # 清理所有监控统计
        cursor = await self.db.execute("DELETE FROM monitoring_stats")
        stats_deleted = cursor.rowcount if hasattr(cursor, 'rowcount') else 0

        return {
            "events_deleted": events_deleted,
            "metrics_deleted": metrics_deleted,
            "reports_deleted": reports_deleted,
            "stats_deleted": stats_deleted
        }

    async def upsert_monitoring_stats(
        self,
        date: str,
        monitoring_mode: str,
        event_mode_active: bool,
        communication_count: int,
        avg_response_time_ms: Optional[float],
        min_response_time_ms: Optional[float],
        max_response_time_ms: Optional[float],
        uptime_seconds: int
    ):
        """
        插入或更新监控统计数据（upsert）
        
        Args:
            date: 统计日期 YYYY-MM-DD
            monitoring_mode: 监控模式
            event_mode_active: 事件驱动是否激活
            communication_count: 通信次数
            avg_response_time_ms: 平均响应时间
            min_response_time_ms: 最小响应时间
            max_response_time_ms: 最大响应时间
            uptime_seconds: 运行时长
        """
        try:
            await self.db.execute("""
                INSERT INTO monitoring_stats (
                    date, monitoring_mode, event_mode_active, communication_count,
                    avg_response_time_ms, min_response_time_ms, max_response_time_ms,
                    uptime_seconds, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(date) DO UPDATE SET
                    monitoring_mode = excluded.monitoring_mode,
                    event_mode_active = excluded.event_mode_active,
                    communication_count = excluded.communication_count,
                    avg_response_time_ms = excluded.avg_response_time_ms,
                    min_response_time_ms = excluded.min_response_time_ms,
                    max_response_time_ms = excluded.max_response_time_ms,
                    uptime_seconds = excluded.uptime_seconds,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                date, monitoring_mode, event_mode_active, communication_count,
                avg_response_time_ms, min_response_time_ms, max_response_time_ms,
                uptime_seconds
            ))
            await self.db.commit()
            logger.debug(f"Upserted monitoring stats for {date}: {communication_count} comms")
        except Exception as e:
            logger.error(f"Failed to upsert monitoring stats: {e}", exc_info=True)
            raise

    async def get_monitoring_stats(self, days: int = 30) -> List[dict]:
        """
        获取监控统计历史数据
        
        Args:
            days: 获取最近几天的统计
            
        Returns:
            监控统计列表
        """
        try:
            since = datetime.now() - timedelta(days=days)
            query = """
                SELECT date, monitoring_mode, event_mode_active, communication_count,
                       avg_response_time_ms, min_response_time_ms, max_response_time_ms,
                       uptime_seconds, created_at, updated_at
                FROM monitoring_stats
                WHERE date >= ?
                ORDER BY date DESC
            """
            rows = await self.db.fetch_all(query, (since.date().isoformat(),))
            
            stats = []
            for row in rows:
                stats.append({
                    'date': row[0],
                    'monitoring_mode': row[1],
                    'event_mode_active': bool(row[2]),
                    'communication_count': row[3],
                    'avg_response_time_ms': row[4],
                    'min_response_time_ms': row[5],
                    'max_response_time_ms': row[6],
                    'uptime_seconds': row[7],
                    'created_at': row[8],
                    'updated_at': row[9]
                })
            
            return stats
        except Exception as e:
            logger.error(f"Failed to get monitoring stats: {e}", exc_info=True)
            return []


# 全局历史服务实例
history_service: Optional[HistoryService] = None


async def get_history_service() -> HistoryService:
    """获取历史服务实例"""
    global history_service
    if history_service is None:
        from db.database import get_db
        db = await get_db()
        history_service = HistoryService(db)
    return history_service
