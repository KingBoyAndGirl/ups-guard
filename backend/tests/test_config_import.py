"""测试配置导入导出功能"""
import pytest
import json
import tempfile
from pathlib import Path
from models import Config
from api.config import (
    mask_sensitive_fields,
    merge_configs,
    validate_config_structure,
    clean_masked_values,
    merge_config_list
)


class TestConfigMaskSensitiveFields:
    """测试敏感字段脱敏"""
    
    def test_mask_simple_password(self):
        """测试简单密码字段脱敏"""
        obj = {
            "username": "admin",
            "password": "secret123",
            "host": "localhost"
        }
        
        masked = mask_sensitive_fields(obj)
        
        assert masked["username"] == "admin"
        assert masked["password"] == "***"
        assert masked["host"] == "localhost"
    
    def test_mask_nested_sensitive(self):
        """测试嵌套敏感字段脱敏"""
        obj = {
            "name": "Test Channel",
            "config": {
                "api_key": "abc123",
                "api_secret": "xyz789",
                "webhook_url": "https://example.com"
            }
        }
        
        masked = mask_sensitive_fields(obj)
        
        assert masked["name"] == "Test Channel"
        assert masked["config"]["api_key"] == "***"
        assert masked["config"]["api_secret"] == "***"
        assert masked["config"]["webhook_url"] == "https://example.com"
    
    def test_mask_list_items(self):
        """测试列表项脱敏"""
        obj = {
            "channels": [
                {"name": "Channel 1", "token": "token1"},
                {"name": "Channel 2", "token": "token2"}
            ]
        }
        
        masked = mask_sensitive_fields(obj)
        
        assert len(masked["channels"]) == 2
        assert masked["channels"][0]["name"] == "Channel 1"
        assert masked["channels"][0]["token"] == "***"
        assert masked["channels"][1]["token"] == "***"
    
    def test_mask_empty_sensitive_field(self):
        """测试空敏感字段不脱敏"""
        obj = {
            "password": "",
            "token": None
        }
        
        masked = mask_sensitive_fields(obj)
        
        # 空字符串和 None 不应该被脱敏
        assert masked["password"] == ""
        assert masked["token"] is None


class TestConfigMerge:
    """测试配置合并"""
    
    def test_merge_simple_values(self):
        """测试简单值合并"""
        current = {
            "shutdown_wait_minutes": 5,
            "shutdown_battery_percent": 20
        }
        
        imported = {
            "shutdown_wait_minutes": 10
        }
        
        merged = merge_configs(current, imported)
        
        assert merged["shutdown_wait_minutes"] == 10
        assert merged["shutdown_battery_percent"] == 20
    
    def test_merge_preserves_sensitive(self):
        """测试合并保留敏感字段"""
        current = {
            "nut_host": "localhost",
            "nut_password": "current_password"
        }
        
        imported = {
            "nut_host": "192.168.1.100",
            "nut_password": "***"
        }
        
        merged = merge_configs(current, imported)
        
        assert merged["nut_host"] == "192.168.1.100"
        assert merged["nut_password"] == "current_password"
    
    def test_merge_config_list(self):
        """测试配置列表合并"""
        current = [
            {"id": "1", "name": "Channel 1", "plugin_id": "serverchan", "token": "old_token"}
        ]
        
        imported = [
            {"id": "1", "name": "Channel 1", "plugin_id": "serverchan", "token": "***"}
        ]
        
        merged = merge_config_list(current, imported)
        
        assert len(merged) == 1
        assert merged[0]["token"] == "old_token"
    
    def test_merge_adds_new_items(self):
        """测试合并添加新项"""
        current = [
            {"id": "1", "name": "Channel 1", "plugin_id": "serverchan"}
        ]
        
        imported = [
            {"id": "1", "name": "Channel 1", "plugin_id": "serverchan"},
            {"id": "2", "name": "Channel 2", "plugin_id": "pushplus"}
        ]
        
        merged = merge_config_list(current, imported)
        
        assert len(merged) == 2
        assert merged[1]["id"] == "2"


class TestConfigValidation:
    """测试配置验证"""
    
    def test_validate_valid_config(self):
        """测试验证有效配置"""
        config = {
            "shutdown_wait_minutes": 5,
            "shutdown_battery_percent": 20,
            "shutdown_final_wait_seconds": 30,
            "sample_interval_seconds": 10,
            "history_retention_days": 7
        }
        
        is_valid, message = validate_config_structure(config)
        
        assert is_valid is True
    
    def test_validate_missing_required_field(self):
        """测试缺少必需字段"""
        config = {
            "shutdown_wait_minutes": 5,
            "shutdown_battery_percent": 20
            # 缺少其他必需字段
        }
        
        is_valid, message = validate_config_structure(config)
        
        assert is_valid is False
        assert "缺少必要字段" in message
    
    def test_validate_invalid_type(self):
        """测试无效类型"""
        config = {
            "shutdown_wait_minutes": "not_a_number",
            "shutdown_battery_percent": 20,
            "shutdown_final_wait_seconds": 30,
            "sample_interval_seconds": 10,
            "history_retention_days": 7
        }
        
        is_valid, message = validate_config_structure(config)
        
        assert is_valid is False


class TestCleanMaskedValues:
    """测试清理脱敏值"""
    
    def test_clean_simple_masked(self):
        """测试清理简单脱敏标记"""
        obj = {
            "username": "admin",
            "password": "***"
        }
        
        cleaned = clean_masked_values(obj)
        
        assert cleaned["username"] == "admin"
        assert cleaned["password"] == ""
    
    def test_clean_nested_masked(self):
        """测试清理嵌套脱敏标记"""
        obj = {
            "config": {
                "api_key": "***",
                "webhook_url": "https://example.com"
            }
        }
        
        cleaned = clean_masked_values(obj)
        
        assert cleaned["config"]["api_key"] == ""
        assert cleaned["config"]["webhook_url"] == "https://example.com"


class TestSelectiveImport:
    """测试选择性导入"""
    
    def test_selected_fields_filtering(self):
        """测试选中字段过滤"""
        config_dict = {
            "shutdown_wait_minutes": 10,
            "shutdown_battery_percent": 15,
            "notify_channels": [],
            "pre_shutdown_hooks": []
        }
        
        selected_fields = ["shutdown_wait_minutes", "notify_channels"]
        
        filtered = {k: v for k, v in config_dict.items() if k in selected_fields}
        
        assert "shutdown_wait_minutes" in filtered
        assert "notify_channels" in filtered
        assert "shutdown_battery_percent" not in filtered
        assert "pre_shutdown_hooks" not in filtered
    
    def test_empty_selected_fields(self):
        """测试空选中字段列表"""
        config_dict = {
            "shutdown_wait_minutes": 10,
            "shutdown_battery_percent": 15
        }
        
        selected_fields = []
        
        filtered = {k: v for k, v in config_dict.items() if k in selected_fields}
        
        assert len(filtered) == 0
