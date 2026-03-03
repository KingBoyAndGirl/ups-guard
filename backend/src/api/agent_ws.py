"""Agent WebSocket 端点"""
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from config import settings
from services.agent_manager import get_agent_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/agent")
async def agent_websocket(
    websocket: WebSocket,
    token: str = Query(...),
    agent_id: str = Query(...),
    agent_name: str = Query(...),
):
    """Agent WebSocket 端点"""
    # 认证
    expected_token = settings.get_or_generate_api_token()
    if token != expected_token:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    manager = get_agent_manager()
    await manager.register(agent_id, agent_name, websocket)

    # 发送注册确认
    await websocket.send_json(
        {"type": "agent_registered", "data": {"agent_id": agent_id}}
    )

    # 启动心跳任务（每25秒 ping）
    async def heartbeat_task():
        while True:
            await asyncio.sleep(25)
            try:
                await websocket.send_json({"type": "ping", "data": {}})
            except Exception:
                break

    hb_task = asyncio.create_task(heartbeat_task())

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=60.0)
            except asyncio.TimeoutError:
                # 60 秒无消息时发 ping 探测
                try:
                    await websocket.send_json({"type": "ping", "data": {}})
                except Exception:
                    break
                continue

            msg_type = data.get("type")
            msg_data = data.get("data", {})

            if msg_type == "pong":
                manager.update_heartbeat(agent_id)

            elif msg_type == "register":
                manager.update_info(agent_id, msg_data)
                logger.info(f"Agent {agent_id} registered system info: {msg_data}")

            elif msg_type == "heartbeat":
                manager.update_heartbeat(agent_id)

            elif msg_type == "command_result":
                request_id = msg_data.get("request_id")
                if request_id:
                    manager.resolve_command(
                        request_id,
                        {
                            "success": msg_data.get("success", False),
                            "message": msg_data.get("message", ""),
                        },
                    )

    except WebSocketDisconnect:
        logger.info(f"Agent {agent_id} disconnected")
    except Exception as e:
        logger.error(f"Agent {agent_id} error: {e}")
    finally:
        hb_task.cancel()
        manager.unregister(agent_id)
