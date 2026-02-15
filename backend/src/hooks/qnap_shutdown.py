"""威联通 NAS 远程关机插件"""
import logging
from typing import Dict, Any, List
import httpx
from hooks.base import PreShutdownHook
from hooks.registry import registry
from utils.retry import async_retry

logger = logging.getLogger(__name__)


class QNAPShutdownHook(PreShutdownHook):
    """威联通 NAS 远程关机插件"""
    
    hook_id = "qnap_shutdown"
    hook_name = "威联通 NAS 关机"
    hook_description = "通过 QNAP CGI API 远程关机威联通 NAS"
    supported_actions = ["shutdown", "reboot"]
    
    @classmethod
    def get_config_schema(cls) -> List[Dict[str, Any]]:
        return [
            {
                "key": "host",
                "label": "NAS 地址",
                "type": "text",
                "required": True,
                "placeholder": "192.168.1.11",
                "description": "威联通 NAS 的 IP 地址或域名（不包含 http://）"
            },
            {
                "key": "port",
                "label": "端口",
                "type": "number",
                "required": False,
                "default": 443,
                "placeholder": "443",
                "description": "QTS 端口，HTTPS 默认 443，HTTP 默认 8080"
            },
            {
                "key": "username",
                "label": "用户名",
                "type": "text",
                "required": True,
                "placeholder": "admin",
                "description": "QTS 管理员账号"
            },
            {
                "key": "password",
                "label": "密码",
                "type": "password",
                "required": True,
                "placeholder": "QTS 登录密码",
                "description": "QTS 管理员密码（明文存储，请注意安全）"
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
                "key": "log_command",
                "label": "日志查看命令（可选）",
                "type": "text",
                "required": False,
                "placeholder": "cat /var/log/messages | tail -100",
                "description": "自定义日志查看命令。留空则使用系统默认命令"
            },
            {
                "key": "mac_address",
                "label": "MAC 地址（WOL）",
                "type": "text",
                "required": False,
                "placeholder": "AA:BB:CC:DD:EE:FF",
                "description": "设备的 MAC 地址，用于 Wake On LAN（来电后自动唤醒设备）"
            },
            {
                "key": "broadcast_address",
                "label": "广播地址（可选）",
                "type": "text",
                "required": False,
                "placeholder": "255.255.255.255",
                "description": "网络广播地址，默认 255.255.255.255。跨子网时需要指定目标网段的广播地址"
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
        """执行威联通 NAS 关机（带重试）"""
        host = self.config["host"]
        port = self.config.get("port", 443)
        username = self.config["username"]
        password = self.config["password"]
        use_https = self.config.get("use_https", "true") == "true"
        
        protocol = "https" if use_https else "http"
        base_url = f"{protocol}://{host}:{port}"
        
        async def _login():
            """登录获取 sid（带重试）"""
            async with httpx.AsyncClient(verify=False, timeout=30) as client:
                login_url = f"{base_url}/cgi-bin/authLogin.cgi"
                login_data = {
                    "user": username,
                    "pwd": password
                }
                
                login_response = await client.post(login_url, data=login_data)
                login_text = login_response.text
                
                # 解析响应获取 sid
                if "<authSid>" in login_text:
                    import re
                    match = re.search(r"<authSid>([^<]+)</authSid>", login_text)
                    if not match:
                        raise RuntimeError("Failed to parse QNAP login response")
                    sid = match.group(1)
                else:
                    sid = login_text.strip()
                
                if not sid or sid == "0" or "error" in sid.lower():
                    raise RuntimeError("QNAP login failed: invalid sid")
                
                return sid
        
        async def _shutdown(sid: str):
            """执行关机命令（带重试，但谨慎）"""
            async with httpx.AsyncClient(verify=False, timeout=30) as client:
                shutdown_url = f"{base_url}/cgi-bin/sys/sysRequest.cgi"
                shutdown_params = {
                    "subfunc": "power_mgmt",
                    "apply": "shutdown",
                    "sid": sid
                }
                
                shutdown_response = await client.get(shutdown_url, params=shutdown_params)
                shutdown_text = shutdown_response.text
                
                # QNAP API 通常返回 XML，检查是否成功
                if "success" not in shutdown_text.lower() and shutdown_response.status_code != 200:
                    raise RuntimeError(f"QNAP shutdown failed: {shutdown_text[:100]}")
                
                return True
        
        try:
            # 步骤1：登录（重试 2 次）
            sid = await async_retry(
                _login,
                max_retries=2,
                base_delay=2.0,
                exponential_backoff=False,
                retry_exceptions=(httpx.HTTPError, RuntimeError),
                operation_name=f"QNAP login ({host})"
            )
            
            # 步骤2：关机（不重试，避免重复关机命令）
            return await _shutdown(sid)
        
        except Exception as e:
            logger.error(f"QNAP NAS operation failed after retries: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """测试威联通 NAS 连接"""
        host = self.config["host"]
        port = self.config.get("port", 443)
        username = self.config["username"]
        password = self.config["password"]
        use_https = self.config.get("use_https", "true") == "true"
        
        protocol = "https" if use_https else "http"
        base_url = f"{protocol}://{host}:{port}"
        
        try:
            async with httpx.AsyncClient(verify=False, timeout=15) as client:
                # 尝试登录
                login_url = f"{base_url}/cgi-bin/authLogin.cgi"
                login_data = {
                    "user": username,
                    "pwd": password
                }
                
                login_response = await client.post(login_url, data=login_data)
                login_text = login_response.text
                
                # 解析响应
                if "<authSid>" in login_text:
                    import re
                    match = re.search(r"<authSid>([^<]+)</authSid>", login_text)
                    if match and match.group(1) != "0":
                        return True
                else:
                    sid = login_text.strip()
                    if sid and sid != "0" and "error" not in sid.lower():
                        return True
                
                logger.error(f"Connection test to QNAP NAS failed: login failed")
                return False
        
        except Exception as e:
            logger.error(f"Connection test to QNAP NAS failed: {e}")
            return False


# 自动注册插件
registry.register(QNAPShutdownHook)
