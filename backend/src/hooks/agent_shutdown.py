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
                "description": (
                    "向操作系统下发关机命令后的倒计时秒数（仅 Windows 生效，Linux/macOS 立即关机）。"
                    "预关机命令会在此倒计时开始前全部执行完毕。"
                ),
            },
            {
                "key": "shutdown_message",
                "label": "关机提示消息",
                "type": "text",
                "required": False,
                "placeholder": "UPS 电量不足，即将关机",
                "description": "显示给已登录用户的关机提示消息（仅 Windows 支持）",
            },
            {
                "key": "pre_commands",
                "label": "预关机命令（可选）",
                "type": "textarea",
                "required": False,
                "placeholder": "echo pre-shutdown\nsync",
                "description": (
                    "关机前在目标设备上逐行执行的命令（每行一条）。"
                    "所有命令执行完毕后才会发送关机指令，关机延迟倒计时从命令执行完毕后才开始。"
                    "⚠️ 请确保「任务超时」设置 ≥ 所有预关机命令预计耗时之和 + 关机延迟秒数，否则任务超时后关机命令将不会下发。"
                ),
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
        shutdown_delay = self.config.get("shutdown_delay", 60)

        # 先执行预关机命令（逐条），全部执行完后再发关机指令
        # 紧急关机时跳过预关机命令（没时间了）
        pre_commands_str = self.config.get("pre_commands", "").strip()
        if pre_commands_str and not self.urgent:
            pre_commands = [cmd.strip() for cmd in pre_commands_str.split("\n") if cmd.strip()]
            logger.info(
                f"AgentShutdownHook: running {len(pre_commands)} pre_command(s) on agent={agent_id} "
                f"before issuing shutdown (delay={shutdown_delay}s)"
            )
            for cmd in pre_commands:
                result = await manager.send_command(
                    agent_id, "execute", {"command": cmd}
                )
                if not result.get("success", False):
                    logger.warning(
                        f"AgentShutdownHook: pre_command failed: {cmd!r} — {result.get('message')}"
                    )
            logger.info(
                f"AgentShutdownHook: pre_commands complete, issuing shutdown with delay={shutdown_delay}s"
            )
        elif self.urgent and pre_commands_str:
            logger.warning(
                f"AgentShutdownHook: URGENT shutdown — skipping pre_commands for agent={agent_id}"
            )

        # 发送关机指令
        # 紧急时：缩短延迟到 10 秒，force=True 让 Agent 加 /f 强制关闭应用
        # 正常时：使用配置的延迟，force=False 让 Windows 自己处理
        params: Dict[str, Any] = {
            "delay": 10 if self.urgent else shutdown_delay,
            "message": self.config.get("shutdown_message", ""),
            "force": self.urgent,
        }

        if self.urgent:
            logger.warning(
                f"AgentShutdownHook: URGENT shutdown agent={agent_id} "
                f"delay=10s force=True"
            )

        result = await manager.send_command(agent_id, "shutdown", params)
        success = result.get("success", False)
        if not success:
            logger.error(
                f"AgentShutdownHook: shutdown agent={agent_id} failed: {result.get('message')}"
            )
        return success

    async def test_connection(self) -> bool:
        """检测 Agent 是否在线，失败时抛出包含诊断信息的异常"""
        from services.agent_manager import get_agent_manager

        agent_id = self.config.get("agent_id", "").strip()
        if not agent_id:
            raise ValueError("Agent ID 未配置")

        manager = get_agent_manager()

        # 获取当前在线 Agent 列表用于诊断
        online_agents = manager.list_agents()
        online_agent_ids = [a["agent_id"] for a in online_agents]

        # 检查 Agent 是否在线
        is_online = await manager.check_agent_online(agent_id)

        if is_online:
            return True

        # 构建详细的错误诊断信息
        if not online_agents:
            error_msg = (
                f"Agent '{agent_id}' 未连接到服务端。\n"
                f"当前没有任何 Agent 在线。\n\n"
                f"排查步骤：\n"
                f"1. 确认 Agent 程序正在运行\n"
                f"2. 检查 Agent 配置中的 server_url 是否指向本服务地址\n"
                f"3. 检查网络连通性和防火墙设置"
            )
        elif agent_id in online_agent_ids:
            error_msg = (
                f"Agent '{agent_id}' 已连接但无响应（可能刚重启或网络不稳定）。\n"
                f"请稍后重试，或检查 Agent 程序状态。"
            )
        else:
            # 在线但 ID 不匹配
            online_list = "\n".join([f"  - {a['agent_id']} ({a.get('agent_name', '未命名')})" for a in online_agents])
            error_msg = (
                f"Agent '{agent_id}' 未找到。\n\n"
                f"当前在线的 Agent ({len(online_agents)} 个)：\n{online_list}\n\n"
                f"可能原因：\n"
                f"1. Agent ID 配置不匹配（请核对 Agent 客户端中配置的 ID）\n"
                f"2. Agent 尚未连接到服务端"
            )

        raise ConnectionError(error_msg)

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
