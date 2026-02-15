"""PushPlus 通知插件"""
import httpx
import logging
from typing import Dict, Any, List
from plugins.base import NotifierPlugin
from plugins.registry import registry

logger = logging.getLogger(__name__)


class PushPlusPlugin(NotifierPlugin):
    """PushPlus 通知插件 (http://www.pushplus.plus/)"""
    
    plugin_id = "pushplus"
    plugin_name = "PushPlus"
    plugin_description = "通过 PushPlus 发送微信通知"
    
    @classmethod
    def get_config_schema(cls) -> List[Dict[str, Any]]:
        return [
            {
                "key": "token",
                "label": "Token",
                "type": "password",
                "required": True,
                "placeholder": "PushPlus Token",
                "description": "从 http://www.pushplus.plus/ 获取"
            },
            {
                "key": "topic",
                "label": "群组编码 (可选)",
                "type": "text",
                "required": False,
                "placeholder": "不填则发送给自己",
                "description": "填写后将发送到指定群组"
            }
        ]
    
    def validate_config(self):
        if "token" not in self.config or not self.config["token"]:
            raise ValueError("PushPlus Token 不能为空")
    
    async def send(self, title: str, content: str, level: str = "info", timestamp: str = ""):
        """
        发送 PushPlus 通知
        
        API 文档: http://www.pushplus.plus/doc/
        """
        token = self.config["token"]
        topic = self.config.get("topic", "")
        url = "http://www.pushplus.plus/send"
        
        # 根据级别添加图标
        icon_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌"
        }
        icon = icon_map.get(level, "")
        
        # 构建结构化消息
        structured_content = f"标题: {title}\n内容: {content}\n级别: {icon} {level}\n时间: {timestamp}"
        
        data = {
            "token": token,
            "title": title,
            "content": structured_content,
            "template": "txt"
        }
        
        if topic:
            data["topic"] = topic
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json=data)
                result = response.json()
                
                if result.get("code") == 200:
                    return True, None
                else:
                    error_msg = result.get('msg', '未知错误')
                    logger.error(f"PushPlus通知发送失败: {error_msg}")
                    return False, error_msg
        except Exception as e:
            logger.error(f"PushPlus通知发送异常: {e}")
            return False, str(e)


# 自动注册插件
registry.register(PushPlusPlugin)
