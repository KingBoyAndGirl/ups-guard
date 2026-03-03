"""系统托盘图标"""
import threading
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# 颜色映射
_COLORS = {
    "connected": (0, 200, 0),
    "connecting": (255, 165, 0),
    "reconnecting": (255, 165, 0),
    "disconnected": (200, 0, 0),
}


def _make_icon(status: str):
    """使用 Pillow 绘制圆形图标"""
    try:
        from PIL import Image, ImageDraw
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        color = _COLORS.get(status, (128, 128, 128))
        # 绘制圆形背景
        draw.ellipse((4, 4, size - 4, size - 4), fill=color)
        # 绘制闪电形状（多边形近似）
        bolt = [
            (34, 8), (20, 34), (32, 34), (30, 56), (44, 30), (32, 30), (34, 8)
        ]
        draw.polygon(bolt, fill=(255, 255, 255))
        return img
    except Exception:
        try:
            from PIL import Image
            return Image.new("RGBA", (64, 64), _COLORS.get(status, (128, 128, 128)))
        except Exception:
            return None


class TrayIcon:
    """系统托盘图标（独立线程运行 pystray）"""

    _STATUS_LABELS = {
        "connected": "已连接",
        "connecting": "连接中…",
        "reconnecting": "重新连接中…",
        "disconnected": "已断开",
    }

    def __init__(self, on_quit: Optional[Callable] = None):
        self._status = "disconnected"
        self._detail = ""
        self._on_quit = on_quit
        self._icon = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """在独立线程中启动托盘图标"""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            import pystray
            from pystray import MenuItem, Menu

            def quit_action(icon, item):
                icon.stop()
                if self._on_quit:
                    self._on_quit()

            img = _make_icon(self._status)
            if img is None:
                logger.warning("Cannot create tray icon image")
                return

            self._icon = pystray.Icon(
                "UPS Guard Agent",
                img,
                "UPS Guard Agent",
                menu=Menu(
                    MenuItem(lambda text: self._status_label(), None, enabled=False),
                    MenuItem("退出", quit_action),
                ),
            )
            self._icon.run()
        except Exception as e:
            logger.warning(f"Tray icon error: {e}")

    def _status_label(self) -> str:
        label = self._STATUS_LABELS.get(self._status, self._status)
        if self._detail:
            return f"UPS Guard Agent — {label} ({self._detail})"
        return f"UPS Guard Agent — {label}"

    def update_status(self, status: str, detail: str = ""):
        """更新托盘图标状态"""
        self._status = status
        self._detail = detail
        if self._icon:
            img = _make_icon(status)
            if img:
                self._icon.icon = img
            self._icon.title = self._status_label()

    def stop(self):
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
