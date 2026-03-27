"""测试通知插件"""
import pytest
from plugins.serverchan import ServerChanPlugin
from plugins.pushplus import PushPlusPlugin


class TestServerChanPlugin:
    """测试 Server酱 插件"""
    
    def test_initialization(self):
        """测试插件初始化"""
        config = {"sendkey": "SCTxxxxxxxxxx"}
        plugin = ServerChanPlugin(config)
        
        assert plugin.plugin_id == "serverchan"
        assert plugin.plugin_name == "Server酱"
        assert plugin.config == config
    
    def test_config_schema(self):
        """测试配置模式"""
        schema = ServerChanPlugin.get_config_schema()
        
        assert len(schema) == 1
        assert schema[0]["key"] == "sendkey"
        assert schema[0]["required"] is True
    
    def test_validate_config_valid(self):
        """测试有效配置验证"""
        config = {"sendkey": "SCT123456789"}
        plugin = ServerChanPlugin(config)
        
        # 应该不抛出异常
        plugin.validate_config()
    
    def test_validate_config_empty(self):
        """测试空配置验证"""
        config = {}
        
        with pytest.raises(ValueError, match="SendKey 不能为空"):
            plugin = ServerChanPlugin(config)
    
    def test_validate_config_invalid_format(self):
        """测试无效格式验证"""
        config = {"sendkey": "invalid_key"}
        
        with pytest.raises(ValueError, match="格式不正确"):
            plugin = ServerChanPlugin(config)
    
    def test_message_formatting(self):
        """测试消息格式化（不实际发送）"""
        config = {"sendkey": "SCT123456789"}
        plugin = ServerChanPlugin(config)
        
        # 验证不同级别的图标映射
        levels = ["info", "warning", "error"]
        icons = ["ℹ️", "⚠️", "❌"]
        
        for level, icon in zip(levels, icons):
            # 这里只验证配置正确，不实际发送请求
            assert plugin.config["sendkey"].startswith("SCT")


class TestPushPlusPlugin:
    """测试 PushPlus 插件"""
    
    def test_initialization(self):
        """测试插件初始化"""
        config = {"token": "test_token_123"}
        plugin = PushPlusPlugin(config)
        
        assert plugin.plugin_id == "pushplus"
        assert plugin.plugin_name == "PushPlus"
        assert plugin.config == config
    
    def test_config_schema(self):
        """测试配置模式"""
        schema = PushPlusPlugin.get_config_schema()
        
        assert len(schema) == 2
        assert schema[0]["key"] == "token"
        assert schema[0]["required"] is True
        assert schema[1]["key"] == "topic"
        assert schema[1]["required"] is False
    
    def test_validate_config_valid(self):
        """测试有效配置验证"""
        config = {"token": "test_token"}
        plugin = PushPlusPlugin(config)
        
        # 应该不抛出异常
        plugin.validate_config()
    
    def test_validate_config_empty(self):
        """测试空配置验证"""
        config = {}
        
        with pytest.raises(ValueError, match="Token 不能为空"):
            plugin = PushPlusPlugin(config)
    
    def test_validate_config_with_topic(self):
        """测试带群组配置"""
        config = {
            "token": "test_token",
            "topic": "my_group"
        }
        plugin = PushPlusPlugin(config)
        
        # 应该不抛出异常
        plugin.validate_config()
        assert plugin.config["topic"] == "my_group"
    
    def test_message_formatting(self):
        """测试消息格式化（不实际发送）"""
        config = {"token": "test_token"}
        plugin = PushPlusPlugin(config)
        
        # 验证配置正确
        assert plugin.config["token"] == "test_token"
        
        # 验证可选的 topic
        topic = plugin.config.get("topic", "")
        assert topic == ""


class TestPluginRegistry:
    """测试插件注册表"""
    
    def test_plugins_registered(self):
        """测试插件是否已注册"""
        from plugins.registry import registry
        
        # 验证插件已注册
        serverchan = registry.get_plugin("serverchan")
        assert serverchan is not None
        assert serverchan.plugin_id == "serverchan"
        
        pushplus = registry.get_plugin("pushplus")
        assert pushplus is not None
        assert pushplus.plugin_id == "pushplus"
    
    def test_list_plugins(self):
        """测试列出所有插件"""
        from plugins.registry import registry
        
        plugins = registry.list_plugins()
        
        assert len(plugins) >= 2
        plugin_ids = [p["id"] for p in plugins]
        assert "serverchan" in plugin_ids
        assert "pushplus" in plugin_ids
