"""通用 Webhook 通知插件"""
import httpx
import logging
import json
from datetime import datetime
from typing import Dict, Any, List
from plugins.base import NotifierPlugin
from plugins.registry import registry

logger = logging.getLogger(__name__)


class WebhookPlugin(NotifierPlugin):
    """通用 Webhook 通知插件"""
    
    plugin_id = "webhook"
    plugin_name = "Webhook"
    plugin_description = "发送 HTTP 请求到自定义 Webhook URL"
    
    @classmethod
    def get_config_schema(cls) -> List[Dict[str, Any]]:
        return [
            {
                "key": "url",
                "label": "Webhook URL",
                "type": "text",
                "required": True,
                "placeholder": "https://example.com/webhook",
                "description": "接收通知的 URL"
            },
            {
                "key": "method",
                "label": "HTTP 方法",
                "type": "select",
                "required": False,
                "default": "POST",
                "options": [
                    {"value": "POST", "label": "POST"},
                    {"value": "GET", "label": "GET"}
                ],
                "description": "HTTP 请求方法"
            },
            {
                "key": "headers",
                "label": "自定义请求头 (JSON 格式)",
                "type": "textarea",
                "required": False,
                "placeholder": '{"Authorization": "Bearer token", "X-Custom": "value"}',
                "description": "可选的自定义 HTTP 请求头，JSON 格式"
            },
            {
                "key": "template",
                "label": "消息体模板 (JSON 格式)",
                "type": "textarea",
                "required": False,
                "placeholder": '{"text": "{title}", "description": "{content}", "level": "{level}", "time": "{timestamp}"}',
                "description": "支持变量: {title}, {content}, {level}, {timestamp}"
            }
        ]
    
    def validate_config(self):
        if "url" not in self.config or not self.config["url"]:
            raise ValueError("Webhook URL 不能为空")
        
        url = self.config["url"]
        if not url.startswith("http://") and not url.startswith("https://"):
            raise ValueError("Webhook URL 必须以 http:// 或 https:// 开头")
        
        # 验证自定义请求头格式
        headers_str = self.config.get("headers", "").strip()
        if headers_str:
            try:
                json.loads(headers_str)
            except json.JSONDecodeError:
                raise ValueError("自定义请求头必须是有效的 JSON 格式")
        
        # 验证消息体模板格式
        template_str = self.config.get("template", "").strip()
        if template_str:
            try:
                json.loads(template_str)
            except json.JSONDecodeError:
                raise ValueError("消息体模板必须是有效的 JSON 格式")
    
    async def send(self, title: str, content: str, level: str = "info", timestamp: str = ""):
        """
        发送 Webhook 通知
        """
        url = self.config["url"]
        method = self.config.get("method", "POST").upper()
        headers_str = self.config.get("headers", "").strip()
        template_str = self.config.get("template", "").strip()
        
        # 准备请求头
        headers = {"Content-Type": "application/json"}
        if headers_str:
            try:
                custom_headers = json.loads(headers_str)
                headers.update(custom_headers)
            except json.JSONDecodeError:
                logger.warning("自定义请求头 JSON 解析失败，使用默认请求头")
        
        # 如果没有传入timestamp，生成一个
        if not timestamp:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if template_str:
            # 使用自定义模板
            try:
                template = json.loads(template_str)
                # 递归替换模板中的变量
                data = self._replace_template_vars(template, {
                    "title": title,
                    "content": content,
                    "level": level,
                    "timestamp": timestamp
                })
            except json.JSONDecodeError:
                logger.warning("消息体模板 JSON 解析失败，使用默认格式")
                data = self._get_default_payload(title, content, level, timestamp)
        else:
            # 使用默认格式
            data = self._get_default_payload(title, content, level, timestamp)
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                if method == "POST":
                    response = await client.post(url, json=data, headers=headers)
                else:  # GET
                    response = await client.get(url, headers=headers)
                
                if response.status_code < 400:
                    return True, None
                else:
                    error_msg = f"HTTP {response.status_code}"
                    logger.error(f"Webhook 通知发送失败: {error_msg}")
                    return False, error_msg
        except Exception as e:
            logger.error(f"Webhook 通知发送异常: {e}")
            return False, str(e)

    def _get_default_payload(self, title: str, content: str, level: str, timestamp: str) -> Dict[str, Any]:
        """获取默认消息体格式"""
        return {
            "title": title,
            "content": content,
            "level": level,
            "timestamp": timestamp
        }
    
    def _replace_template_vars(self, template: Any, vars: Dict[str, str]) -> Any:
        """递归替换模板中的变量"""
        if isinstance(template, str):
            # 替换字符串中的变量
            result = template
            for key, value in vars.items():
                result = result.replace(f"{{{key}}}", value)
            return result
        elif isinstance(template, dict):
            # 递归处理字典
            return {k: self._replace_template_vars(v, vars) for k, v in template.items()}
        elif isinstance(template, list):
            # 递归处理列表
            return [self._replace_template_vars(item, vars) for item in template]
        else:
            # 其他类型直接返回
            return template


# 自动注册插件
registry.register(WebhookPlugin)
