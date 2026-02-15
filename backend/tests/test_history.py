"""测试历史记录服务"""
import pytest
import asyncio
from datetime import datetime, timedelta
from models import EventType, Metric
from services.history import HistoryService


class TestHistoryService:
    """测试 HistoryService"""
    
    @pytest.mark.asyncio
    async def test_add_event(self, temp_db):
        """测试添加事件"""
        service = HistoryService(temp_db)
        
        await service.add_event(
            EventType.POWER_LOST,
            "测试断电事件",
            metadata={"voltage": 220}
        )
        
        # 验证事件已添加
        cursor = await temp_db.execute("SELECT * FROM events")
        rows = await cursor.fetchall()
        
        assert len(rows) == 1
        assert rows[0]["event_type"] == "POWER_LOST"
        assert rows[0]["message"] == "测试断电事件"
    
    @pytest.mark.asyncio
    async def test_get_events(self, temp_db):
        """测试获取事件列表"""
        service = HistoryService(temp_db)
        
        # 添加多个事件
        await service.add_event(EventType.POWER_LOST, "断电1")
        await service.add_event(EventType.POWER_RESTORED, "恢复供电1")
        await service.add_event(EventType.LOW_BATTERY, "低电量1")
        
        # 获取事件
        events = await service.get_events(days=7)
        
        assert len(events) == 3
        # 验证事件类型（不验证顺序，因为时间戳可能相同）
        event_types = {e.event_type for e in events}
        assert EventType.POWER_LOST in event_types
        assert EventType.POWER_RESTORED in event_types
        assert EventType.LOW_BATTERY in event_types
    
    @pytest.mark.asyncio
    async def test_get_events_by_type(self, temp_db):
        """测试按类型过滤事件"""
        service = HistoryService(temp_db)
        
        await service.add_event(EventType.POWER_LOST, "断电1")
        await service.add_event(EventType.POWER_RESTORED, "恢复供电1")
        await service.add_event(EventType.POWER_LOST, "断电2")
        
        # 只获取 POWER_LOST 事件
        events = await service.get_events(days=7, event_type=EventType.POWER_LOST)
        
        assert len(events) == 2
        assert all(e.event_type == EventType.POWER_LOST for e in events)
    
    @pytest.mark.asyncio
    async def test_add_metric(self, temp_db):
        """测试添加指标采样"""
        service = HistoryService(temp_db)
        
        metric = Metric(
            battery_charge=85.5,
            battery_runtime=1800,
            input_voltage=220.0,
            output_voltage=220.0,
            load_percent=45.0,
            temperature=25.5
        )
        
        await service.add_metric(metric)
        
        # 验证指标已添加
        cursor = await temp_db.execute("SELECT * FROM metrics")
        rows = await cursor.fetchall()
        
        assert len(rows) == 1
        assert rows[0]["battery_charge"] == 85.5
        assert rows[0]["battery_runtime"] == 1800
        assert rows[0]["load_percent"] == 45.0
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, temp_db):
        """测试获取指标列表"""
        service = HistoryService(temp_db)
        
        # 添加多个指标
        for i in range(5):
            metric = Metric(
                battery_charge=90 - i * 5,
                battery_runtime=1800 - i * 100,
                input_voltage=220.0,
                output_voltage=220.0,
                load_percent=50.0,
                temperature=25.0
            )
            await service.add_metric(metric)
        
        # 获取指标
        metrics = await service.get_metrics(hours=24)
        
        assert len(metrics) == 5
        # 验证指标数据（不验证顺序）
        charges = [m.battery_charge for m in metrics]
        assert 90.0 in charges
        assert 70.0 in charges
    
    @pytest.mark.asyncio
    async def test_cleanup_old_data(self, temp_db):
        """测试清理过期数据"""
        service = HistoryService(temp_db)
        
        # 添加新事件
        await service.add_event(EventType.POWER_LOST, "最近事件")
        
        # 手动添加旧事件（10天前）
        old_time = (datetime.now() - timedelta(days=10)).isoformat()
        await temp_db.execute(
            "INSERT INTO events (event_type, message, timestamp) VALUES (?, ?, ?)",
            ("POWER_LOST", "旧事件", old_time)
        )
        await temp_db.commit()
        
        # 添加新指标
        await service.add_metric(Metric(battery_charge=90.0))
        
        # 手动添加旧指标（10天前）
        await temp_db.execute(
            "INSERT INTO metrics (timestamp, battery_charge) VALUES (?, ?)",
            (old_time, 50.0)
        )
        await temp_db.commit()
        
        # 清理 7 天前的数据
        result = await service.cleanup_old_data(retention_days=7)
        
        # 验证旧数据已删除
        events = await service.get_events(days=30)
        assert len(events) == 1
        assert events[0].message == "最近事件"
        
        metrics = await service.get_metrics(hours=24 * 30)
        assert len(metrics) == 1
        assert metrics[0].battery_charge == 90.0
        
        # 验证返回的统计信息
        assert result["events_deleted"] >= 1
        assert result["metrics_deleted"] >= 1
    
    @pytest.mark.asyncio
    async def test_event_with_metadata(self, temp_db):
        """测试带元数据的事件"""
        service = HistoryService(temp_db)
        
        metadata = {
            "battery_charge": 85,
            "runtime": 1800,
            "reason": "low_battery"
        }
        
        await service.add_event(
            EventType.SHUTDOWN,
            "系统关机",
            metadata=metadata
        )
        
        events = await service.get_events(days=1)
        
        assert len(events) == 1
        assert events[0].metadata is not None
        assert events[0].metadata["battery_charge"] == 85
        assert events[0].metadata["reason"] == "low_battery"
