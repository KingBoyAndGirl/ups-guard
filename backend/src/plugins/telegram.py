"""Telegram Bot 通知插件"""
import httpx
import logging
from typing import Dict, Any, List
from plugins.base import NotifierPlugin
from plugins.registry import registry

logger = logging.getLogger(__name__)


class TelegramPlugin(NotifierPlugin):
    """Telegram Bot 通知插件 (https://core.telegram.org/bots/api)"""
    
    plugin_id = "telegram"
    plugin_name = "Telegram Bot"
    plugin_description = "通过 Telegram Bot 发送通知消息"
    
    @classmethod
    def get_config_schema(cls) -> List[Dict[str, Any]]:
        return [
            {
                "key": "bot_token",
                "label": "Bot Token",
                "type": "password",
                "required": True,
                "placeholder": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
                "description": "从 @BotFather 获取"
            },
            {
                "key": "chat_id",
                "label": "Chat ID",
                "type": "text",
                "required": True,
                "placeholder": "123456789 或 @channel_name",
                "description": "接收消息的用户/群组/频道 ID"
            },
            {
                "key": "proxy_url",
                "label": "代理地址 (可选)",
                "type": "text",
                "required": False,
                "placeholder": "http://proxy.example.com:8080",
                "description": "如需代理访问 Telegram API，填写此项"
            }
        ]
    
    def validate_config(self):
        if "bot_token" not in self.config or not self.config["bot_token"]:
            raise ValueError("Telegram Bot Token 不能为空")
        
        if "chat_id" not in self.config or not self.config["chat_id"]:
            raise ValueError("Telegram Chat ID 不能为空")
        
        # Bot Token 基本格式检查（跳过脱敏值检查）
        token = self.config["bot_token"]
        if token != "***" and not token.startswith("***"):
            # 完整 Token 格式检查: 数字:字母数字串
            if ":" not in token:
                raise ValueError("Telegram Bot Token 格式不正确，应为 123456789:ABCdef... 格式")
            parts = token.split(":", 1)
            if not parts[0].isdigit():
                raise ValueError("Telegram Bot Token 格式不正确，冒号前应为数字")
            # Token 的第二部分至少要有一些字符（不做严格长度限制）
            if len(parts[1]) < 10:
                raise ValueError("Telegram Bot Token 格式不正确，Token 太短")

    async def send(self, title: str, content: str, level: str = "info", timestamp: str = ""):
        """
        发送 Telegram 通知
        
        API 文档: https://core.telegram.org/bots/api#sendmessage
        """
        bot_token = self.config["bot_token"]
        chat_id = self.config["chat_id"]
        proxy_url = self.config.get("proxy_url", "")
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        # 根据级别添加图标
        icon_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌"
        }
        icon = icon_map.get(level, "")
        
        # 构建结构化消息
        html_text = f"<b>标题:</b> {title}\n<b>内容:</b> {content}\n<b>级别:</b> {icon} {level}\n<b>时间:</b> {timestamp}"
        
        data = {
            "chat_id": chat_id,
            "text": html_text,
            "parse_mode": "HTML"
        }
        
        try:
            # 配置代理 (httpx 使用 proxies 参数，但需要正确的格式)
            proxies = None
            if proxy_url:
                proxies = proxy_url
            
            async with httpx.AsyncClient(timeout=10, proxy=proxies) as client:
                response = await client.post(url, json=data)

                # 处理 HTTP 错误
                if response.status_code == 404:
                    logger.error(f"Telegram API 返回 404: Bot Token 可能无效")
                    return False, "Bot Token 无效，请检查是否正确从 @BotFather 获取"

                if response.status_code == 401:
                    logger.error(f"Telegram API 返回 401: Bot Token 未授权")
                    return False, "Bot Token 未授权，请检查 Token 是否正确"

                result = response.json()
                
                if result.get("ok"):
                    return True, None
                else:
                    error_code = result.get("error_code", "")
                    error_msg = result.get("description", "Unknown error")

                    # 提供更友好的错误信息
                    if error_code == 400 and "chat not found" in error_msg.lower():
                        error_msg = f"Chat ID 无效或 Bot 未加入该聊天: {chat_id}"
                    elif error_code == 403:
                        error_msg = f"Bot 没有发送消息的权限，请确认 Bot 已被添加到聊天中"

                    logger.error(f"Telegram 通知发送失败: {error_msg}")
                    return False, error_msg
        except httpx.ConnectError as e:
            logger.error(f"Telegram 连接失败: {e}")
            return False, "无法连接到 Telegram API，请检查网络或配置代理"
        except httpx.TimeoutException:
            logger.error("Telegram 请求超时")
            return False, "请求超时，请检查网络连接或配置代理"
        except Exception as e:
            logger.error(f"Telegram 通知发送异常: {e}")
            return False, str(e)


# 自动注册插件
registry.register(TelegramPlugin)
