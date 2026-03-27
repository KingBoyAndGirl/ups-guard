"""测试 UPS 监控器"""
import pytest
import asyncio
from models import UpsStatus, EventType
from services.monitor import UpsMonitor
from services.shutdown_manager import ShutdownManager
from services.history import HistoryService


class TestUpsMonitor:
    """测试 UpsMonitor"""
    
    @pytest.mark.asyncio
    async def test_monitor_initialization(self, mock_nut_client, mock_shutdown_client):
        """测试监控器初始化"""
        shutdown_manager = ShutdownManager(mock_shutdown_client)
        monitor = UpsMonitor(mock_nut_client, shutdown_manager, poll_interval=1)
        
        assert monitor._current_status == UpsStatus.OFFLINE
        assert monitor._running is False
    
    @pytest.mark.asyncio
    async def test_monitor_start_stop(self, mock_nut_client, mock_shutdown_client):
        """测试监控器启动和停止"""
        shutdown_manager = ShutdownManager(mock_shutdown_client)
        monitor = UpsMonitor(mock_nut_client, shutdown_manager, poll_interval=1)
        
        await monitor.start()
        assert monitor._running is True
        await asyncio.sleep(0.5)
        
        await monitor.stop()
        assert monitor._running is False
    
    @pytest.mark.asyncio
    async def test_status_parsing_online(self, mock_nut_client, mock_shutdown_client):
        """测试在线状态解析"""
        shutdown_manager = ShutdownManager(mock_shutdown_client)
        monitor = UpsMonitor(mock_nut_client, shutdown_manager, poll_interval=1)
        
        status = monitor._parse_status("OL")
        assert status == UpsStatus.ONLINE
    
    @pytest.mark.asyncio
    async def test_status_parsing_on_battery(self, mock_nut_client, mock_shutdown_client):
        """测试电池供电状态解析"""
        shutdown_manager = ShutdownManager(mock_shutdown_client)
        monitor = UpsMonitor(mock_nut_client, shutdown_manager, poll_interval=1)
        
        status = monitor._parse_status("OB")
        assert status == UpsStatus.ON_BATTERY
    
    @pytest.mark.asyncio
    async def test_status_parsing_low_battery(self, mock_nut_client, mock_shutdown_client):
        """测试低电量状态解析"""
        shutdown_manager = ShutdownManager(mock_shutdown_client)
        monitor = UpsMonitor(mock_nut_client, shutdown_manager, poll_interval=1)
        
        status = monitor._parse_status("OB LB")
        assert status == UpsStatus.LOW_BATTERY
    
    @pytest.mark.asyncio
    async def test_read_ups_data(self, mock_nut_client, mock_shutdown_client):
        """测试读取 UPS 数据"""
        await mock_nut_client.connect()
        shutdown_manager = ShutdownManager(mock_shutdown_client)
        monitor = UpsMonitor(mock_nut_client, shutdown_manager, poll_interval=1)
        
        data = await monitor._read_ups_data()
        
        assert data is not None
        assert data.status == UpsStatus.ONLINE
        assert data.battery_charge == 100
        assert data.battery_runtime == 3600
        assert data.ups_model == "Mock UPS Model"
    
    @pytest.mark.asyncio
    async def test_status_change_callback(self, mock_nut_client, mock_shutdown_client):
        """测试状态变化回调"""
        shutdown_manager = ShutdownManager(mock_shutdown_client, wait_minutes=10)
        monitor = UpsMonitor(mock_nut_client, shutdown_manager, poll_interval=1)
        
        callback_called = []
        
        async def test_callback(data):
            callback_called.append(data)
        
        monitor.add_status_callback(test_callback)
        
        await monitor.start()
        await asyncio.sleep(2)
        
        # 模拟断电
        mock_nut_client.set_power_lost()
        await asyncio.sleep(2)
        
        await monitor.stop()
        
        assert len(callback_called) > 0
    
    @pytest.mark.asyncio
    async def test_float_parsing(self, mock_nut_client, mock_shutdown_client):
        """测试浮点数解析"""
        shutdown_manager = ShutdownManager(mock_shutdown_client)
        monitor = UpsMonitor(mock_nut_client, shutdown_manager)
        
        assert monitor._parse_float("123.45") == 123.45
        assert monitor._parse_float("invalid") is None
        assert monitor._parse_float(None) is None
    
    @pytest.mark.asyncio
    async def test_int_parsing(self, mock_nut_client, mock_shutdown_client):
        """测试整数解析"""
        shutdown_manager = ShutdownManager(mock_shutdown_client)
        monitor = UpsMonitor(mock_nut_client, shutdown_manager)
        
        assert monitor._parse_int("123") == 123
        assert monitor._parse_int("123.45") == 123
        assert monitor._parse_int("invalid") is None
        assert monitor._parse_int(None) is None
