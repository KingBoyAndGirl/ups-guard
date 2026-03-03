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
        self._ws: Optional[websockets.WebSocketClientProtocol] = None  # Current websocket connection
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _ws_url(self) -> str:
        base = self.server_url
        # 将 http/https 转为 ws/wss
        if base.startswith("https://"):
            base = "wss://" + base[len("https://"):]
        elif base.startswith("http://"):
            base = "ws://" + base[len("http://"):]
        url = (
            f"{base}/ws/agent"
            f"?token={self.token}"
            f"&agent_id={self.agent_id}"
            f"&agent_name={self.agent_name}"
        )
        masked_token = (self.token[:4] + "****") if self.token else ""
        masked_url = (
            f"{base}/ws/agent"
            f"?token={masked_token}"
            f"&agent_id={self.agent_id}"
            f"&agent_name={self.agent_name}"
        )
        logger.debug(f"WS URL: {masked_url}")
        return url

    def _update_status(self, status: str, detail: str = ""):
        if self.status_callback:
            try:
                self.status_callback(status, detail)
            except Exception:
                pass

    def update_config(self, server_url: str, token: str, agent_id: str, agent_name: str):
        """更新连接配置（重连前调用）"""
        self.server_url = server_url.rstrip("/")
        self.token = token
        self.agent_id = agent_id
        self.agent_name = agent_name
        masked_token = (token[:4] + "****") if token else ""
        logger.info(
            f"Config updated: server_url={server_url} agent_id={agent_id} "
            f"agent_name={agent_name} token={masked_token}"
        )

    def reconnect(self):
        """断开当前连接并使用新配置重连"""
        logger.info("Reconnect requested, closing current connection")
        if self._ws is not None and self._loop is not None:
            asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop)

    async def start(self):
        """带自动重连循环启动客户端"""
        self._running = True
        self._loop = asyncio.get_running_loop()
        masked_token = (self.token[:4] + "****") if self.token else ""
        logger.info(
            f"Starting AgentClient: server_url={self.server_url} "
            f"agent_id={self.agent_id} agent_name={self.agent_name} token={masked_token}"
        )
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
        logger.info("Stopping AgentClient")
        self._running = False

    async def _connect_and_listen(self):
        """连接并监听消息"""
        url = self._ws_url()
        masked_token = (self.token[:4] + "****") if self.token else ""
        masked_url = url.replace(self.token, masked_token)
        logger.info(f"Connecting to {masked_url}")
        async with websockets.connect(url) as ws:
            self._ws = ws
            logger.info(f"Connected to {self.server_url}")
            self._update_status("connected")

            # 发送 register 消息（系统信息）
            sys_info = get_system_info()
            logger.info(
                f"Sending register: hostname={sys_info.get('hostname')} "
                f"os={sys_info.get('os')} ip={sys_info.get('ip_address')}"
            )
            await ws.send(json.dumps({
                "type": "register",
                "data": sys_info,
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
                        logger.debug("Heartbeat sent")
                    except Exception as e:
                        logger.warning(f"Heartbeat failed: {e}")
                        break

            hb_task = asyncio.create_task(heartbeat())
            try:
                async for message in ws:
                    data = json.loads(message)
                    logger.debug(f"Message received: type={data.get('type')}")
                    await self._handle_message(ws, data)
            except ConnectionClosed as e:
                logger.info(f"WebSocket connection closed: code={e.code} reason={e.reason!r}")
            finally:
                hb_task.cancel()

            self._ws = None
            self._update_status("disconnected")
            logger.info("Disconnected from server")

    async def _handle_message(self, ws, data: dict):
        msg_type = data.get("type")
        msg_data = data.get("data", {})
        logger.debug(f"Handling message type={msg_type}")

        if msg_type == "ping":
            # 回复 pong，带上 request_id（用于服务端在线检测）
            request_id = msg_data.get("request_id", "")
            await ws.send(json.dumps({
                "type": "pong",
                "data": {"request_id": request_id},
            }))

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

        if result.get("success"):
            logger.info(f"Command {action} succeeded: {result.get('message', '')}")
        else:
            logger.warning(f"Command {action} failed: {result.get('message', '')}")

        try:
            await ws.send(json.dumps({
                "type": "command_result",
                "data": {
                    "request_id": request_id,
                    "success": result.get("success", False),
                    "message": result.get("message", ""),
                },
            }))
        except Exception as e:
            logger.warning(f"Failed to send command result: {e}")
