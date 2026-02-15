"""Test new configuration parameters"""
import pytest
from models import Config


class TestConfigParameters:
    """测试新增的配置参数"""
    
    def test_config_model_includes_new_fields(self):
        """测试 Config 模型包含新字段"""
        config = Config()
        
        # 验证新字段存在且有默认值
        assert hasattr(config, 'poll_interval_seconds')
        assert hasattr(config, 'cleanup_interval_hours')
        
        # 验证默认值
        assert config.poll_interval_seconds == 5
        assert config.cleanup_interval_hours == 24
    
    def test_config_model_accepts_custom_values(self):
        """测试 Config 模型接受自定义值"""
        config = Config(
            poll_interval_seconds=10,
            cleanup_interval_hours=12
        )
        
        assert config.poll_interval_seconds == 10
        assert config.cleanup_interval_hours == 12
    
    def test_config_model_serialization(self):
        """测试 Config 模型序列化"""
        config = Config(
            poll_interval_seconds=3,
            cleanup_interval_hours=48
        )
        
        config_dict = config.dict()
        
        assert 'poll_interval_seconds' in config_dict
        assert 'cleanup_interval_hours' in config_dict
        assert config_dict['poll_interval_seconds'] == 3
        assert config_dict['cleanup_interval_hours'] == 48
    
    def test_config_update_model(self):
        """测试 ConfigUpdate 模型包含所有必需字段"""
        from api.config import ConfigUpdate
        
        # 验证 ConfigUpdate 包含所有必需字段
        config_update = ConfigUpdate(
            shutdown_wait_minutes=5,
            shutdown_battery_percent=20,
            shutdown_final_wait_seconds=30,
            estimated_runtime_threshold=3,
            notify_channels=[],
            notify_events=[],
            sample_interval_seconds=60,
            history_retention_days=30,
            poll_interval_seconds=5,
            cleanup_interval_hours=24
        )
        
        assert config_update.poll_interval_seconds == 5
        assert config_update.cleanup_interval_hours == 24
        assert config_update.estimated_runtime_threshold == 3
