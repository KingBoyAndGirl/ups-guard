"""WebSocket 客户端"""
import asyncio
import json
import logging
from typing import Callable, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from ups_guard_agent.system_info import get_system_info, get_runtime_info

logger = logging.getLogger(__name__)

# 重连延迟梯度（秒）：3, 5, 10, 15, 30, 60
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
        self._ws: Optional[websockets.WebSocketClientProtocol] = None  # 当前 WebSocket 连接
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_event: Optional[asyncio.Event] = None  # 用于中断重连等待

    def _ws_url(self) -> str:
        """构造 WebSocket 连接地址"""
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
        logger.debug(f"WebSocket 地址: {masked_url}")
        return url

    def _update_status(self, status: str, detail: str = ""):
        """更新连接状态回调"""
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
            f"配置已更新: server_url={server_url} agent_id={agent_id} "
            f"agent_name={agent_name} token={masked_token}"
        )

    def reconnect(self):
        """断开当前连接并使用新配置重连"""
        logger.info("请求重连，正在关闭当前连接")
        if self._ws is not None and self._loop is not None:
            asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop)

    async def start(self):
        """启动客户端（带自动重连循环）"""
        self._running = True
        self._loop = asyncio.get_running_loop()
        self._stop_event = asyncio.Event()
        masked_token = (self.token[:4] + "****") if self.token else ""
        logger.info(
            f"启动 AgentClient: server_url={self.server_url} "
            f"agent_id={self.agent_id} agent_name={self.agent_name} token={masked_token}"
        )
        delay_idx = 0
        while self._running:
            self._update_status("connecting")
            try:
                await self._connect_and_listen()
                delay_idx = 0  # 连接成功后重置重连间隔
            except Exception as e:
                logger.warning(f"连接错误: {e}")
            if not self._running:
                break
            delay = RECONNECT_DELAYS[min(delay_idx, len(RECONNECT_DELAYS) - 1)]
            delay_idx += 1
            self._update_status("reconnecting", f"{delay}秒后重连")
            logger.info(f"{delay}秒后重连...")
            # 使用 _stop_event 等待，stop() 可以立即中断
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass  # 正常超时，继续重连
            if self._stop_event.is_set():
                break  # stop() 被调用，立即退出

    def stop(self):
        """停止客户端"""
        logger.info("正在停止 AgentClient")
        self._running = False
        # 设置停止事件，立即中断重连等待
        if self._stop_event is not None and self._loop is not None:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        # 主动关闭 WebSocket 连接，触发异步循环退出
        if self._ws is not None and self._loop is not None:
            try:
                asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop)
            except Exception as e:
                logger.debug(f"关闭 WebSocket 时出错: {e}")

    async def _connect_and_listen(self):
        """连接服务端并监听消息"""
        url = self._ws_url()
        masked_token = (self.token[:4] + "****") if self.token else ""
        masked_url = url.replace(self.token, masked_token)
        logger.info(f"正在连接 {masked_url}")
        async with websockets.connect(url) as ws:
            self._ws = ws
            logger.info(f"已连接到 {self.server_url}")
            self._update_status("connected")

            # 发送注册消息（包含系统信息）
            sys_info = get_system_info()
            logger.info(
                f"发送注册信息: hostname={sys_info.get('hostname')} "
                f"os={sys_info.get('os')} ip={sys_info.get('ip_address')}"
            )
            await ws.send(json.dumps({
                "type": "register",
                "data": sys_info,
            }))

            # 启动心跳任务（每30秒发送一次）
            async def heartbeat():
                while True:
                    await asyncio.sleep(30)
                    try:
                        await ws.send(json.dumps({
                            "type": "heartbeat",
                            "data": get_runtime_info(),
                        }))
                        logger.debug("心跳已发送")
                    except Exception as e:
                        logger.warning(f"心跳发送失败: {e}")
                        break

            hb_task = asyncio.create_task(heartbeat())
            try:
                async for message in ws:
                    data = json.loads(message)
                    logger.debug(f"收到消息: type={data.get('type')}")
                    await self._handle_message(ws, data)
            except ConnectionClosed as e:
                logger.info(f"WebSocket 连接已关闭: code={e.code} reason={e.reason!r}")
            finally:
                hb_task.cancel()

            self._ws = None
            self._update_status("disconnected")
            logger.info("已断开与服务端的连接")

    async def _handle_message(self, ws, data: dict):
        """处理收到的消息"""
        msg_type = data.get("type")
        msg_data = data.get("data", {})
        logger.debug(f"处理消息: type={msg_type}")

        if msg_type == "ping":
            # 回复 pong，带上 request_id（用于服务端在线检测）
            request_id = msg_data.get("request_id", "")
            await ws.send(json.dumps({
                "type": "pong",
                "data": {"request_id": request_id},
            }))

        elif msg_type == "agent_registered":
            logger.info(f"已注册为 Agent: {msg_data.get('agent_id')}")

        elif msg_type == "command":
            await self._handle_command(ws, msg_data)

    async def _handle_command(self, ws, data: dict):
        """处理服务端下发的命令"""
        request_id = data.get("request_id", "")
        action = data.get("action", "")
        params = data.get("params", {})
        logger.info(f"执行命令: {action} 参数={params}")
        try:
            result = await self.command_handler(action, params)
        except Exception as e:
            result = {"success": False, "message": str(e)}

        if result.get("success"):
            logger.info(f"命令 {action} 执行成功: {result.get('message', '')}")
        else:
            logger.warning(f"命令 {action} 执行失败: {result.get('message', '')}")

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
            logger.warning(f"发送命令结果失败: {e}")
