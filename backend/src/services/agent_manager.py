"""Agent 连接管理器"""
import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class AgentInfo:
    """Agent 连接信息"""
    agent_id: str
    agent_name: str
    websocket: WebSocket
    hostname: str = ""
    os_type: str = ""
    os_version: str = ""
    mac_address: str = ""
    ip_address: str = ""
    system_info: Dict[str, Any] = field(default_factory=dict)
    connected_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)


class AgentConnectionManager:
    """Agent WebSocket 连接管理器（全局单例）"""

    def __init__(self):
        self._agents: Dict[str, AgentInfo] = {}
        self._pending_commands: Dict[str, asyncio.Future] = {}

    async def register(self, agent_id: str, agent_name: str, websocket: WebSocket) -> AgentInfo:
        """注册 Agent 连接，同 ID 旧连接自动关闭（支持断线重连）"""
        if agent_id in self._agents:
            old = self._agents[agent_id]
            logger.info(f"Agent {agent_id} reconnecting, closing old connection")
            try:
                await old.websocket.close()
            except Exception:
                pass

        info = AgentInfo(
            agent_id=agent_id,
            agent_name=agent_name,
            websocket=websocket,
        )
        self._agents[agent_id] = info
        logger.info(f"Agent registered: {agent_id} ({agent_name})")
        return info

    def unregister(self, agent_id: str):
        """注销 Agent 连接"""
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"Agent unregistered: {agent_id}")

    def update_info(self, agent_id: str, system_info: Dict[str, Any]):
        """更新 Agent 系统信息"""
        if agent_id not in self._agents:
            return
        info = self._agents[agent_id]
        info.system_info = system_info
        info.hostname = system_info.get("hostname", "")
        info.os_type = system_info.get("os", "")
        info.os_version = system_info.get("os_version", "")
        info.mac_address = system_info.get("mac_address", "")
        info.ip_address = system_info.get("ip_address", "")

    def update_heartbeat(self, agent_id: str):
        """更新 Agent 心跳时间"""
        if agent_id in self._agents:
            self._agents[agent_id].last_heartbeat = datetime.now()

    async def send_command(
        self,
        agent_id: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """向 Agent 发送命令并等待响应。对于关机类命令超时视为成功"""
        if agent_id not in self._agents:
            return {"success": False, "message": f"Agent {agent_id} not online"}

        request_id = str(uuid.uuid4())
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()
        self._pending_commands[request_id] = future

        power_actions = {"shutdown", "reboot", "sleep", "hibernate"}

        try:
            message = {
                "type": "command",
                "data": {
                    "request_id": request_id,
                    "action": action,
                    "params": params or {},
                },
            }
            ws = self._agents[agent_id].websocket
            await ws.send_json(message)

            try:
                result = await asyncio.wait_for(future, timeout=timeout)
                return result
            except asyncio.TimeoutError:
                if action in power_actions:
                    logger.info(
                        f"Command {action} timed out for agent {agent_id}, treating as success"
                    )
                    return {"success": True, "message": "Command sent (connection closed, treated as success)"}
                return {"success": False, "message": f"Command timed out after {timeout}s"}
        except Exception as e:
            if action in power_actions:
                logger.info(
                    f"Command {action} error for agent {agent_id} ({e}), treating as success"
                )
                return {"success": True, "message": "Command sent (connection closed, treated as success)"}
            return {"success": False, "message": str(e)}
        finally:
            self._pending_commands.pop(request_id, None)

    def resolve_command(self, request_id: str, result: Dict[str, Any]):
        """由 WebSocket 消息循环调用，将结果填入 Future"""
        future = self._pending_commands.get(request_id)
        if future and not future.done():
            future.set_result(result)

    async def check_agent_online(self, agent_id: str) -> bool:
        """
        发送 ping 并等待 pong 回复来检测 Agent 是否真正在线。

        仅 send_json 成功不代表 Agent 在线（数据可能只是写入了内核缓冲区），
        必须收到 pong 回复才能确认。
        """
        if agent_id not in self._agents:
            logger.debug(f"Agent {agent_id} not in agents dict, offline")
            return False

        # 构造一个唯一的 ping request_id，复用 pending_commands 机制等待回复
        ping_id = f"ping-{uuid.uuid4()}"
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()
        self._pending_commands[ping_id] = future

        try:
            ws = self._agents[agent_id].websocket
            await ws.send_json({
                "type": "ping",
                "data": {"request_id": ping_id},
            })
            # 等待 pong 回复，最多 5 秒
            await asyncio.wait_for(future, timeout=5.0)
            logger.debug(f"Agent {agent_id} online check: OK")
            return True
        except asyncio.TimeoutError:
            logger.info(f"Agent {agent_id} online check: pong timeout (5s), cleaning up stale connection")
            self.unregister(agent_id)
            return False
        except Exception as e:
            logger.info(f"Agent {agent_id} online check failed: {e}, cleaning up")
            self.unregister(agent_id)
            return False
        finally:
            self._pending_commands.pop(ping_id, None)

    def list_agents(self) -> list:
        """列出所有在线 Agent 信息"""
        result = []
        for info in self._agents.values():
            result.append(
                {
                    "agent_id": info.agent_id,
                    "agent_name": info.agent_name,
                    "hostname": info.hostname,
                    "os_type": info.os_type,
                    "os_version": info.os_version,
                    "mac_address": info.mac_address,
                    "ip_address": info.ip_address,
                    "system_info": info.system_info,
                    "connected_at": info.connected_at.isoformat(),
                    "last_heartbeat": info.last_heartbeat.isoformat(),
                }
            )
        return result


# 全局单例
_agent_manager: Optional[AgentConnectionManager] = None


def get_agent_manager() -> AgentConnectionManager:
    """获取全局 Agent 管理器实例"""
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentConnectionManager()
    return _agent_manager
