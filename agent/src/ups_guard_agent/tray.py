"""系统托盘图标"""
import os
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
    """使用 Pillow 绘制圆形图标，中间有闪电"""
    try:
        from PIL import Image, ImageDraw
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        color = _COLORS.get(status, (128, 128, 128))
        # 绘制圆形背景
        draw.ellipse((2, 2, size - 2, size - 2), fill=color)
        # 绘制闪电形状
        # 上半部分三角形
        draw.polygon([(38, 10), (22, 34), (36, 34)], fill=(255, 255, 255))
        # 下半部分三角形
        draw.polygon([(28, 30), (42, 30), (26, 54)], fill=(255, 255, 255))
        return img
    except Exception as e:
        logger.warning(f"Failed to create icon: {e}")
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

    def __init__(
        self,
        on_quit: Optional[Callable] = None,
        on_settings: Optional[Callable] = None,
    ):
        self._status = "disconnected"
        self._detail = ""
        self._on_quit = on_quit
        self._on_settings = on_settings
        self._icon = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """在独立线程中启动托盘图标"""
        logger.info("Starting tray icon")
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            import pystray
            from pystray import MenuItem, Menu

            def quit_action(icon, item):
                logger.info("Quit action triggered")
                icon.stop()
                if self._on_quit:
                    self._on_quit()
                # 强制退出整个程序
                os._exit(0)

            # 使用当前状态创建图标
            img = _make_icon(self._status)
            if img is None:
                logger.warning("Cannot create tray icon image")
                return

            self._icon = pystray.Icon(
                "UPS Guard Agent",
                img,
                self._status_label(),
                menu=Menu(
                    MenuItem(lambda text: self._status_label(), None, enabled=False),
                    Menu.SEPARATOR,
                    MenuItem("退出", quit_action),
                ),
            )

            logger.info(f"Tray icon starting, status={self._status}")
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
        logger.info(f"Status changed: {self._status} -> {status}" + (f" ({detail})" if detail else ""))
        self._status = status
        self._detail = detail
        self._apply_status()

    def _apply_status(self):
        """应用当前状态到图标（如果图标还未创建，启动延迟重试）"""
        if self._icon:
            try:
                img = _make_icon(self._status)
                if img:
                    self._icon.icon = img
                self._icon.title = self._status_label()
            except Exception as e:
                logger.warning(f"Failed to update tray icon: {e}")
        else:
            # 图标还未创建，延迟重试
            def retry():
                import time
                for _ in range(10):  # 最多等待 2 秒
                    time.sleep(0.2)
                    if self._icon:
                        try:
                            img = _make_icon(self._status)
                            if img:
                                self._icon.icon = img
                            self._icon.title = self._status_label()
                            logger.debug(f"Tray icon updated after delay: {self._status}")
                        except Exception as e:
                            logger.warning(f"Failed to update tray icon after delay: {e}")
                        break
            threading.Thread(target=retry, daemon=True).start()

    def stop(self):
        logger.info("Stopping tray icon")
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
