"""通用 HTTP API 关机插件"""
import logging
import json
from typing import Dict, Any, List
import httpx
from hooks.base import PreShutdownHook
from hooks.registry import registry
from utils.retry import async_retry

logger = logging.getLogger(__name__)


class HTTPAPIHook(PreShutdownHook):
    """通用 HTTP API 关机插件"""
    
    hook_id = "http_api"
    hook_name = "HTTP API 调用"
    hook_description = "通过自定义 HTTP API 调用实现关机或其他操作"
    supported_actions = ["shutdown"]
    
    @classmethod
    def get_config_schema(cls) -> List[Dict[str, Any]]:
        return [
            {
                "key": "url",
                "label": "API URL",
                "type": "text",
                "required": True,
                "placeholder": "https://example.com/api/shutdown",
                "description": "完整的 API 地址（必须以 http:// 或 https:// 开头）"
            },
            {
                "key": "method",
                "label": "HTTP 方法",
                "type": "select",
                "required": False,
                "default": "POST",
                "options": [
                    {"value": "GET", "label": "GET"},
                    {"value": "POST", "label": "POST"},
                    {"value": "PUT", "label": "PUT"}
                ],
                "description": "HTTP 请求方法"
            },
            {
                "key": "headers",
                "label": "请求头 (JSON 格式)",
                "type": "textarea",
                "required": False,
                "placeholder": '{"Authorization": "Bearer token123", "Content-Type": "application/json"}',
                "description": "自定义 HTTP 请求头，JSON 格式"
            },
            {
                "key": "body",
                "label": "请求体 (JSON 格式)",
                "type": "textarea",
                "required": False,
                "placeholder": '{"action": "shutdown", "delay": 60}',
                "description": "请求体内容，JSON 格式（仅 POST/PUT）"
            },
            {
                "key": "expected_status",
                "label": "预期状态码",
                "type": "number",
                "required": False,
                "default": 200,
                "placeholder": "200",
                "description": "成功时的 HTTP 状态码"
            },
            {
                "key": "timeout",
                "label": "超时时间（秒）",
                "type": "number",
                "required": False,
                "default": 30,
                "placeholder": "30",
                "description": "请求超时时间"
            }
        ]
    
    def validate_config(self):
        if "url" not in self.config or not self.config["url"]:
            raise ValueError("API URL 不能为空")
        
        url = self.config["url"]
        if not url.startswith("http://") and not url.startswith("https://"):
            raise ValueError("API URL 必须以 http:// 或 https:// 开头")
        
        # 验证 headers 格式
        headers_str = self.config.get("headers", "").strip()
        if headers_str:
            try:
                json.loads(headers_str)
            except json.JSONDecodeError:
                raise ValueError("请求头必须是有效的 JSON 格式")
        
        # 验证 body 格式
        body_str = self.config.get("body", "").strip()
        if body_str:
            try:
                json.loads(body_str)
            except json.JSONDecodeError:
                raise ValueError("请求体必须是有效的 JSON 格式")
    
    async def execute(self) -> bool:
        """执行 HTTP API 调用（带重试）"""
        url = self.config["url"]
        method = self.config.get("method", "POST").upper()
        headers_str = self.config.get("headers", "").strip()
        body_str = self.config.get("body", "").strip()
        expected_status = self.config.get("expected_status", 200)
        timeout = self.config.get("timeout", 30)
        
        # 准备请求头
        headers = {}
        if headers_str:
            try:
                headers = json.loads(headers_str)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse headers JSON, using empty headers")
        
        # 准备请求体
        body = None
        if body_str and method in ["POST", "PUT"]:
            try:
                body = json.loads(body_str)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse body JSON, using empty body")
        
        async def _do_request():
            """执行单次 HTTP 请求"""
            async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, json=body, headers=headers)
                elif method == "PUT":
                    response = await client.put(url, json=body, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                if response.status_code != expected_status:
                    raise RuntimeError(
                        f"Unexpected status code: {response.status_code} (expected {expected_status})"
                    )
                return True
        
        try:
            # 使用 async_retry 进行重试，带指数退避
            return await async_retry(
                _do_request,
                max_retries=2,
                base_delay=3.0,
                exponential_backoff=True,
                max_delay=10.0,
                retry_exceptions=(httpx.HTTPError, httpx.TimeoutException, RuntimeError),
                operation_name=f"HTTP API Hook ({method} {url})"
            )
        except Exception as e:
            logger.error(f"HTTP API Hook failed after retries: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """测试 HTTP API 连接"""
        return await self.execute()


# 自动注册插件
registry.register(HTTPAPIHook)
