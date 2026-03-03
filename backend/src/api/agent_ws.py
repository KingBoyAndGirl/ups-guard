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

                # 自动注册为前置关机任务
                try:
                    await _auto_register_shutdown_hook(
                        agent_id=agent_id,
                        agent_name=agent_name,
                        system_info=msg_data,
                    )
                except Exception as e:
                    logger.error(f"Auto-register shutdown hook failed for {agent_id}: {e}")

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


async def _auto_register_shutdown_hook(
    agent_id: str,
    agent_name: str,
    system_info: dict,
) -> None:
    """
    Agent 首次连接时，自动注册为 agent_shutdown 类型的前置关机任务。

    去重规则（按优先级）：
    1. agent_id 精确匹配 → 跳过（同一实例重连）
    2. MAC 地址匹配 → 更新 agent_id（同一台机器换了 agent_id）
    3. 都不匹配 → 新建

    Args:
        agent_id:    Agent 唯一 ID
        agent_name:  Agent 名称（用户配置的设备名）
        system_info: Agent 上报的系统信息（含 hostname, os, os_version 等）
    """
    from config import get_config_manager
    from api.websocket import broadcast_config_changed

    config_manager = await get_config_manager()
    config = await config_manager.get_config()

    mac_address = system_info.get("mac_address", "").upper().strip()
    hostname = system_info.get("hostname", "").strip()

    for hook in config.pre_shutdown_hooks:
        if hook.get("hook_id") != "agent_shutdown":
            continue

        hook_config = hook.get("config", {})
        hook_agent_id = hook_config.get("agent_id", "")

        # 规则 1：agent_id 精确匹配 → 跳过
        if hook_agent_id == agent_id:
            logger.debug(
                f"Agent {agent_id} already has a shutdown hook, skipping"
            )
            return

        # 规则 2：MAC 地址匹配 → 同一台物理机换了 agent_id，更新即可
        hook_mac = hook_config.get("mac_address", "").upper().strip()
        if mac_address and hook_mac and mac_address == hook_mac:
            old_id = hook_agent_id
            hook_config["agent_id"] = agent_id
            await config_manager.update_config(config)
            logger.info(
                f"Agent {agent_id} matched existing hook by MAC={mac_address}, "
                f"updated agent_id from {old_id}"
            )
            # 通知前端配置变更
            await broadcast_config_changed()
            return

    # 规则 3：都不匹配 → 新建
    os_type = system_info.get("os", "")

    if hostname and os_type:
        hook_name = f"{agent_name} ({hostname}, {os_type})"
    elif hostname:
        hook_name = f"{agent_name} ({hostname})"
    else:
        hook_name = agent_name

    existing_priorities = [
        h.get("priority", 10) for h in config.pre_shutdown_hooks
    ]
    next_priority = max(existing_priorities, default=9) + 1

    new_hook = {
        "enabled": True,
        "hook_id": "agent_shutdown",
        "name": hook_name,
        "priority": next_priority,
        "timeout": 120,
        "on_failure": "continue",
        "auto_registered": True,
        "config": {
            "agent_id": agent_id,
            "shutdown_delay": 60,
            "shutdown_message": "UPS 电量不足，系统即将安全关机",
            "pre_commands": "",
            "mac_address": mac_address,
            "broadcast_address": "255.255.255.255",
        },
    }

    config.pre_shutdown_hooks.append(new_hook)
    await config_manager.update_config(config)

    logger.info(
        f"Auto-registered shutdown hook for Agent {agent_id} "
        f"({hook_name}), priority={next_priority}"
    )

    # 通知前端实时刷新
    await broadcast_config_changed()

