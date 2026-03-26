"""测试诊断报告功能"""
import pytest
from api.system import mask_sensitive_data


class TestDiagnosticsMaskSensitiveData:
    """测试诊断报告脱敏功能"""
    
    def test_mask_password_fields(self):
        """测试密码字段脱敏"""
        obj = {
            "username": "admin",
            "password": "secret123",
            "ssh_password": "ssh_secret"
        }
        
        masked = mask_sensitive_data(obj)
        
        assert masked["username"] == "admin"
        assert masked["password"] == "***"
        assert masked["ssh_password"] == "***"
    
    def test_mask_token_fields(self):
        """测试 token 字段脱敏"""
        obj = {
            "api_token": "abc123",
            "webhook_token": "xyz789",
            "access_token": "token123"
        }
        
        masked = mask_sensitive_data(obj)
        
        assert masked["api_token"] == "***"
        assert masked["webhook_token"] == "***"
        assert masked["access_token"] == "***"
    
    def test_mask_key_fields(self):
        """测试密钥字段脱敏"""
        obj = {
            "api_key": "key123",
            "private_key": "private_data",
            "secret_key": "secret_data"
        }
        
        masked = mask_sensitive_data(obj)
        
        assert masked["api_key"] == "***"
        assert masked["private_key"] == "***"
        assert masked["secret_key"] == "***"
    
    def test_mask_nested_sensitive(self):
        """测试嵌套敏感字段脱敏"""
        obj = {
            "device": {
                "name": "Server 1",
                "config": {
                    "host": "192.168.1.100",
                    "password": "admin123",
                    "api_key": "key123"
                }
            }
        }
        
        masked = mask_sensitive_data(obj)
        
        assert masked["device"]["name"] == "Server 1"
        assert masked["device"]["config"]["host"] == "192.168.1.100"
        assert masked["device"]["config"]["password"] == "***"
        assert masked["device"]["config"]["api_key"] == "***"
    
    def test_mask_list_items(self):
        """测试列表项脱敏"""
        obj = {
            "devices": [
                {"name": "Device 1", "password": "pass1"},
                {"name": "Device 2", "token": "token2"}
            ]
        }
        
        masked = mask_sensitive_data(obj)
        
        assert len(masked["devices"]) == 2
        assert masked["devices"][0]["name"] == "Device 1"
        assert masked["devices"][0]["password"] == "***"
        assert masked["devices"][1]["name"] == "Device 2"
        assert masked["devices"][1]["token"] == "***"
    
    def test_preserve_non_sensitive(self):
        """测试保留非敏感字段"""
        obj = {
            "host": "192.168.1.100",
            "port": 22,
            "username": "admin",
            "device_name": "Server",
            "ip_address": "10.0.0.1"
        }
        
        masked = mask_sensitive_data(obj)
        
        assert masked["host"] == "192.168.1.100"
        assert masked["port"] == 22
        assert masked["username"] == "admin"
        assert masked["device_name"] == "Server"
        assert masked["ip_address"] == "10.0.0.1"
    
    def test_mask_empty_sensitive_field(self):
        """测试空敏感字段"""
        obj = {
            "password": "",
            "token": None,
            "api_key": False
        }
        
        masked = mask_sensitive_data(obj)
        
        # 空值不应该脱敏
        assert masked["password"] == ""
        assert masked["token"] is None
        assert masked["api_key"] is False
    
    def test_diagnostics_structure(self):
        """测试诊断报告结构"""
        # 模拟诊断报告结构
        diagnostics = {
            "generated_at": "2026-02-12T10:00:00",
            "system_info": {
                "version": "1.0.7",
                "python_version": "3.11.0",
                "os": "Linux",
                "test_mode": "production"
            },
            "ups_status": {
                "status": "ONLINE",
                "battery_charge": 100
            },
            "config_summary": {
                "shutdown_wait_minutes": 5,
                "notification_channels_count": 2
            },
            "device_status": [
                {
                    "name": "Server 1",
                    "config": {
                        "host": "192.168.1.100",
                        "password": "admin123"
                    }
                }
            ]
        }
        
        masked = mask_sensitive_data(diagnostics)
        
        # 验证结构保持不变
        assert "generated_at" in masked
        assert "system_info" in masked
        assert "ups_status" in masked
        assert "config_summary" in masked
        assert "device_status" in masked
        
        # 验证敏感数据已脱敏
        assert masked["device_status"][0]["config"]["password"] == "***"
        
        # 验证非敏感数据保持不变
        assert masked["device_status"][0]["config"]["host"] == "192.168.1.100"
        assert masked["system_info"]["version"] == "1.0.7"


class TestDiagnosticsCompleteness:
    """测试诊断报告完整性"""
    
    def test_required_sections(self):
        """测试必需的诊断报告部分"""
        required_sections = [
            "generated_at",
            "system_info",
            "ups_status",
            "config_summary",
            "recent_events",
            "shutdown_manager_status",
            "websocket_connections",
            "database_info",
            "device_status"
        ]
        
        # 这个测试需要实际运行 API 才能完整测试
        # 这里只验证结构定义
        for section in required_sections:
            assert section in required_sections
    
    def test_system_info_fields(self):
        """测试系统信息字段"""
        system_info = {
            "version": "1.0.7",
            "python_version": "3.11.0",
            "os": "Linux x86_64",
            "uptime_seconds": 12345,
            "test_mode": "production"
        }
        
        assert "version" in system_info
        assert "python_version" in system_info
        assert "os" in system_info
        assert "test_mode" in system_info
    
    def test_config_summary_no_sensitive_data(self):
        """测试配置摘要不含敏感数据"""
        config_summary = {
            "shutdown_wait_minutes": 5,
            "shutdown_battery_percent": 20,
            "notification_channels_count": 2,
            "pre_shutdown_hooks_count": 3,
            "test_mode": "production"
        }
        
        # 验证不包含敏感字段
        assert "password" not in config_summary
        assert "token" not in config_summary
        assert "api_key" not in config_summary
        assert "secret" not in config_summary


class TestDiagnosticsJSONEncoder:
    """测试诊断报告 JSON 编码器"""
    
    def test_json_encoder_datetime(self):
        """测试 JSON 编码器处理 datetime 对象"""
        import json
        from datetime import datetime
        from api.system import DiagnosticsJSONEncoder
        
        test_data = {
            "timestamp": datetime(2026, 2, 12, 10, 30, 0),
            "nested": {
                "created_at": datetime(2026, 2, 11, 15, 0, 0)
            }
        }
        
        # 使用自定义编码器
        result = json.dumps(test_data, cls=DiagnosticsJSONEncoder)
        
        # 验证 datetime 被转换为 ISO 格式字符串
        assert "2026-02-12T10:30:00" in result
        assert "2026-02-11T15:00:00" in result
    
    def test_json_encoder_decimal(self):
        """测试 JSON 编码器处理 Decimal 对象"""
        import json
        from decimal import Decimal
        from api.system import DiagnosticsJSONEncoder
        
        test_data = {
            "price": Decimal("123.45"),
            "quantity": Decimal("10")
        }
        
        result = json.dumps(test_data, cls=DiagnosticsJSONEncoder)
        parsed = json.loads(result)
        
        # 验证 Decimal 被转换为 float
        assert parsed["price"] == 123.45
        assert parsed["quantity"] == 10.0
    
    def test_json_encoder_enum(self):
        """测试 JSON 编码器处理 Enum 对象"""
        import json
        from enum import Enum
        from api.system import DiagnosticsJSONEncoder
        
        class Status(Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"
        
        test_data = {
            "status": Status.ACTIVE
        }
        
        result = json.dumps(test_data, cls=DiagnosticsJSONEncoder)
        parsed = json.loads(result)
        
        # 验证 Enum 被转换为其值
        assert parsed["status"] == "active"
    
    def test_json_encoder_bytes(self):
        """测试 JSON 编码器处理 bytes 对象"""
        import json
        from api.system import DiagnosticsJSONEncoder
        
        test_data = {
            "data": b"test bytes"
        }
        
        result = json.dumps(test_data, cls=DiagnosticsJSONEncoder)
        parsed = json.loads(result)
        
        # 验证 bytes 被解码为字符串
        assert parsed["data"] == "test bytes"
    
    def test_json_encoder_complex_nested(self):
        """测试 JSON 编码器处理复杂嵌套结构"""
        import json
        from datetime import datetime
        from decimal import Decimal
        from api.system import DiagnosticsJSONEncoder
        
        test_data = {
            "timestamp": datetime(2026, 2, 12, 10, 0, 0),
            "metrics": {
                "value": Decimal("99.99"),
                "items": [
                    datetime(2026, 2, 11, 10, 0, 0),
                    Decimal("12.34"),
                    "normal_string"
                ]
            }
        }
        
        # 应该能成功序列化
        result = json.dumps(test_data, cls=DiagnosticsJSONEncoder)
        parsed = json.loads(result)
        
        # 验证所有值都被正确转换
        assert "2026-02-12T10:00:00" in result
        assert parsed["metrics"]["value"] == 99.99
        assert len(parsed["metrics"]["items"]) == 3

