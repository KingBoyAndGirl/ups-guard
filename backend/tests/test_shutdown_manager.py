"""测试关机管理器"""
import pytest
import asyncio
from datetime import datetime
from services.shutdown_manager import ShutdownManager
from models import UpsData, UpsStatus


class TestShutdownManager:
    """测试 ShutdownManager"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_shutdown_client):
        """测试初始化"""
        manager = ShutdownManager(
            mock_shutdown_client,
            wait_minutes=5,
            battery_percent=20,
            final_wait_seconds=30,
            estimated_runtime_threshold=3
        )
        
        assert manager.wait_minutes == 5
        assert manager.battery_percent == 20
        assert manager.final_wait_seconds == 30
        assert manager.estimated_runtime_threshold == 3
        assert manager._is_shutting_down is False
    
    @pytest.mark.asyncio
    async def test_check_battery_level_normal(self, mock_shutdown_client):
        """测试电池电量正常"""
        manager = ShutdownManager(mock_shutdown_client, battery_percent=20)
        
        assert manager.check_battery_level(50) is False
        assert manager.check_battery_level(21) is False
    
    @pytest.mark.asyncio
    async def test_check_battery_level_low(self, mock_shutdown_client):
        """测试电池电量过低"""
        manager = ShutdownManager(mock_shutdown_client, battery_percent=20)
        
        assert manager.check_battery_level(20) is True
        assert manager.check_battery_level(15) is True
        assert manager.check_battery_level(5) is True
    
    @pytest.mark.asyncio
    async def test_check_runtime_threshold_normal(self, mock_shutdown_client):
        """测试续航时间正常"""
        manager = ShutdownManager(mock_shutdown_client, estimated_runtime_threshold=3)
        
        # 5 分钟 = 300 秒
        assert manager.check_runtime_threshold(300) is False
        # 10 分钟 = 600 秒
        assert manager.check_runtime_threshold(600) is False
    
    @pytest.mark.asyncio
    async def test_check_runtime_threshold_low(self, mock_shutdown_client):
        """测试续航时间过低"""
        manager = ShutdownManager(mock_shutdown_client, estimated_runtime_threshold=3)
        
        # 3 分钟 = 180 秒
        assert manager.check_runtime_threshold(180) is True
        # 2 分钟 = 120 秒
        assert manager.check_runtime_threshold(120) is True
        # 1 分钟 = 60 秒
        assert manager.check_runtime_threshold(60) is True
    
    @pytest.mark.asyncio
    async def test_on_power_lost(self, mock_shutdown_client):
        """测试检测到断电"""
        manager = ShutdownManager(mock_shutdown_client, wait_minutes=10)
        
        ups_data = UpsData(
            status=UpsStatus.ON_BATTERY,
            battery_charge=80,
            battery_runtime=1800
        )
        
        manager.on_power_lost(ups_data)
        
        assert manager._power_lost_time is not None
        assert isinstance(manager._power_lost_time, datetime)
        
        # 等待一小段时间确保任务启动
        await asyncio.sleep(0.1)
        assert manager._is_shutting_down is True
    
    @pytest.mark.asyncio
    async def test_on_power_restored(self, mock_shutdown_client):
        """测试检测到恢复供电"""
        manager = ShutdownManager(mock_shutdown_client, wait_minutes=10)
        
        ups_data = UpsData(
            status=UpsStatus.ON_BATTERY,
            battery_charge=80,
            battery_runtime=1800
        )
        
        manager.on_power_lost(ups_data)
        await asyncio.sleep(0.1)
        
        manager.on_power_restored()
        
        assert manager._power_lost_time is None
    
    @pytest.mark.asyncio
    async def test_cancel_shutdown(self, mock_shutdown_client, monkeypatch):
        """测试取消关机"""
        # Mock history and notifier services to avoid database dependency
        async def mock_get_history():
            class MockHistory:
                async def add_event(self, *args, **kwargs):
                    pass
            return MockHistory()
        
        def mock_get_notifier():
            class MockNotifier:
                async def notify(self, *args, **kwargs):
                    pass
            return MockNotifier()
        
        monkeypatch.setattr("services.shutdown_manager.get_history_service", mock_get_history)
        monkeypatch.setattr("services.shutdown_manager.get_notifier_service", mock_get_notifier)
        
        manager = ShutdownManager(mock_shutdown_client, wait_minutes=10)
        
        # 启动关机倒计时
        ups_data = UpsData(
            status=UpsStatus.ON_BATTERY,
            battery_charge=80,
            battery_runtime=1800
        )
        manager.on_power_lost(ups_data)
        await asyncio.sleep(0.1)
        
        assert manager._is_shutting_down is True
        
        # 取消关机
        success = await manager.cancel_shutdown()
        
        assert success is True
        await asyncio.sleep(0.5)
        assert manager._is_shutting_down is False
    
    @pytest.mark.asyncio
    async def test_get_status_shutting_down(self, mock_shutdown_client):
        """测试获取关机状态"""
        manager = ShutdownManager(
            mock_shutdown_client,
            wait_minutes=1,
            final_wait_seconds=5
        )
        
        ups_data = UpsData(
            status=UpsStatus.ON_BATTERY,
            battery_charge=80,
            battery_runtime=1800
        )
        
        manager.on_power_lost(ups_data)
        await asyncio.sleep(0.1)
        
        status = manager.get_status()
        
        assert status["shutting_down"] is True
        assert "power_lost_time" in status
        assert "elapsed_seconds" in status
        assert "remaining_seconds" in status
    
    @pytest.mark.asyncio
    async def test_get_status_not_shutting_down(self, mock_shutdown_client):
        """测试获取非关机状态"""
        manager = ShutdownManager(mock_shutdown_client)
        
        status = manager.get_status()
        
        assert status["shutting_down"] is False
    
    @pytest.mark.asyncio
    async def test_mock_shutdown_not_executed(self, mock_shutdown_client, monkeypatch):
        """测试 Mock 模式下不会真正关机"""
        # Mock history and notifier services to avoid database dependency
        async def mock_get_history():
            class MockHistory:
                async def add_event(self, *args, **kwargs):
                    pass
            return MockHistory()
        
        def mock_get_notifier():
            class MockNotifier:
                async def notify(self, *args, **kwargs):
                    pass
            return MockNotifier()
        
        monkeypatch.setattr("services.shutdown_manager.get_history_service", mock_get_history)
        monkeypatch.setattr("services.shutdown_manager.get_notifier_service", mock_get_notifier)
        
        manager = ShutdownManager(
            mock_shutdown_client,
            wait_minutes=0,  # 立即触发
            final_wait_seconds=3
        )
        
        ups_data = UpsData(
            status=UpsStatus.ON_BATTERY,
            battery_charge=10,
            battery_runtime=60
        )
        
        manager.on_power_lost(ups_data)
        
        # 等待关机流程完成
        await asyncio.sleep(6)
        
        # 验证关机已被调用，但 Mock 模式不会真正关机
        assert mock_shutdown_client.shutdown_called is True
        
        # 清理
        if manager._is_shutting_down:
            await manager.cancel_shutdown()
    
    @pytest.mark.asyncio
    async def test_get_status_with_phase(self, mock_shutdown_client):
        """测试状态包含 phase 字段"""
        manager = ShutdownManager(mock_shutdown_client)
        
        # 初始状态
        status = manager.get_status()
        assert "phase" in status
        assert status["phase"] == "idle"
        
        # 启动关机后
        ups_data = UpsData(
            status=UpsStatus.ON_BATTERY,
            battery_charge=80,
            battery_runtime=1800
        )
        manager.on_power_lost(ups_data)
        await asyncio.sleep(0.1)
        
        status = manager.get_status()
        assert "phase" in status
        assert status["phase"] in ["waiting", "final_countdown", "executing_hooks", "shutting_down_host", "completed"]
    
    @pytest.mark.asyncio
    async def test_immediate_shutdown(self, mock_shutdown_client, monkeypatch):
        """测试立即关机流程"""
        # Mock 依赖
        async def mock_get_history():
            class MockHistory:
                async def add_event(self, *args, **kwargs):
                    pass
            return MockHistory()
        
        def mock_get_notifier():
            class MockNotifier:
                async def notify(self, *args, **kwargs):
                    pass
            return MockNotifier()
        
        async def mock_get_config_manager():
            class MockConfigManager:
                async def get_config(self):
                    from models import Config
                    return Config(
                        shutdown_wait_minutes=5,
                        shutdown_battery_percent=20,
                        shutdown_final_wait_seconds=30,
                        estimated_runtime_threshold=3,
                        notify_channels=[],
                        notify_events=[],
                        sample_interval_seconds=10,
                        history_retention_days=7,
                        pre_shutdown_hooks=[]
                    )
            return MockConfigManager()
        
        monkeypatch.setattr("services.shutdown_manager.get_history_service", mock_get_history)
        monkeypatch.setattr("services.shutdown_manager.get_notifier_service", mock_get_notifier)
        monkeypatch.setattr("services.shutdown_manager.get_config_manager", mock_get_config_manager)
        
        manager = ShutdownManager(mock_shutdown_client, test_mode="dry_run")
        
        # 执行立即关机
        success = await manager.immediate_shutdown()
        
        assert success is True
        assert mock_shutdown_client.shutdown_called is False  # dry_run 模式不会实际关机
        
        # 验证 phase 为 completed
        status = manager.get_status()
        assert status["phase"] == "completed"
    
    @pytest.mark.asyncio
    async def test_hook_executor_cancellation(self, mock_shutdown_client, monkeypatch):
        """测试 Hook 执行器取消检查"""
        # Mock 依赖
        async def mock_get_history():
            class MockHistory:
                async def add_event(self, *args, **kwargs):
                    pass
            return MockHistory()
        
        def mock_get_notifier():
            class MockNotifier:
                async def notify(self, *args, **kwargs):
                    pass
            return MockNotifier()
        
        async def mock_get_config_manager():
            class MockConfigManager:
                async def get_config(self):
                    from models import Config
                    return Config(
                        shutdown_wait_minutes=5,
                        shutdown_battery_percent=20,
                        shutdown_final_wait_seconds=30,
                        estimated_runtime_threshold=3,
                        notify_channels=[],
                        notify_events=[],
                        sample_interval_seconds=10,
                        history_retention_days=7,
                        pre_shutdown_hooks=[
                            {
                                "hook_id": "ssh_shutdown",
                                "name": "Test Hook",
                                "priority": 1,
                                "enabled": True,
                                "timeout": 60,
                                "on_failure": "continue",
                                "config": {
                                    "host": "localhost",
                                    "port": 22,
                                    "username": "test",
                                    "password": "test"
                                }
                            }
                        ]
                    )
            return MockConfigManager()
        
        monkeypatch.setattr("services.shutdown_manager.get_history_service", mock_get_history)
        monkeypatch.setattr("services.shutdown_manager.get_notifier_service", mock_get_notifier)
        monkeypatch.setattr("services.shutdown_manager.get_config_manager", mock_get_config_manager)
        
        manager = ShutdownManager(mock_shutdown_client, test_mode="dry_run")
        
        # 启动立即关机并立即取消
        shutdown_task = asyncio.create_task(manager.immediate_shutdown())
        await asyncio.sleep(0.1)
        
        # 触发取消
        manager._shutdown_cancelled = True
        
        # 等待任务完成
        result = await shutdown_task
        
        # 验证关机被取消
        assert result is False or manager._current_phase == "idle"
    
    @pytest.mark.asyncio
    async def test_phase_transitions(self, mock_shutdown_client, monkeypatch):
        """测试关机阶段转换"""
        # Mock 依赖
        async def mock_get_history():
            class MockHistory:
                async def add_event(self, *args, **kwargs):
                    pass
            return MockHistory()
        
        def mock_get_notifier():
            class MockNotifier:
                async def notify(self, *args, **kwargs):
                    pass
            return MockNotifier()
        
        monkeypatch.setattr("services.shutdown_manager.get_history_service", mock_get_history)
        monkeypatch.setattr("services.shutdown_manager.get_notifier_service", mock_get_notifier)
        
        manager = ShutdownManager(
            mock_shutdown_client,
            wait_minutes=0,
            final_wait_seconds=1
        )
        
        # 初始阶段
        assert manager._current_phase == "idle"
        
        # 断电 -> waiting
        ups_data = UpsData(
            status=UpsStatus.ON_BATTERY,
            battery_charge=80,
            battery_runtime=1800
        )
        manager.on_power_lost(ups_data)
        await asyncio.sleep(0.1)
        assert manager._current_phase in ["waiting", "final_countdown", "executing_hooks"]
        
        # 恢复供电 -> idle
        manager.on_power_restored()
        await asyncio.sleep(0.1)
        assert manager._current_phase == "idle"
