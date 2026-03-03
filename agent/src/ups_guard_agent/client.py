"""WebSocket 客户端"""
import asyncio
import json
import logging
from typing import Callable, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from ups_guard_agent.system_info import get_system_info, get_runtime_info

logger = logging.getLogger(__name__)

RECONNECT_DELAYS = [3, 5, 10, 15, 30, 60]


class AgentClient:
    """WebSocket Agent 客户端，带自动重连"""

    def __init__(
        self,
        server_url: str,
        token: str,
        agent_id: str,
        agent_name: str,
        command_handler: Callable,
        status_callback: Optional[Callable] = None,
    ):
        self.server_url = server_url.rstrip("/")
        self.token = token
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.command_handler = command_handler
        self.status_callback = status_callback
        self._running = False

    def _ws_url(self) -> str:
        base = self.server_url
        # 将 http/https 转为 ws/wss
        if base.startswith("https://"):
            base = "wss://" + base[len("https://"):]
        elif base.startswith("http://"):
            base = "ws://" + base[len("http://"):]
        return (
            f"{base}/ws/agent"
            f"?token={self.token}"
            f"&agent_id={self.agent_id}"
            f"&agent_name={self.agent_name}"
        )

    def _update_status(self, status: str, detail: str = ""):
        if self.status_callback:
            try:
                self.status_callback(status, detail)
            except Exception:
                pass

    async def start(self):
        """带自动重连循环启动客户端"""
        self._running = True
        delay_idx = 0
        while self._running:
            self._update_status("connecting")
            try:
                await self._connect_and_listen()
                delay_idx = 0  # 连接成功后重置重连间隔
            except Exception as e:
                logger.warning(f"Connection error: {e}")
            if not self._running:
                break
            delay = RECONNECT_DELAYS[min(delay_idx, len(RECONNECT_DELAYS) - 1)]
            delay_idx += 1
            self._update_status("reconnecting", f"reconnecting in {delay}s")
            logger.info(f"Reconnecting in {delay}s...")
            await asyncio.sleep(delay)

    def stop(self):
        self._running = False

    async def _connect_and_listen(self):
        """连接并监听消息"""
        url = self._ws_url()
        async with websockets.connect(url) as ws:
            logger.info(f"Connected to {self.server_url}")
            self._update_status("connected")

            # 发送 register 消息（系统信息）
            await ws.send(json.dumps({
                "type": "register",
                "data": get_system_info(),
            }))

            # 启动心跳任务（每30秒发送 heartbeat）
            async def heartbeat():
                while True:
                    await asyncio.sleep(30)
                    try:
                        await ws.send(json.dumps({
                            "type": "heartbeat",
                            "data": get_runtime_info(),
                        }))
                    except Exception:
                        break

            hb_task = asyncio.create_task(heartbeat())
            try:
                async for message in ws:
                    data = json.loads(message)
                    await self._handle_message(ws, data)
            except ConnectionClosed:
                logger.info("WebSocket connection closed")
            finally:
                hb_task.cancel()

            self._update_status("disconnected")

    async def _handle_message(self, ws, data: dict):
        msg_type = data.get("type")
        msg_data = data.get("data", {})

        if msg_type == "ping":
            await ws.send(json.dumps({"type": "pong", "data": {}}))

        elif msg_type == "agent_registered":
            logger.info(f"Registered as agent: {msg_data.get('agent_id')}")

        elif msg_type == "command":
            await self._handle_command(ws, msg_data)

    async def _handle_command(self, ws, data: dict):
        request_id = data.get("request_id", "")
        action = data.get("action", "")
        params = data.get("params", {})
        logger.info(f"Executing command: {action} params={params}")
        try:
            result = await self.command_handler(action, params)
        except Exception as e:
            result = {"success": False, "message": str(e)}

        try:
            await ws.send(json.dumps({
                "type": "command_result",
                "data": {
                    "request_id": request_id,
                    "success": result.get("success", False),
                    "message": result.get("message", ""),
                },
            }))
        except Exception:
            pass
