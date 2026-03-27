"""群晖 NAS 远程关机插件"""
import logging
from typing import Dict, Any, List
import httpx
from hooks.base import PreShutdownHook
from hooks.registry import registry
from utils.retry import async_retry

logger = logging.getLogger(__name__)


class SynologyShutdownHook(PreShutdownHook):
    """群晖 NAS 远程关机插件"""
    
    hook_id = "synology_shutdown"
    hook_name = "群晖 NAS 关机"
    hook_description = "通过 Synology Web API 远程关机群晖 NAS"
    supported_actions = ["shutdown", "reboot"]
    
    @classmethod
    def get_config_schema(cls) -> List[Dict[str, Any]]:
        return [
            {
                "key": "host",
                "label": "NAS 地址",
                "type": "text",
                "required": True,
                "placeholder": "192.168.1.10",
                "description": "群晖 NAS 的 IP 地址或域名（不包含 http://）"
            },
            {
                "key": "port",
                "label": "端口",
                "type": "number",
                "required": False,
                "default": 5001,
                "placeholder": "5001",
                "description": "DSM 端口，HTTPS 默认 5001，HTTP 默认 5000"
            },
            {
                "key": "username",
                "label": "用户名",
                "type": "text",
                "required": True,
                "placeholder": "admin",
                "description": "DSM 管理员账号"
            },
            {
                "key": "password",
                "label": "密码",
                "type": "password",
                "required": True,
                "placeholder": "DSM 登录密码",
                "description": "DSM 管理员密码（明文存储，请注意安全）"
            },
            {
                "key": "use_https",
                "label": "使用 HTTPS",
                "type": "select",
                "required": False,
                "default": "true",
                "options": [
                    {"value": "true", "label": "是"},
                    {"value": "false", "label": "否"}
                ],
                "description": "是否使用 HTTPS 连接（推荐）"
            },
            {
                "key": "mac_address",
                "label": "MAC 地址（WOL）",
                "type": "text",
                "required": False,
                "placeholder": "AA:BB:CC:DD:EE:FF",
                "description": "用于 Wake On LAN 唤醒的 MAC 地址（可选）"
            },
            {
                "key": "broadcast_address",
                "label": "广播地址",
                "type": "text",
                "required": False,
                "default": "255.255.255.255",
                "placeholder": "255.255.255.255",
                "description": "WOL 广播地址，默认 255.255.255.255"
            },
            {
                "key": "log_command",
                "label": "日志查看命令（可选）",
                "type": "text",
                "required": False,
                "placeholder": "cat /var/log/messages | tail -100",
                "description": "自定义日志查看命令。留空则使用系统默认命令"
            }
        ]
    
    def validate_config(self):
        if "host" not in self.config or not self.config["host"]:
            raise ValueError("NAS 地址不能为空")
        
        if "username" not in self.config or not self.config["username"]:
            raise ValueError("用户名不能为空")
        
        if "password" not in self.config or not self.config["password"]:
            raise ValueError("密码不能为空")
    
    async def execute(self) -> bool:
        """执行群晖 NAS 关机（带重试）"""
        host = self.config["host"]
        port = self.config.get("port", 5001)
        username = self.config["username"]
        password = self.config["password"]
        use_https = self.config.get("use_https", "true") == "true"
        
        protocol = "https" if use_https else "http"
        base_url = f"{protocol}://{host}:{port}"
        
        async def _login():
            """登录获取 SID（带重试）"""
            async with httpx.AsyncClient(verify=False, timeout=30) as client:
                auth_url = f"{base_url}/webapi/auth.cgi"
                auth_params = {
                    "api": "SYNO.API.Auth",
                    "version": "3",
                    "method": "login",
                    "account": username,
                    "passwd": password,
                    "session": "FileStation",
                    "format": "sid"
                }
                
                auth_response = await client.get(auth_url, params=auth_params)
                auth_data = auth_response.json()
                
                if not auth_data.get("success"):
                    error_code = auth_data.get("error", {}).get("code", "unknown")
                    raise RuntimeError(f"Login failed with error code {error_code}")
                
                return auth_data["data"]["sid"]
        
        async def _shutdown(sid: str):
            """执行关机命令（带重试，但谨慎）"""
            async with httpx.AsyncClient(verify=False, timeout=30) as client:
                shutdown_url = f"{base_url}/webapi/entry.cgi"
                shutdown_params = {
                    "api": "SYNO.Core.System",
                    "version": "1",
                    "method": "shutdown",
                    "_sid": sid
                }
                
                shutdown_response = await client.get(shutdown_url, params=shutdown_params)
                shutdown_data = shutdown_response.json()
                
                if not shutdown_data.get("success"):
                    error_code = shutdown_data.get("error", {}).get("code", "unknown")
                    raise RuntimeError(f"Shutdown failed with error code {error_code}")
                
                return True
        
        try:
            # 步骤1：登录（重试 2 次）
            sid = await async_retry(
                _login,
                max_retries=2,
                base_delay=2.0,
                exponential_backoff=False,
                retry_exceptions=(httpx.HTTPError, RuntimeError),
                operation_name=f"Synology login ({host})"
            )
            
            # 步骤2：关机（不重试，避免重复关机命令）
            return await _shutdown(sid)
        
        except Exception as e:
            logger.error(f"Synology NAS operation failed after retries: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """测试群晖 NAS 连接"""
        host = self.config["host"]
        port = self.config.get("port", 5001)
        username = self.config["username"]
        password = self.config["password"]
        use_https = self.config.get("use_https", "true") == "true"
        
        protocol = "https" if use_https else "http"
        base_url = f"{protocol}://{host}:{port}"
        
        try:
            async with httpx.AsyncClient(verify=False, timeout=15) as client:
                # 尝试登录
                auth_url = f"{base_url}/webapi/auth.cgi"
                auth_params = {
                    "api": "SYNO.API.Auth",
                    "version": "3",
                    "method": "login",
                    "account": username,
                    "passwd": password,
                    "session": "FileStation",
                    "format": "sid"
                }
                
                auth_response = await client.get(auth_url, params=auth_params)
                auth_data = auth_response.json()
                
                if auth_data.get("success"):
                    # 登出
                    sid = auth_data["data"]["sid"]
                    logout_params = {
                        "api": "SYNO.API.Auth",
                        "version": "1",
                        "method": "logout",
                        "session": "FileStation",
                        "_sid": sid
                    }
                    await client.get(auth_url, params=logout_params)
                    
                    return True
                else:
                    logger.error(f"Connection test to Synology NAS failed: login failed")
                    return False
        
        except Exception as e:
            logger.error(f"Connection test to Synology NAS failed: {e}")
            return False


# 自动注册插件
registry.register(SynologyShutdownHook)
