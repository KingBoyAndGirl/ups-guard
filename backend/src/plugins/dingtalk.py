"""钉钉机器人通知插件"""
import httpx
import logging
import time
import hmac
import hashlib
import base64
from urllib.parse import quote_plus
from typing import Dict, Any, List
from plugins.base import NotifierPlugin
from plugins.registry import registry

logger = logging.getLogger(__name__)


class DingTalkPlugin(NotifierPlugin):
    """钉钉机器人通知插件 (https://open.dingtalk.com/document/robots/custom-robot-access)"""
    
    plugin_id = "dingtalk"
    plugin_name = "钉钉机器人"
    plugin_description = "通过钉钉群机器人发送 Markdown 通知"
    
    @classmethod
    def get_config_schema(cls) -> List[Dict[str, Any]]:
        return [
            {
                "key": "webhook_url",
                "label": "Webhook URL",
                "type": "text",
                "required": True,
                "placeholder": "https://oapi.dingtalk.com/robot/send?access_token=...",
                "description": "从钉钉群机器人设置中获取"
            },
            {
                "key": "secret",
                "label": "加签密钥 (可选)",
                "type": "password",
                "required": False,
                "placeholder": "SEC开头的密钥",
                "description": "启用加签安全设置后需要填写"
            }
        ]
    
    def validate_config(self):
        if "webhook_url" not in self.config or not self.config["webhook_url"]:
            raise ValueError("钉钉机器人 Webhook URL 不能为空")
        
        webhook_url = self.config["webhook_url"]
        # 更严格的 URL 验证：必须是 HTTPS 且域名完全匹配
        if not webhook_url.startswith("https://oapi.dingtalk.com/robot/send?access_token="):
            raise ValueError("钉钉机器人 Webhook URL 格式不正确，必须以 https://oapi.dingtalk.com/robot/send?access_token= 开头")
    
    def _generate_sign(self, secret: str, timestamp: int) -> str:
        """
        生成钉钉加签
        
        Args:
            secret: 加签密钥
            timestamp: 当前时间戳（毫秒）
        
        Returns:
            签名字符串
        """
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        sign = quote_plus(base64.b64encode(hmac_code))
        return sign
    
    async def send(self, title: str, content: str, level: str = "info", timestamp: str = ""):
        """
        发送钉钉机器人通知
        
        API 文档: https://open.dingtalk.com/document/robots/custom-robot-access
        """
        webhook_url = self.config["webhook_url"]
        secret = self.config.get("secret", "")
        
        # 如果有加签密钥，添加签名参数
        if secret:
            timestamp_ms = int(time.time() * 1000)
            sign = self._generate_sign(secret, timestamp_ms)
            webhook_url = f"{webhook_url}&timestamp={timestamp_ms}&sign={sign}"
        
        # 根据级别添加图标和颜色标记
        icon_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌"
        }
        icon = icon_map.get(level, "")
        
        # 构建结构化 Markdown 消息
        markdown_text = f"**标题:** {title}\n\n**内容:** {content}\n\n**级别:** {icon} {level}\n\n**时间:** {timestamp}"
        
        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": markdown_text
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(webhook_url, json=data)
                result = response.json()
                
                if result.get("errcode") == 0:
                    return True, None
                else:
                    error_msg = result.get('errmsg', '未知错误')
                    logger.error(f"钉钉通知发送失败: {error_msg}")
                    return False, error_msg
        except Exception as e:
            logger.error(f"钉钉通知发送异常: {e}")
            return False, str(e)


# 自动注册插件
registry.register(DingTalkPlugin)
