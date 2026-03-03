"""Agent REST API"""
import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.agent_manager import get_agent_manager

logger = logging.getLogger(__name__)

router = APIRouter()


class CommandRequest(BaseModel):
    action: str
    params: Optional[Dict[str, Any]] = None


@router.get("/agents")
async def list_agents():
    """列出所有在线 Agent 及数量"""
    manager = get_agent_manager()
    agents = manager.list_agents()
    return {"agents": agents, "count": len(agents)}


@router.post("/agents/{agent_id}/command")
async def send_command(agent_id: str, body: CommandRequest):
    """向指定 Agent 发送命令"""
    manager = get_agent_manager()
    if agent_id not in manager._agents:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found or offline")

    result = await manager.send_command(agent_id, body.action, body.params)
    return result
