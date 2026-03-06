"""系统托盘图标"""
import os
import sys
import threading
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# 状态颜色映射
_COLORS = {
    "connected": (0, 200, 0),
    "connecting": (255, 165, 0),
    "reconnecting": (255, 165, 0),
    "disconnected": (200, 0, 0),
}


def _make_icon(status: str):
    """使用 Pillow 绘制圆形图标，中间有闪电符号"""
    try:
        from PIL import Image, ImageDraw
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        color = _COLORS.get(status, (128, 128, 128))
        # 绘制圆形背景
        draw.ellipse((2, 2, size - 2, size - 2), fill=color)
        # 绘制闪电形状（上半部分三角形 + 下半部分三角形）
        draw.polygon([(38, 10), (22, 34), (36, 34)], fill=(255, 255, 255))
        draw.polygon([(28, 30), (42, 30), (26, 54)], fill=(255, 255, 255))
        return img
    except Exception as e:
        logger.warning(f"创建图标失败: {e}")
        try:
            from PIL import Image
            return Image.new("RGBA", (64, 64), _COLORS.get(status, (128, 128, 128)))
        except Exception:
            return None


class TrayIcon:
    """系统托盘图标（在独立线程中运行 pystray）"""

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
        logger.info("正在启动托盘图标")
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        """托盘图标主循环"""
        try:
            import pystray
            from pystray import MenuItem, Menu

            def open_settings():
                logger.info("设置按钮被点击（左键单击）")
                if self._on_settings:
                    self._on_settings()

            def quit_action(icon, item):
                logger.info("退出操作触发")
                # 停止托盘图标
                try:
                    icon.stop()
                except Exception:
                    pass

                # 强杀所有同名进程（服务进程 + bootloader 子进程），确保零残留
                try:
                    import subprocess
                    exe_name = os.path.basename(sys.executable)
                    subprocess.run(
                        ["taskkill", "/F", "/IM", exe_name],
                        capture_output=True, timeout=5,
                    )
                except Exception:
                    pass

                os._exit(0)

            # 使用当前状态创建图标
            img = _make_icon(self._status)
            if img is None:
                logger.warning("无法创建托盘图标图片")
                return

            # 创建菜单，第一项设为 default=True 使左键单击触发
            menu = Menu(
                MenuItem(lambda text: self._status_label(), None, enabled=False),
                Menu.SEPARATOR,
                MenuItem("打开", lambda icon, item: open_settings(), default=True, visible=False),
                MenuItem("退出", quit_action),
            )

            self._icon = pystray.Icon(
                "UPS Guard Agent",
                img,
                self._status_label(),
                menu=menu,
            )

            logger.info(f"托盘图标启动中，状态={self._status}")
            self._icon.run()
        except Exception as e:
            logger.warning(f"托盘图标出错: {e}")

    def _status_label(self) -> str:
        """生成状态标签文本"""
        label = self._STATUS_LABELS.get(self._status, self._status)
        if self._detail:
            return f"UPS Guard Agent — {label} ({self._detail})"
        return f"UPS Guard Agent — {label}"

    def update_status(self, status: str, detail: str = ""):
        """更新托盘图标状态"""
        logger.info(f"状态变更: {self._status} -> {status}" + (f" ({detail})" if detail else ""))
        self._status = status
        self._detail = detail
        self._apply_status()

    def _apply_status(self):
        """将当前状态应用到图标（如果图标还未创建，延迟重试）"""
        if self._icon:
            try:
                img = _make_icon(self._status)
                if img:
                    self._icon.icon = img
                self._icon.title = self._status_label()
            except Exception as e:
                logger.warning(f"更新托盘图标失败: {e}")
        else:
            # 图标还未创建，启动延迟重试
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
                            logger.debug(f"延迟更新托盘图标成功: {self._status}")
                        except Exception as e:
                            logger.warning(f"延迟更新托盘图标失败: {e}")
                        break
            threading.Thread(target=retry, daemon=True).start()

    def stop(self):
        """停止托盘图标"""
        logger.info("正在停止托盘图标")
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
