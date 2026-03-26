"""API 集成测试"""
import pytest
from fastapi.testclient import TestClient
from main import app


class TestAPIIntegration:
    """测试所有 API 端点"""
    
    def test_root_endpoint(self):
        """测试根路径"""
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "UPS Guard API"
        assert "version" in data
        assert "status" in data
    
    def test_health_endpoint(self):
        """测试健康检查"""
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "mock_mode" in data
    
    def test_get_status(self):
        """测试获取 UPS 状态"""
        client = TestClient(app)
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "battery_charge" in data
    
    def test_get_config(self):
        """测试获取配置"""
        client = TestClient(app)
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "shutdown_wait_minutes" in data
        assert "shutdown_battery_percent" in data
        assert "history_retention_days" in data
        assert "poll_interval_seconds" in data
        assert "cleanup_interval_hours" in data
        assert "estimated_runtime_threshold" in data
    
    def test_put_config(self):
        """测试更新配置"""
        client = TestClient(app)
        # 先获取当前配置
        get_response = client.get("/api/config")
        config = get_response.json()
        
        # 修改配置
        config["shutdown_wait_minutes"] = 10
        
        # 更新配置
        put_response = client.put("/api/config", json=config)
        assert put_response.status_code == 200
        
        # 验证配置已更新
        verify_response = client.get("/api/config")
        updated_config = verify_response.json()
        assert updated_config["shutdown_wait_minutes"] == 10
    
    def test_get_events(self):
        """测试获取事件历史"""
        client = TestClient(app)
        response = client.get("/api/history/events?days=7")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert isinstance(data["events"], list)
    
    def test_get_metrics(self):
        """测试获取指标历史"""
        client = TestClient(app)
        response = client.get("/api/history/metrics?hours=1")
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert isinstance(data["metrics"], list)
    
    def test_cancel_shutdown(self):
        """测试取消关机"""
        client = TestClient(app)
        response = client.post("/api/actions/cancel-shutdown")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "message" in data
    
    def test_cleanup_history(self):
        """测试清理历史数据"""
        client = TestClient(app)
        response = client.post("/api/actions/cleanup-history")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "events_deleted" in data
        assert "metrics_deleted" in data
    
    def test_get_storage_info(self):
        """测试获取存储信息"""
        client = TestClient(app)
        response = client.get("/api/system/storage")
        assert response.status_code == 200
        data = response.json()
        assert "db_size_bytes" in data
        assert "db_size_mb" in data
        assert "event_count" in data
        assert "metric_count" in data
        assert isinstance(data["db_size_mb"], (int, float))
        assert isinstance(data["event_count"], int)
        assert isinstance(data["metric_count"], int)
    
    def test_list_plugins(self):
        """测试列出所有通知插件"""
        client = TestClient(app)
        response = client.get("/api/config/plugins")
        assert response.status_code == 200
        data = response.json()
        assert "plugins" in data
        plugins = data["plugins"]
        assert isinstance(plugins, list)
        
        # 验证新增的插件都已注册
        plugin_ids = [p["id"] for p in plugins]
        assert "serverchan" in plugin_ids
        assert "pushplus" in plugin_ids
        assert "dingtalk" in plugin_ids
        assert "telegram" in plugin_ids
        assert "email_smtp" in plugin_ids
        assert "webhook" in plugin_ids
        
        # 验证至少有 6 个插件
        assert len(plugins) >= 6
        
        # 验证每个插件都有必要的字段
        for plugin in plugins:
            assert "id" in plugin
            assert "name" in plugin
            assert "description" in plugin
            assert "config_schema" in plugin


class TestMockModeAPI:
    """测试 Mock 模式专用 API"""
    
    def test_mock_mode_enabled(self):
        """验证 Mock 模式已启用"""
        client = TestClient(app)
        response = client.get("/health")
        data = response.json()
        assert data["mock_mode"] is True
    
    def test_mock_power_lost(self):
        """测试模拟断电"""
        client = TestClient(app)
        response = client.post("/api/dev/mock/power-lost")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_mock_power_restored(self):
        """测试模拟恢复供电"""
        client = TestClient(app)
        response = client.post("/api/dev/mock/power-restored")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_mock_low_battery(self):
        """测试模拟低电量"""
        client = TestClient(app)
        response = client.post("/api/dev/mock/low-battery?charge=15")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
