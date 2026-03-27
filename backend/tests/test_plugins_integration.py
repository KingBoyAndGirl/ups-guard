"""通知插件集成测试"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import httpx


class TestDingTalkPlugin:
    """测试钉钉机器人插件"""
    
    def test_plugin_registered(self):
        """验证插件已注册"""
        from plugins.registry import registry
        
        dingtalk = registry.get_plugin("dingtalk")
        assert dingtalk is not None
        assert dingtalk.plugin_id == "dingtalk"
        assert dingtalk.plugin_name == "钉钉机器人"
    
    def test_config_schema(self):
        """测试配置 Schema"""
        from plugins.dingtalk import DingTalkPlugin
        
        schema = DingTalkPlugin.get_config_schema()
        assert len(schema) == 2
        
        # webhook_url
        assert schema[0]["key"] == "webhook_url"
        assert schema[0]["required"] is True
        
        # secret (可选)
        assert schema[1]["key"] == "secret"
        assert schema[1]["required"] is False
    
    def test_validate_config_valid(self):
        """测试有效配置验证"""
        from plugins.dingtalk import DingTalkPlugin
        
        config = {
            "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=abc123"
        }
        
        plugin = DingTalkPlugin(config)
        assert plugin.config == config
    
    def test_validate_config_invalid_url(self):
        """测试无效 URL"""
        from plugins.dingtalk import DingTalkPlugin
        
        config = {
            "webhook_url": "https://invalid.com/webhook"
        }
        
        with pytest.raises(ValueError, match="Webhook URL 格式不正确"):
            DingTalkPlugin(config)
    
    @pytest.mark.asyncio
    async def test_send_message(self):
        """测试发送消息 (模拟 HTTP 请求)"""
        from plugins.dingtalk import DingTalkPlugin
        
        config = {
            "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=test"
        }
        
        plugin = DingTalkPlugin(config)
        
        # Mock HTTP 响应
        mock_response = Mock()
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
        
        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await plugin.send("测试标题", "测试内容", "info")
            assert result is True


class TestTelegramPlugin:
    """测试 Telegram Bot 插件"""
    
    def test_plugin_registered(self):
        """验证插件已注册"""
        from plugins.registry import registry
        
        telegram = registry.get_plugin("telegram")
        assert telegram is not None
        assert telegram.plugin_id == "telegram"
        assert telegram.plugin_name == "Telegram Bot"
    
    def test_config_schema(self):
        """测试配置 Schema"""
        from plugins.telegram import TelegramPlugin
        
        schema = TelegramPlugin.get_config_schema()
        assert len(schema) == 3
        
        # bot_token
        assert schema[0]["key"] == "bot_token"
        assert schema[0]["type"] == "password"
        assert schema[0]["required"] is True
        
        # chat_id
        assert schema[1]["key"] == "chat_id"
        assert schema[1]["required"] is True
        
        # proxy_url (可选)
        assert schema[2]["key"] == "proxy_url"
        assert schema[2]["required"] is False
    
    def test_validate_config_valid(self):
        """测试有效配置验证"""
        from plugins.telegram import TelegramPlugin
        
        config = {
            "bot_token": "123456:ABC-DEF1234ghIkl",
            "chat_id": "123456789"
        }
        
        plugin = TelegramPlugin(config)
        assert plugin.config == config
    
    def test_validate_config_invalid_token(self):
        """测试无效 Token 格式"""
        from plugins.telegram import TelegramPlugin
        
        config = {
            "bot_token": "invalid_token",
            "chat_id": "123456789"
        }
        
        with pytest.raises(ValueError, match="Token 格式不正确"):
            TelegramPlugin(config)
    
    @pytest.mark.asyncio
    async def test_send_message(self):
        """测试发送消息"""
        from plugins.telegram import TelegramPlugin
        
        config = {
            "bot_token": "123456:ABC-DEF1234ghIkl",
            "chat_id": "123456789"
        }
        
        plugin = TelegramPlugin(config)
        
        # Mock HTTP 响应
        mock_response = Mock()
        mock_response.json.return_value = {"ok": True}
        
        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await plugin.send("测试标题", "测试内容", "info")
            assert result is True


class TestEmailSMTPPlugin:
    """测试邮件 SMTP 插件"""
    
    def test_plugin_registered(self):
        """验证插件已注册"""
        from plugins.registry import registry
        
        email = registry.get_plugin("email_smtp")
        assert email is not None
        assert email.plugin_id == "email_smtp"
        assert email.plugin_name == "邮件 (SMTP)"
    
    def test_config_schema(self):
        """测试配置 Schema"""
        from plugins.email_smtp import EmailSMTPPlugin
        
        schema = EmailSMTPPlugin.get_config_schema()
        assert len(schema) == 7
        
        # 验证必填字段
        required_keys = ["smtp_host", "username", "password", "sender", "recipients"]
        schema_keys = [s["key"] for s in schema]
        for key in required_keys:
            assert key in schema_keys
    
    def test_validate_config_valid(self):
        """测试有效配置验证"""
        from plugins.email_smtp import EmailSMTPPlugin
        
        config = {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "username": "user@example.com",
            "password": "password123",
            "sender": "noreply@example.com",
            "recipients": "admin@example.com, user@example.com",
            "use_tls": "true"
        }
        
        plugin = EmailSMTPPlugin(config)
        assert plugin.config == config
    
    def test_validate_config_invalid_email(self):
        """测试无效邮箱格式"""
        from plugins.email_smtp import EmailSMTPPlugin
        
        config = {
            "smtp_host": "smtp.example.com",
            "username": "user@example.com",
            "password": "password123",
            "sender": "invalid_email",
            "recipients": "admin@example.com"
        }
        
        with pytest.raises(ValueError, match="邮箱格式不正确"):
            EmailSMTPPlugin(config)


class TestWebhookPlugin:
    """测试通用 Webhook 插件"""
    
    def test_plugin_registered(self):
        """验证插件已注册"""
        from plugins.registry import registry
        
        webhook = registry.get_plugin("webhook")
        assert webhook is not None
        assert webhook.plugin_id == "webhook"
        assert webhook.plugin_name == "Webhook"
    
    def test_config_schema(self):
        """测试配置 Schema"""
        from plugins.webhook import WebhookPlugin
        
        schema = WebhookPlugin.get_config_schema()
        assert len(schema) == 4
        
        # url
        assert schema[0]["key"] == "url"
        assert schema[0]["required"] is True
        
        # method
        assert schema[1]["key"] == "method"
        assert schema[1]["required"] is False
    
    def test_validate_config_valid(self):
        """测试有效配置验证"""
        from plugins.webhook import WebhookPlugin
        
        config = {
            "url": "https://example.com/webhook",
            "method": "POST"
        }
        
        plugin = WebhookPlugin(config)
        assert plugin.config == config
    
    def test_validate_config_invalid_url(self):
        """测试无效 URL"""
        from plugins.webhook import WebhookPlugin
        
        config = {
            "url": "not_a_url"
        }
        
        with pytest.raises(ValueError, match="URL 必须以 http"):
            WebhookPlugin(config)
    
    @pytest.mark.asyncio
    async def test_send_with_template(self):
        """测试使用自定义模板发送"""
        from plugins.webhook import WebhookPlugin
        
        config = {
            "url": "https://example.com/webhook",
            "method": "POST",
            "template": '{"msg": "{title}", "content": "{content}"}'
        }
        
        plugin = WebhookPlugin(config)
        
        # Mock HTTP 响应
        mock_response = Mock()
        mock_response.status_code = 200
        
        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await plugin.send("测试标题", "测试内容", "info")
            assert result is True
    
    def test_template_variable_replacement(self):
        """测试模板变量替换"""
        from plugins.webhook import WebhookPlugin
        
        config = {
            "url": "https://example.com/webhook"
        }
        
        plugin = WebhookPlugin(config)
        
        template = {
            "title": "{title}",
            "message": "{content}",
            "severity": "{level}",
            "nested": {
                "time": "{timestamp}"
            }
        }
        
        vars = {
            "title": "Test Title",
            "content": "Test Content",
            "level": "info",
            "timestamp": "2024-01-01T00:00:00"
        }
        
        result = plugin._replace_template_vars(template, vars)
        
        assert result["title"] == "Test Title"
        assert result["message"] == "Test Content"
        assert result["severity"] == "info"
        assert result["nested"]["time"] == "2024-01-01T00:00:00"
