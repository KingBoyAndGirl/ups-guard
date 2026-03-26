"""用户偏好设置 API"""
import json
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from db.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# 默认卡片顺序
DEFAULT_DASHBOARD_CARDS = {
    "col1": ["status", "energy", "battery-detail", "voltage-quality", "events"],
    "col2": ["power-metrics", "battery-status", "environment", "self-test"],
    "col3": ["power-chart", "battery-life", "predictions"]
}

DEFAULT_SETTINGS_CARDS = {
    "col1": ["shutdown-policy", "data-management"],
    "col2": ["notifications", "config-io"],
    "col3": ["monitoring", "hooks"],
    "col4": ["ups-config", "security"]
}


class UserPreferences(BaseModel):
    """用户偏好设置"""
    dashboardCardOrder: Optional[Dict[str, List[str]]] = None
    settingsCardOrder: Optional[Dict[str, List[str]]] = None


class CardOrderUpdate(BaseModel):
    """卡片顺序更新请求"""
    page: str  # "dashboard" 或 "settings"
    col: str   # "col1", "col2", "col3", "col4"
    cards: List[str]


class CardMoveRequest(BaseModel):
    """卡片移动请求"""
    page: str  # "dashboard" 或 "settings"
    fromCol: str
    toCol: str
    cardId: str
    toIndex: int


async def get_user_preferences() -> Dict[str, Any]:
    """从数据库获取用户偏好设置"""
    db = await get_db()
    row = await db.fetch_one("SELECT value FROM config WHERE key = 'user_preferences'")

    if row and row['value']:
        try:
            prefs = json.loads(row['value'])
            # 确保有默认值
            if 'dashboardCardOrder' not in prefs:
                prefs['dashboardCardOrder'] = DEFAULT_DASHBOARD_CARDS.copy()
            if 'settingsCardOrder' not in prefs:
                prefs['settingsCardOrder'] = DEFAULT_SETTINGS_CARDS.copy()
            return prefs
        except json.JSONDecodeError:
            pass

    # 返回默认值
    return {
        'dashboardCardOrder': DEFAULT_DASHBOARD_CARDS.copy(),
        'settingsCardOrder': DEFAULT_SETTINGS_CARDS.copy()
    }


async def save_user_preferences(prefs: Dict[str, Any]):
    """保存用户偏好设置到数据库"""
    db = await get_db()
    await db.execute(
        "INSERT OR REPLACE INTO config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
        ('user_preferences', json.dumps(prefs))
    )


@router.get("/preferences")
async def get_preferences():
    """获取用户偏好设置"""
    prefs = await get_user_preferences()
    return prefs


@router.put("/preferences")
async def update_preferences(preferences: UserPreferences):
    """更新用户偏好设置"""
    prefs = await get_user_preferences()

    if preferences.dashboardCardOrder is not None:
        prefs['dashboardCardOrder'] = preferences.dashboardCardOrder
    if preferences.settingsCardOrder is not None:
        prefs['settingsCardOrder'] = preferences.settingsCardOrder

    await save_user_preferences(prefs)
    return {"success": True, "message": "偏好设置已更新"}


@router.post("/preferences/card-order")
async def update_card_order(request: CardOrderUpdate):
    """更新单列卡片顺序"""
    prefs = await get_user_preferences()

    if request.page == "dashboard":
        if request.col not in prefs.get('dashboardCardOrder', {}):
            prefs['dashboardCardOrder'][request.col] = []
        prefs['dashboardCardOrder'][request.col] = request.cards
    elif request.page == "settings":
        if request.col not in prefs.get('settingsCardOrder', {}):
            prefs['settingsCardOrder'][request.col] = []
        prefs['settingsCardOrder'][request.col] = request.cards
    else:
        raise HTTPException(status_code=400, detail="Invalid page")

    await save_user_preferences(prefs)
    return {"success": True, "message": "卡片顺序已更新"}


@router.post("/preferences/card-move")
async def move_card(request: CardMoveRequest):
    """跨列移动卡片"""
    prefs = await get_user_preferences()

    if request.page == "dashboard":
        card_order = prefs.get('dashboardCardOrder', DEFAULT_DASHBOARD_CARDS.copy())
    elif request.page == "settings":
        card_order = prefs.get('settingsCardOrder', DEFAULT_SETTINGS_CARDS.copy())
    else:
        raise HTTPException(status_code=400, detail="Invalid page")

    # 从源列移除
    if request.fromCol in card_order:
        from_cards = card_order[request.fromCol]
        if request.cardId in from_cards:
            from_cards.remove(request.cardId)

    # 添加到目标列
    if request.toCol not in card_order:
        card_order[request.toCol] = []

    to_cards = card_order[request.toCol]
    insert_index = min(request.toIndex, len(to_cards))
    to_cards.insert(insert_index, request.cardId)

    # 保存
    if request.page == "dashboard":
        prefs['dashboardCardOrder'] = card_order
    else:
        prefs['settingsCardOrder'] = card_order

    await save_user_preferences(prefs)
    return {"success": True, "message": "卡片已移动"}


@router.post("/preferences/reset")
async def reset_preferences(page: str = "all"):
    """重置偏好设置为默认值"""
    prefs = await get_user_preferences()

    if page == "dashboard" or page == "all":
        prefs['dashboardCardOrder'] = DEFAULT_DASHBOARD_CARDS.copy()
    if page == "settings" or page == "all":
        prefs['settingsCardOrder'] = DEFAULT_SETTINGS_CARDS.copy()

    await save_user_preferences(prefs)
    return {"success": True, "message": "偏好设置已重置"}

