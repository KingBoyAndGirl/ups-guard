"""Agent 客户端关机插件"""
import logging
from typing import Dict, Any, List
from hooks.base import PreShutdownHook
from hooks.registry import registry

logger = logging.getLogger(__name__)


class AgentShutdownHook(PreShutdownHook):
    """Agent 客户端关机插件（无需 SSH，安装客户端即可）"""

    hook_id = "agent_shutdown"
    hook_name = "Agent 客户端关机"
    hook_description = (
        "通过 Agent 客户端远程关机，无需开启 SSH 或配置防火墙。"
        "在目标设备上安装 UPS Guard Agent 客户端，客户端主动反连服务端即可。"
    )
    supported_actions = ["shutdown", "reboot", "sleep", "hibernate"]

    @classmethod
    def get_config_schema(cls) -> List[Dict[str, Any]]:
        return [
            {
                "key": "agent_id",
                "label": "Agent ID",
                "type": "text",
                "required": True,
                "placeholder": "abc123",
                "description": "Agent 客户端的唯一 ID（在客户端配置中查看）",
            },
            {
                "key": "shutdown_delay",
                "label": "关机延迟（秒）",
                "type": "number",
                "required": False,
                "default": 60,
                "placeholder": "60",
                "description": "执行关机前的等待秒数",
            },
            {
                "key": "shutdown_message",
                "label": "关机提示消息",
                "type": "text",
                "required": False,
                "placeholder": "UPS 电量不足，即将关机",
                "description": "显示给用户的关机提示消息",
            },
            {
                "key": "pre_commands",
                "label": "预关机命令（可选）",
                "type": "textarea",
                "required": False,
                "placeholder": "echo pre-shutdown\nsync",
                "description": "关机前在目标设备上逐行执行的命令",
            },
            {
                "key": "mac_address",
                "label": "MAC 地址（可选）",
                "type": "text",
                "required": False,
                "placeholder": "AA:BB:CC:DD:EE:FF",
                "description": "用于 WOL 唤醒（预留，暂未使用）",
            },
            {
                "key": "broadcast_address",
                "label": "广播地址（可选）",
                "type": "text",
                "required": False,
                "default": "255.255.255.255",
                "placeholder": "255.255.255.255",
                "description": "WOL 广播地址（预留，暂未使用）",
            },
        ]

    def validate_config(self):
        agent_id = self.config.get("agent_id", "").strip()
        if not agent_id:
            raise ValueError("agent_id 不能为空")

    async def _send_action(self, action: str) -> bool:
        """通用发送动作方法"""
        from services.agent_manager import get_agent_manager

        agent_id = self.config.get("agent_id", "").strip()
        manager = get_agent_manager()

        params: Dict[str, Any] = {
            "delay": self.config.get("shutdown_delay", 60),
            "message": self.config.get("shutdown_message", ""),
        }

        result = await manager.send_command(agent_id, action, params)
        success = result.get("success", False)
        if not success:
            logger.error(
                f"AgentShutdownHook: action={action} agent={agent_id} failed: {result.get('message')}"
            )
        return success

    async def execute(self) -> bool:
        """执行 Agent 关机"""
        from services.agent_manager import get_agent_manager

        agent_id = self.config.get("agent_id", "").strip()
        manager = get_agent_manager()

        # 先执行预关机命令（逐条）
        pre_commands_str = self.config.get("pre_commands", "").strip()
        if pre_commands_str:
            pre_commands = [cmd.strip() for cmd in pre_commands_str.split("\n") if cmd.strip()]
            for cmd in pre_commands:
                result = await manager.send_command(
                    agent_id, "execute", {"command": cmd}
                )
                if not result.get("success", False):
                    logger.warning(
                        f"AgentShutdownHook: pre_command failed: {cmd} — {result.get('message')}"
                    )

        # 执行关机
        return await self._send_action("shutdown")

    async def test_connection(self) -> bool:
        """检测 Agent 是否在线"""
        from services.agent_manager import get_agent_manager

        agent_id = self.config.get("agent_id", "").strip()
        manager = get_agent_manager()
        return await manager.check_agent_online(agent_id)

    async def reboot(self) -> bool:
        """重启设备"""
        return await self._send_action("reboot")

    async def sleep(self) -> bool:
        """睡眠设备"""
        return await self._send_action("sleep")

    async def hibernate(self) -> bool:
        """休眠设备"""
        return await self._send_action("hibernate")


# 自动注册插件
registry.register(AgentShutdownHook)
