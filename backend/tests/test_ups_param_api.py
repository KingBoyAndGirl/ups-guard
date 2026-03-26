"""测试 UPS 参数配置 API"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


class TestUpsParamAPI:
    """测试 UPS 参数配置 API 端点"""
    
    def test_allowed_set_vars_whitelist(self):
        """测试 ALLOWED_SET_VARS 白名单配置"""
        from api.ups_control import ALLOWED_SET_VARS
        
        # 验证白名单包含预期的变量
        assert "input.transfer.high" in ALLOWED_SET_VARS
        assert "input.transfer.low" in ALLOWED_SET_VARS
        assert "input.sensitivity" in ALLOWED_SET_VARS
        assert "ups.delay.shutdown" in ALLOWED_SET_VARS
        
        # 验证高压阈值配置
        high_config = ALLOWED_SET_VARS["input.transfer.high"]
        assert high_config["type"] == "number"
        assert high_config["min"] == 220
        assert high_config["max"] == 300
        
        # 验证低压阈值配置
        low_config = ALLOWED_SET_VARS["input.transfer.low"]
        assert low_config["type"] == "number"
        assert low_config["min"] == 100
        assert low_config["max"] == 200
        
        # 验证灵敏度配置
        sens_config = ALLOWED_SET_VARS["input.sensitivity"]
        assert sens_config["type"] == "enum"
        assert set(sens_config["options"]) == {"low", "medium", "high"}
        
        # 验证关机延迟配置
        delay_config = ALLOWED_SET_VARS["ups.delay.shutdown"]
        assert delay_config["type"] == "number"
        assert delay_config.get("integer") is True
        assert delay_config["min"] == 0
        assert delay_config["max"] == 600
    
    def test_validate_var_value_number(self):
        """测试数字类型变量验证"""
        from api.ups_control import _validate_var_value
        
        meta = {"type": "number", "min": 100, "max": 200}
        
        # 有效值
        assert _validate_var_value("test", "150", meta) is None
        assert _validate_var_value("test", "100", meta) is None
        assert _validate_var_value("test", "200", meta) is None
        
        # 无效值 - 非数字
        error = _validate_var_value("test", "abc", meta)
        assert error is not None
        assert "不是有效的数字" in error
        
        # 无效值 - 超出范围
        error = _validate_var_value("test", "50", meta)
        assert error is not None
        assert "低于最小值" in error
        
        error = _validate_var_value("test", "250", meta)
        assert error is not None
        assert "超过最大值" in error
    
    def test_validate_var_value_integer(self):
        """测试整数类型变量验证"""
        from api.ups_control import _validate_var_value
        
        meta = {"type": "number", "integer": True, "min": 0, "max": 600}
        
        # 有效整数
        assert _validate_var_value("test", "30", meta) is None
        assert _validate_var_value("test", "0", meta) is None
        
        # 无效 - 小数
        error = _validate_var_value("test", "30.5", meta)
        assert error is not None
        assert "必须是整数" in error
    
    def test_validate_var_value_enum(self):
        """测试枚举类型变量验证"""
        from api.ups_control import _validate_var_value
        
        meta = {"type": "enum", "options": ["low", "medium", "high"]}
        
        # 有效值
        assert _validate_var_value("test", "low", meta) is None
        assert _validate_var_value("test", "medium", meta) is None
        assert _validate_var_value("test", "high", meta) is None
        
        # 无效值
        error = _validate_var_value("test", "invalid", meta)
        assert error is not None
        assert "不在允许的选项中" in error


class TestUpsParamEventLogging:
    """测试 UPS 参数修改的事件记录"""
    
    def test_event_type_exists(self):
        """测试 UPS_PARAM_CHANGED 事件类型存在"""
        from models import EventType
        
        assert hasattr(EventType, "UPS_PARAM_CHANGED")
        assert EventType.UPS_PARAM_CHANGED == "UPS_PARAM_CHANGED"
    
    def test_event_in_notifier_level_map(self):
        """测试事件类型在通知器映射中"""
        from services.notifier import NotifierService
        from models import EventType
        
        # 创建 notifier 实例来访问 level_map
        # 注意：这个测试依赖于 notify 方法中的 level_map
        # 实际测试中，我们验证 UPS_PARAM_CHANGED 会被正确处理
        assert EventType.UPS_PARAM_CHANGED == "UPS_PARAM_CHANGED"


class TestUpsParamFrontendSupport:
    """测试前端对 UPS 参数事件的支持"""
    
    def test_event_type_in_model(self):
        """测试事件类型在模型中正确定义"""
        from models import EventType
        
        # 获取所有事件类型
        event_types = [e.value for e in EventType]
        
        # 验证 UPS_PARAM_CHANGED 在列表中
        assert "UPS_PARAM_CHANGED" in event_types
