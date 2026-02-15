"""API 路由器"""
from fastapi import APIRouter
from api import status, history, config, websocket, ups, actions, system, hooks, devices, predictions, preferences, health, ups_control

# 创建主路由器
router = APIRouter(prefix="/api")

# 注册子路由
router.include_router(status.router, tags=["status"])
router.include_router(history.router, tags=["history"])
router.include_router(config.router, tags=["config"])
router.include_router(websocket.router, tags=["websocket"])
router.include_router(ups.router, tags=["ups"])
router.include_router(ups_control.router, tags=["ups-control"])
router.include_router(actions.router, tags=["actions"])
router.include_router(system.router, tags=["system"])
router.include_router(hooks.router, tags=["hooks"])
router.include_router(devices.router, tags=["devices"])
router.include_router(predictions.router, tags=["predictions"])
router.include_router(preferences.router, tags=["preferences"])
router.include_router(health.router, tags=["health"])
