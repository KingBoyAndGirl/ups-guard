"""Server酱通知插件"""
import httpx
import logging
from typing import Dict, Any, List
from plugins.base import NotifierPlugin
from plugins.registry import registry

logger = logging.getLogger(__name__)


class ServerChanPlugin(NotifierPlugin):
    """Server酱通知插件 (https://sct.ftqq.com/)"""
    
    plugin_id = "serverchan"
    plugin_name = "Server酱"
    plugin_description = "通过 Server酱 发送微信通知"
    
    @classmethod
    def get_config_schema(cls) -> List[Dict[str, Any]]:
        return [
            {
                "key": "sendkey",
                "label": "SendKey",
                "type": "password",
                "required": True,
                "placeholder": "SCT开头的SendKey",
                "description": "从 https://sct.ftqq.com/ 获取"
            }
        ]
    
    def validate_config(self):
        if "sendkey" not in self.config or not self.config["sendkey"]:
            raise ValueError("Server酱 SendKey 不能为空")
        
        if not self.config["sendkey"].startswith("SCT"):
            raise ValueError("Server酱 SendKey 格式不正确，应以 SCT 开头")
    
    async def send(self, title: str, content: str, level: str = "info", timestamp: str = ""):
        """
        发送 Server酱 通知
        
        API 文档: https://sct.ftqq.com/sendkey
        """
        sendkey = self.config["sendkey"]
        url = f"https://sctapi.ftqq.com/{sendkey}.send"
        
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
            "title": title,
            "desp": structured_content
        }
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, data=data)
                result = response.json()
                
                if result.get("code") == 0:
                    return True, None
                else:
                    error_msg = result.get('message', '未知错误')
                    logger.error(f"Server酱通知发送失败: {error_msg}")
                    return False, error_msg
        except Exception as e:
            logger.error(f"Server酱通知发送异常: {e}")
            return False, str(e)


# 自动注册插件
registry.register(ServerChanPlugin)
