"""SSH 远程关机插件（Linux/macOS）"""
import asyncio
import logging
from typing import Dict, Any, List
import asyncssh
from hooks.base import PreShutdownHook
from hooks.registry import registry
from utils.retry import async_retry

logger = logging.getLogger(__name__)


class SSHShutdownHook(PreShutdownHook):
    """SSH 远程关机插件（Linux/macOS）"""
    
    hook_id = "ssh_shutdown"
    hook_name = "SSH 远程关机 (Linux/macOS)"
    hook_description = "通过 SSH 连接远程 Linux 或 macOS 主机执行关机命令"
    supported_actions = ["shutdown", "reboot", "sleep", "hibernate"]
    
    @classmethod
    def get_config_schema(cls) -> List[Dict[str, Any]]:
        return [
            {
                "key": "host",
                "label": "主机地址",
                "type": "text",
                "required": True,
                "placeholder": "192.168.1.100",
                "description": "目标主机的 IP 地址或域名"
            },
            {
                "key": "port",
                "label": "SSH 端口",
                "type": "number",
                "required": False,
                "default": 22,
                "placeholder": "22",
                "description": "SSH 服务端口，默认 22"
            },
            {
                "key": "username",
                "label": "用户名",
                "type": "text",
                "required": True,
                "placeholder": "root",
                "description": "SSH 登录用户名"
            },
            {
                "key": "auth_type",
                "label": "认证方式",
                "type": "select",
                "required": False,
                "default": "password",
                "options": [
                    {"value": "password", "label": "密码"},
                    {"value": "key", "label": "私钥"}
                ],
                "description": "SSH 认证方式"
            },
            {
                "key": "password",
                "label": "密码",
                "type": "password",
                "required": False,
                "placeholder": "SSH 登录密码",
                "description": "使用密码认证时必填（明文存储，请注意安全）"
            },
            {
                "key": "private_key",
                "label": "私钥",
                "type": "textarea",
                "required": False,
                "placeholder": "-----BEGIN OPENSSH PRIVATE KEY-----\n...\n-----END OPENSSH PRIVATE KEY-----",
                "description": "使用私钥认证时必填（PEM 格式）"
            },
            {
                "key": "shutdown_command",
                "label": "关机命令",
                "type": "text",
                "required": False,
                "default": "sudo shutdown -h now",
                "placeholder": "sudo shutdown -h now",
                "description": "执行的关机命令"
            },
            {
                "key": "pre_commands",
                "label": "预关机命令（可选）",
                "type": "textarea",
                "required": False,
                "placeholder": "# 懒猫微服示例：\ndocker stop docker pg-docker lzc-docker\n# 或停止所有容器：\ndocker stop $(docker ps -q)\n# 停止服务：\nsystemctl stop nginx",
                "description": "关机前先执行的命令，每行一条。可用于停止 Docker 容器、系统服务等。支持懒猫微服的 docker/pg-docker/lzc-docker 容器"
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
                "placeholder": "journalctl --no-pager -n 100 --since '1 hour ago'",
                "description": "自定义日志查看命令。留空则使用系统默认命令"
            }
        ]
    
    def validate_config(self):
        if "host" not in self.config or not self.config["host"]:
            raise ValueError("主机地址不能为空")
        
        if "username" not in self.config or not self.config["username"]:
            raise ValueError("用户名不能为空")
        
        auth_type = self.config.get("auth_type", "password")
        if auth_type == "password":
            if "password" not in self.config or not self.config["password"]:
                raise ValueError("使用密码认证时，密码不能为空")
        elif auth_type == "key":
            if "private_key" not in self.config or not self.config["private_key"]:
                raise ValueError("使用私钥认证时，私钥不能为空")
    
    async def execute(self) -> bool:
        """执行 SSH 远程关机（带连接重试）"""
        host = self.config["host"]
        port = self.config.get("port", 22)
        username = self.config["username"]
        auth_type = self.config.get("auth_type", "password")
        shutdown_command = self.config.get("shutdown_command", "sudo shutdown -h now")
        pre_commands_str = self.config.get("pre_commands", "").strip()
        
        # 准备认证参数
        connect_kwargs = {
            "host": host,
            "port": port,
            "username": username,
            "known_hosts": None  # 禁用 host key 检查
        }
        
        if auth_type == "password":
            connect_kwargs["password"] = self.config["password"]
        else:
            # 使用私钥认证
            connect_kwargs["client_keys"] = [self.config["private_key"]]
        
        async def _connect_and_execute():
            """连接并执行命令（带连接重试）"""
            # 连接 SSH
            async with asyncssh.connect(**connect_kwargs) as conn:
                # 执行预关机命令
                if pre_commands_str:
                    pre_commands = [cmd.strip() for cmd in pre_commands_str.split("\n") if cmd.strip()]
                    for cmd in pre_commands:
                        result = await conn.run(cmd, check=False, timeout=30)
                        if result.exit_status != 0:
                            logger.warning(f"Pre-command failed on {host}: {cmd} (exit {result.exit_status})")
                
                # 执行关机命令（不等待响应，因为连接会断开）
                try:
                    await asyncio.wait_for(conn.run(shutdown_command, check=False), timeout=5)
                except (asyncio.TimeoutError, asyncssh.ConnectionLost, asyncssh.DisconnectError):
                    # 预期的行为：关机命令会导致连接断开
                    pass
                
                return True
        
        try:
            # 使用 async_retry 进行连接重试（仅连接阶段）
            # 关机命令本身不重试，避免重复关机
            return await async_retry(
                _connect_and_execute,
                max_retries=2,
                base_delay=3.0,
                exponential_backoff=False,  # 固定延迟更适合关机场景
                retry_exceptions=(asyncssh.Error, OSError, ConnectionError),
                operation_name=f"SSH connection to {host}:{port}"
            )
        except Exception as e:
            logger.error(f"SSH operation failed after retries: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """测试 SSH 连接（带重试）"""
        host = self.config["host"]
        port = self.config.get("port", 22)
        username = self.config["username"]
        auth_type = self.config.get("auth_type", "password")
        
        # 准备认证参数
        connect_kwargs = {
            "host": host,
            "port": port,
            "username": username,
            "known_hosts": None
        }
        
        if auth_type == "password":
            connect_kwargs["password"] = self.config["password"]
        else:
            connect_kwargs["client_keys"] = [self.config["private_key"]]
        
        async def _test_connect():
            """测试连接"""
            async with asyncssh.connect(**connect_kwargs) as conn:
                result = await conn.run("echo 'SSH connection test successful'", check=True, timeout=10)
                return True
        
        try:
            # 使用 async_retry 进行连接测试重试
            return await async_retry(
                _test_connect,
                max_retries=2,
                base_delay=3.0,
                exponential_backoff=False,
                retry_exceptions=(asyncssh.Error, OSError, ConnectionError),
                operation_name=f"SSH connection test to {host}:{port}"
            )
        except Exception as e:
            logger.error(f"SSH connection test failed after retries: {e}")
            return False
    
    async def _execute_ssh_command(self, command: str, operation_name: str = "operation") -> bool:
        """通用 SSH 命令执行方法"""
        host = self.config["host"]
        port = self.config.get("port", 22)
        username = self.config["username"]
        auth_type = self.config.get("auth_type", "password")
        
        try:
            # 准备认证参数
            connect_kwargs = {
                "host": host,
                "port": port,
                "username": username,
                "known_hosts": None
            }
            
            if auth_type == "password":
                connect_kwargs["password"] = self.config["password"]
            else:
                connect_kwargs["client_keys"] = [self.config["private_key"]]
            
            # 连接 SSH
            async with asyncssh.connect(**connect_kwargs) as conn:

                # 执行命令（不等待响应太久，因为连接可能会断开）
                try:
                    await asyncio.wait_for(conn.run(command, check=False), timeout=5)
                except (asyncio.TimeoutError, asyncssh.ConnectionLost, asyncssh.DisconnectError):
                    # 预期的行为：某些命令会导致连接断开
                    pass
                return True
        
        except asyncssh.Error as e:
            logger.error(f"SSH error for {host} during {operation_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to execute {operation_name} on {host}: {e}")
            return False
    
    async def reboot(self) -> bool:
        """重启设备"""
        reboot_command = "sudo reboot"
        return await self._execute_ssh_command(reboot_command, "reboot")
    
    async def sleep(self) -> bool:
        """睡眠设备（挂起到内存）"""
        sleep_command = "sudo systemctl suspend"
        return await self._execute_ssh_command(sleep_command, "sleep")
    
    async def hibernate(self) -> bool:
        """休眠设备（挂起到磁盘）"""
        hibernate_command = "sudo systemctl hibernate"
        return await self._execute_ssh_command(hibernate_command, "hibernate")



# 自动注册插件
registry.register(SSHShutdownHook)
