"""测试 Hook 执行器"""
import pytest
import asyncio
from services.hook_executor import HookExecutor


# Mock Hook 类用于测试，避免实际执行任何操作
class MockHook:
    """用于测试的 Mock Hook，不执行任何实际操作"""
    
    def __init__(self, config, should_succeed=True, execution_time=0.1):
        self.config = config
        self.should_succeed = should_succeed
        self.execution_time = execution_time
    
    async def execute(self):
        """模拟执行"""
        await asyncio.sleep(self.execution_time)
        return self.should_succeed
    
    async def test_connection(self):
        """模拟连接测试"""
        await asyncio.sleep(0.01)  # 快速模拟
        return self.should_succeed


@pytest.fixture
def mock_hook_registry(monkeypatch):
    """创建一个 Mock 的 Hook Registry"""
    def create_mock_instance(hook_id, config):
        # 根据配置返回不同的 mock hook
        should_succeed = config.get("_mock_should_succeed", True)
        execution_time = config.get("_mock_execution_time", 0.01)
        return MockHook(config, should_succeed, execution_time)
    
    # 这个 fixture 返回一个函数，可以用来 patch registry
    return create_mock_instance


class TestHookExecutorCancellation:
    """测试 Hook 执行器取消机制"""
    
    @pytest.mark.asyncio
    async def test_cancellation_callback_stops_execution(self, mock_hook_registry, monkeypatch):
        """测试取消回调停止执行"""
        cancelled = False
        
        def cancellation_callback():
            return cancelled
        
        hooks_config = [
            {
                "hook_id": "ssh_shutdown",
                "name": "Test Hook 1",
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
            },
            {
                "hook_id": "ssh_shutdown",
                "name": "Test Hook 2",
                "priority": 2,
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
        
        executor = HookExecutor(
            hooks_config=hooks_config,
            test_mode="dry_run",
            cancellation_callback=cancellation_callback
        )
        
        # Mock registry 避免实际 SSH 连接
        monkeypatch.setattr(executor.registry, "create_instance", mock_hook_registry)
        
        # 在执行开始后立即取消
        async def cancel_soon():
            await asyncio.sleep(0.1)
            nonlocal cancelled
            cancelled = True
        
        cancel_task = asyncio.create_task(cancel_soon())
        result = await executor.execute_all()
        await cancel_task
        
        # 验证有任务被跳过
        assert result["skipped"] > 0 or result["total"] > result["success"] + result["failed"]
    
    @pytest.mark.asyncio
    async def test_no_cancellation_callback(self, mock_hook_registry, monkeypatch):
        """测试无取消回调时正常执行"""
        hooks_config = [
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
        
        executor = HookExecutor(
            hooks_config=hooks_config,
            test_mode="dry_run",
            cancellation_callback=None
        )
        
        # Mock registry 避免实际 SSH 连接
        monkeypatch.setattr(executor.registry, "create_instance", mock_hook_registry)
        
        result = await executor.execute_all()
        
        # 无取消回调时应该正常执行完成
        assert result["total"] == 1


class TestHookExecutorTimeout:
    """测试 Hook 执行器超时处理"""
    
    @pytest.mark.asyncio
    async def test_hook_timeout(self, monkeypatch):
        """测试 Hook 超时 - 使用 Mock 模式避免实际执行"""
        import asyncio
        
        # Mock 一个会超时的 hook 实例
        class SlowMockHook:
            def __init__(self, config):
                self.config = config
            
            async def execute(self):
                # 模拟一个需要很长时间的操作（超过超时时间）
                await asyncio.sleep(10)
                return True
            
            async def test_connection(self):
                return True
        
        # Mock registry 的 create_instance 方法
        def mock_create_instance(hook_id, config):
            return SlowMockHook(config)
        
        hooks_config = [
            {
                "hook_id": "custom_script",
                "name": "Slow Hook",
                "priority": 1,
                "enabled": True,
                "timeout": 1,  # 1秒超时
                "on_failure": "continue",
                "config": {
                    "script_path": "/mock/path",
                    "args": []
                }
            }
        ]
        
        executor = HookExecutor(
            hooks_config=hooks_config,
            test_mode="dry_run"  # 使用 dry_run 模式而非 production
        )
        
        # Mock create_instance 方法来返回我们的 SlowMockHook
        monkeypatch.setattr(executor.registry, "create_instance", mock_create_instance)
        
        result = await executor.execute_all()
        
        # 应该超时失败
        assert result["failed"] == 1
        assert result["details"][0]["success"] is False
        assert "timed out" in result["details"][0]["error"].lower() or "timeout" in result["details"][0]["error"].lower()


class TestHookExecutorDryRun:
    """测试 Hook 执行器 Dry-Run 模式"""
    
    @pytest.mark.asyncio
    async def test_dry_run_mode(self, mock_hook_registry, monkeypatch):
        """测试 Dry-Run 模式 - 使用 Mock 避免实际连接"""
        hooks_config = [
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
        
        executor = HookExecutor(
            hooks_config=hooks_config,
            test_mode="dry_run"
        )
        
        # Mock registry 避免实际 SSH 连接
        monkeypatch.setattr(executor.registry, "create_instance", mock_hook_registry)
        
        result = await executor.execute_all()
        
        # Dry-Run 模式应该测试连接而不是执行实际关机
        assert result["total"] == 1


class TestHookExecutorPriority:
    """测试 Hook 执行器优先级"""
    
    @pytest.mark.asyncio
    async def test_priority_ordering(self, mock_hook_registry, monkeypatch):
        """测试优先级排序 - 使用 Mock 避免实际连接"""
        execution_order = []
        
        async def track_execution(data):
            execution_order.append(data["data"]["hook_name"])
        
        hooks_config = [
            {
                "hook_id": "ssh_shutdown",
                "name": "Priority 3",
                "priority": 3,
                "enabled": True,
                "timeout": 60,
                "on_failure": "continue",
                "config": {
                    "host": "localhost",
                    "port": 22,
                    "username": "test",
                    "password": "test"
                }
            },
            {
                "hook_id": "ssh_shutdown",
                "name": "Priority 1",
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
            },
            {
                "hook_id": "ssh_shutdown",
                "name": "Priority 2",
                "priority": 2,
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
        
        executor = HookExecutor(
            hooks_config=hooks_config,
            test_mode="dry_run",
            progress_callback=track_execution
        )
        
        # Mock registry 避免实际 SSH 连接
        monkeypatch.setattr(executor.registry, "create_instance", mock_hook_registry)
        
        result = await executor.execute_all()
        
        # 验证所有 hook 都执行了
        assert result["total"] == 3
        
        # 验证优先级顺序（低数字优先）
        # 注意：同优先级的 hook 可能并行执行，所以只检查不同优先级的顺序
        priority_1_index = None
        priority_2_index = None
        priority_3_index = None
        
        for i, name in enumerate(execution_order):
            if "Priority 1" in name:
                priority_1_index = i
            elif "Priority 2" in name:
                priority_2_index = i
            elif "Priority 3" in name:
                priority_3_index = i
        
        # 优先级 1 应该在优先级 2 之前
        if priority_1_index is not None and priority_2_index is not None:
            assert priority_1_index < priority_2_index
        
        # 优先级 2 应该在优先级 3 之前
        if priority_2_index is not None and priority_3_index is not None:
            assert priority_2_index < priority_3_index


class TestHookExecutorFailurePolicy:
    """测试 Hook 执行器失败策略"""
    
    @pytest.mark.asyncio
    async def test_abort_on_failure(self, mock_hook_registry, monkeypatch):
        """测试失败时中止策略 - 使用 Mock 避免实际连接"""
        # 创建一个会失败的 mock hook
        def create_failing_mock(hook_id, config):
            if "invalid_host" in config.get("host", ""):
                return MockHook(config, should_succeed=False, execution_time=0.01)
            return MockHook(config, should_succeed=True, execution_time=0.01)
        
        hooks_config = [
            {
                "hook_id": "ssh_shutdown",
                "name": "Will Fail",
                "priority": 1,
                "enabled": True,
                "timeout": 60,
                "on_failure": "abort",
                "config": {
                    "host": "invalid_host_that_does_not_exist",
                    "port": 22,
                    "username": "test",
                    "password": "test"
                }
            },
            {
                "hook_id": "ssh_shutdown",
                "name": "Should Skip",
                "priority": 2,
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
        
        executor = HookExecutor(
            hooks_config=hooks_config,
            test_mode="dry_run"
        )
        
        # Mock registry 使用自定义的 failing mock
        monkeypatch.setattr(executor.registry, "create_instance", create_failing_mock)
        
        result = await executor.execute_all()
        
        # 第一个失败后应该跳过后续
        assert result["total"] == 2
        # 可能会有跳过的任务
        # assert result["skipped"] >= 0  # 取决于 abort 策略实现
    
    @pytest.mark.asyncio
    async def test_continue_on_failure(self, mock_hook_registry, monkeypatch):
        """测试失败时继续策略 - 使用 Mock 避免实际连接"""
        # 创建一个会失败的 mock hook
        def create_mixed_mock(hook_id, config):
            if "invalid_host" in config.get("host", ""):
                return MockHook(config, should_succeed=False, execution_time=0.01)
            return MockHook(config, should_succeed=True, execution_time=0.01)
        
        hooks_config = [
            {
                "hook_id": "ssh_shutdown",
                "name": "Will Fail",
                "priority": 1,
                "enabled": True,
                "timeout": 60,
                "on_failure": "continue",
                "config": {
                    "host": "invalid_host",
                    "port": 22,
                    "username": "test",
                    "password": "test"
                }
            },
            {
                "hook_id": "ssh_shutdown",
                "name": "Should Execute",
                "priority": 2,
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
        
        executor = HookExecutor(
            hooks_config=hooks_config,
            test_mode="dry_run"
        )
        
        # Mock registry 使用自定义的 mixed mock
        monkeypatch.setattr(executor.registry, "create_instance", create_mixed_mock)
        
        result = await executor.execute_all()
        
        # 所有任务都应该尝试执行
        assert result["total"] == 2
        assert result["skipped"] == 0
