"""Windows SSH 远程关机插件"""
import asyncio
import logging
from typing import Dict, Any, List
import asyncssh
from hooks.base import PreShutdownHook
from hooks.registry import registry

logger = logging.getLogger(__name__)


class WindowsShutdownHook(PreShutdownHook):
    """Windows SSH 远程关机插件"""
    
    hook_id = "windows_shutdown"
    hook_name = "Windows 远程关机 (SSH)"
    hook_description = "通过 SSH 连接远程 Windows 主机执行关机命令（需要 OpenSSH Server）"
    supported_actions = ["shutdown", "reboot", "sleep", "hibernate"]
    
    @classmethod
    def get_config_schema(cls) -> List[Dict[str, Any]]:
        return [
            {
                "key": "host",
                "label": "主机地址",
                "type": "text",
                "required": True,
                "placeholder": "192.168.1.101",
                "description": "目标 Windows 主机的 IP 地址或域名"
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
                "placeholder": "Administrator",
                "description": "SSH 登录用户名"
            },
            {
                "key": "password",
                "label": "密码",
                "type": "password",
                "required": True,
                "placeholder": "Windows 登录密码",
                "description": "SSH 登录密码（明文存储，请注意安全）"
            },
            {
                "key": "shutdown_command",
                "label": "关机命令",
                "type": "text",
                "required": False,
                "default": "shutdown /s /t 60 /c \"UPS power lost\"",
                "placeholder": "shutdown /s /t 60 /c \"UPS power lost\"",
                "description": "执行的关机命令（/s=关机, /t=延迟秒数, /c=注释）"
            },
            {
                "key": "pre_commands",
                "label": "预关机命令（可选）",
                "type": "textarea",
                "required": False,
                "placeholder": "Stop-Service -Name MyService\nStop-Process -Name myapp",
                "description": "关机前先执行的 PowerShell 命令，每行一条"
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
                "placeholder": "powershell.exe -Command \"Get-EventLog -LogName System -Newest 50 | Format-List\"",
                "description": "自定义日志查看命令。留空则使用系统默认命令"
            }
        ]
    
    def validate_config(self):
        if "host" not in self.config or not self.config["host"]:
            raise ValueError("主机地址不能为空")
        
        if "username" not in self.config or not self.config["username"]:
            raise ValueError("用户名不能为空")
        
        if "password" not in self.config or not self.config["password"]:
            raise ValueError("密码不能为空")
    
    async def execute(self) -> bool:
        """执行 Windows 远程关机"""
        host = self.config["host"]
        port = self.config.get("port", 22)
        username = self.config["username"]
        password = self.config["password"]
        shutdown_command = self.config.get("shutdown_command", "shutdown /s /t 60 /c \"UPS power lost\"")
        pre_commands_str = self.config.get("pre_commands", "").strip()
        
        try:
            # 连接 SSH
            async with asyncssh.connect(
                host=host,
                port=port,
                username=username,
                password=password,
                known_hosts=None  # 禁用 host key 检查
            ) as conn:

                # 执行预关机命令
                if pre_commands_str:
                    pre_commands = [cmd.strip() for cmd in pre_commands_str.split("\n") if cmd.strip()]
                    for cmd in pre_commands:
                        # 使用 PowerShell 执行命令
                        ps_cmd = f"powershell.exe -Command \"{cmd}\""
                        result = await conn.run(ps_cmd, check=False, timeout=30)
                        if result.exit_status != 0:
                            logger.warning(f"Pre-command failed on {host}: {cmd} (exit {result.exit_status})")

                # 执行关机命令
                try:
                    # Windows shutdown 命令通常会成功返回
                    result = await asyncio.wait_for(conn.run(shutdown_command, check=False), timeout=10)
                    if result.exit_status == 0:
                        return True
                    else:
                        logger.error(f"Shutdown command failed on {host} (exit {result.exit_status})")
                        return False
                except asyncio.TimeoutError:
                    logger.warning(f"Shutdown command on {host} timed out (might still succeed)")
                    return True
        
        except asyncssh.Error as e:
            logger.error(f"SSH error for {host}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to execute Windows shutdown on {host}: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """测试 Windows SSH 连接"""
        host = self.config["host"]
        port = self.config.get("port", 22)
        username = self.config["username"]
        password = self.config["password"]
        
        try:
            async with asyncssh.connect(
                host=host,
                port=port,
                username=username,
                password=password,
                known_hosts=None
            ) as conn:
                result = await conn.run("echo SSH connection test successful", check=True, timeout=10)
                return True
        
        except Exception as e:
            logger.error(f"SSH connection test to {host} failed: {e}")
            return False
    
    async def _execute_windows_command(self, command: str, operation_name: str = "operation") -> bool:
        """通用 Windows SSH 命令执行方法"""
        host = self.config["host"]
        port = self.config.get("port", 22)
        username = self.config["username"]
        password = self.config["password"]
        
        try:
            async with asyncssh.connect(
                host,
                port=port,
                username=username,
                password=password,
                known_hosts=None
            ) as conn:

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
        reboot_command = "shutdown /r /t 0"
        return await self._execute_windows_command(reboot_command, "reboot")
    
    async def sleep(self) -> bool:
        """睡眠设备"""
        sleep_command = "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"
        return await self._execute_windows_command(sleep_command, "sleep")
    
    async def hibernate(self) -> bool:
        """休眠设备"""
        hibernate_command = "shutdown /h"
        return await self._execute_windows_command(hibernate_command, "hibernate")



# 自动注册插件
registry.register(WindowsShutdownHook)
