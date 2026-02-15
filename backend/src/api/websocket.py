"""WebSocket API"""
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from services.monitor import get_monitor
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """接受连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """广播消息到所有连接"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                disconnected.append(connection)
        
        # 移除断开的连接
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)


manager = ConnectionManager()


def verify_ws_token(token: str) -> bool:
    """验证 WebSocket token"""
    expected_token = settings.get_or_generate_api_token()
    return token == expected_token


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(default="")):
    """WebSocket 端点，实时推送 UPS 状态"""
    # 验证 token
    if not verify_ws_token(token):
        logger.warning(f"WebSocket connection rejected: invalid token")
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await manager.connect(websocket)
    
    try:
        # 发送初始状态
        monitor = get_monitor()
        if monitor and monitor.get_current_data():
            data = monitor.get_current_data()
            shutdown_status = monitor.shutdown_manager.get_status()
            
            # 使用 Pydantic 的 model_dump() 自动序列化所有字段（包括 Phase 1-4 新增字段）
            response_data = data.model_dump(mode='json')
            response_data["shutdown"] = shutdown_status

            await websocket.send_json({
                "type": "status_update",
                "data": response_data
            })
        
        # 心跳任务
        async def heartbeat():
            try:
                while True:
                    await asyncio.sleep(25)  # 每25秒发送心跳
                    try:
                        await websocket.send_json({"type": "ping"})
                    except Exception:
                        break
            except asyncio.CancelledError:
                pass
        
        heartbeat_task = asyncio.create_task(heartbeat())
        
        # 保持连接并接收客户端消息
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                # 简单的心跳响应
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data == "pong":
                    pass  # 客户端响应心跳
            except asyncio.TimeoutError:
                # 30秒没有消息，断开连接
                logger.warning("WebSocket client timeout, disconnecting")
                break
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
    finally:
        # 取消心跳任务
        if 'heartbeat_task' in locals():
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass


async def broadcast_status_update(data):
    """广播状态更新（由 monitor 调用）"""
    from services.monitor import get_monitor
    monitor = get_monitor()
    
    if monitor:
        shutdown_status = monitor.shutdown_manager.get_status()
        
        # 使用 Pydantic 的 model_dump() 自动序列化所有字段（包括 Phase 1-4 新增字段）
        response_data = data.model_dump(mode='json')
        response_data["shutdown"] = shutdown_status
        

        await manager.broadcast({
            "type": "status_update",
            "data": response_data
        })


async def broadcast_event(event_type: str, message: str, metadata: dict = None):
    """广播事件（由 history 或其他服务调用）"""
    await manager.broadcast({
        "type": "event",
        "data": {
            "event_type": event_type,
            "message": message,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }
    })


async def broadcast_config_changed():
    """广播配置变更"""
    await manager.broadcast({
        "type": "config_changed",
        "data": {
            "timestamp": datetime.now().isoformat()
        }
    })


async def broadcast_hook_progress(progress_data: dict):
    """
    广播 hook 执行进度（由 HookExecutor 调用）
    
    Args:
        progress_data: 进度数据，包含 type 和 data 字段
    """
    await manager.broadcast(progress_data)
