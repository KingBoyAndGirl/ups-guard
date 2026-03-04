"""图形化配置窗口（tkinter）"""
import logging
import socket
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox
from typing import Callable, Optional

from ups_guard_agent.autostart import is_autostart_enabled, install_autostart, remove_autostart

logger = logging.getLogger(__name__)

# 单例锁，防止多次打开设置窗口
_window_lock = threading.Lock()
_window_instance: Optional["ConfigWindow"] = None


class ConfigWindow:
    """Agent 配置管理窗口"""

    def __init__(
        self,
        on_save: Optional[Callable] = None,
        on_close: Optional[Callable] = None,
    ):
        self._on_save = on_save
        self._on_close = on_close
        self._root: Optional[tk.Tk] = None
        self._hidden_root: Optional[tk.Tk] = None
        self._entries: dict = {}
        self._testing = False
        # 保持图标引用防止被垃圾回收
        self._icon_photo_small = None
        self._icon_photo_medium = None
        self._icon_photo_large = None

    @staticmethod
    def _get_logo_path() -> Path:
        """获取 logo.png 的路径"""
        if getattr(sys, "frozen", False):
            # PyInstaller 打包后，资源在 _MEIPASS 目录
            base = Path(sys._MEIPASS)  # type: ignore
        else:
            # 源码运行
            base = Path(__file__).parent
        return base / "assets" / "logo.png"

    def _set_window_icon(self, root: tk.Tk, hidden_root: tk.Tk = None):
        """设置窗口图标（左上角和任务栏）"""
        try:
            logo_path = self._get_logo_path()
            logger.info(f"Setting window icon from: {logo_path}, exists: {logo_path.exists()}")
            if logo_path.exists():
                # 使用 Pillow 加载 PNG 并转换为 PhotoImage
                from PIL import Image, ImageTk
                img = Image.open(logo_path)

                # 创建多个尺寸的图标（Windows 需要不同尺寸）
                # 小图标用于窗口左上角，大图标用于任务栏
                img_small = img.resize((16, 16), Image.Resampling.LANCZOS)
                img_medium = img.resize((32, 32), Image.Resampling.LANCZOS)
                img_large = img.resize((48, 48), Image.Resampling.LANCZOS)

                self._icon_photo_small = ImageTk.PhotoImage(img_small)
                self._icon_photo_medium = ImageTk.PhotoImage(img_medium)
                self._icon_photo_large = ImageTk.PhotoImage(img_large)

                # 设置 Toplevel 窗口图标（传入多个尺寸）
                root.iconphoto(True, self._icon_photo_large, self._icon_photo_medium, self._icon_photo_small)

                # 同时设置隐藏根窗口的图标（Windows 任务栏显示的是根窗口图标）
                if hidden_root:
                    hidden_root.iconphoto(True, self._icon_photo_large, self._icon_photo_medium, self._icon_photo_small)

                logger.info(f"Window icon set successfully from {logo_path}")
            else:
                logger.warning(f"Logo not found: {logo_path}")
        except Exception as e:
            logger.warning(f"Failed to set window icon: {e}")

    def show(self, wait: bool = False):
        """
        显示配置窗口。

        Args:
            wait: True 时阻塞直到窗口关闭（首次配置场景）
        """
        global _window_instance

        with _window_lock:
            # 如果已有窗口打开，尝试将其置顶
            if _window_instance is not None and _window_instance._root is not None:
                try:
                    # 使用 after 在 tkinter 主线程中执行置顶操作
                    _window_instance._root.after(0, _window_instance._bring_to_front)
                    logger.debug("Config window already open, bringing to front")
                    return
                except Exception:
                    # 窗口可能已销毁，继续创建新窗口
                    _window_instance = None

            _window_instance = self

        if wait:
            self._build_and_run()
        else:
            threading.Thread(target=self._build_and_run, daemon=True).start()

    def _bring_to_front(self):
        """将窗口置顶（必须在 tkinter 主线程调用）"""
        if self._root:
            try:
                self._root.deiconify()  # 如果最小化了，恢复
                self._root.lift()
                self._root.focus_force()
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    #  窗口构建
    # ------------------------------------------------------------------ #
    def _build_and_run(self):
        from ups_guard_agent.config import AgentConfig

        cfg = AgentConfig.load()
        logger.info("Opening config window")

        # 创建主窗口
        root = tk.Tk()
        self._root = root
        self._hidden_root = None

        root.title("UPS Guard Agent — 设置")
        root.resizable(False, False)

        # 设置窗口图标
        self._set_window_icon(root, None)

        # 居中显示 — 加宽窗口
        win_w, win_h = 580, 540
        scr_w = root.winfo_screenwidth()
        scr_h = root.winfo_screenheight()
        x = (scr_w - win_w) // 2
        y = (scr_h - win_h) // 2
        root.geometry(f"{win_w}x{win_h}+{x}+{y}")

        # 延迟设置置顶
        root.after(100, lambda: root.attributes("-topmost", True))
        root.after(500, lambda: root.attributes("-topmost", False))

        # --- 标题 ---
        title = tk.Label(root, text="⚡ UPS Guard Agent 配置", font=("", 14, "bold"))
        title.pack(pady=(15, 5))

        # --- 表单 ---
        form = ttk.Frame(root, padding=20)
        form.pack(fill="x")

        # (key, label, placeholder_hint, is_secret)
        fields = [
            ("server_url", "服务器地址", "如 http://192.168.1.100:8000", False),
            ("token", "API Token", "查看容器日志或环境变量 API_TOKEN", True),
            ("agent_name", "设备名称", socket.gethostname(), False),
            ("agent_id", "Agent ID（自动生成）", "", False),
        ]

        self._hint_labels = {}  # 保存 hint label 引用

        for row, (key, label, hint, is_secret) in enumerate(fields):
            ttk.Label(form, text=label + "：").grid(
                row=row, column=0, sticky="e", padx=(0, 8), pady=4
            )
            entry = ttk.Entry(form, width=46, show="•" if is_secret else "")
            entry.grid(row=row, column=1, sticky="w", pady=4)

            # 填充当前值
            current = getattr(cfg, key, "") or ""
            if current:
                entry.insert(0, current)

            # agent_id 只读
            if key == "agent_id":
                entry.config(state="readonly")

            self._entries[key] = entry

            # 输入提示 — 在输入框下方显示小字提示（仅当输入框为空时显示）
            if hint and key != "agent_id":
                hint_label = tk.Label(
                    form, text=f"  {hint}", font=("", 8),
                    foreground="grey", anchor="w",
                )
                hint_label.grid(row=row, column=1, sticky="sw", padx=(2, 0), pady=(22, 0))
                self._hint_labels[key] = hint_label

                # 如果已有内容，隐藏 hint
                if current:
                    hint_label.grid_remove()

                # 绑定输入事件，动态显示/隐藏 hint
                def make_hint_handler(k, lbl):
                    def handler(event=None):
                        if self._entries[k].get().strip():
                            lbl.grid_remove()
                        else:
                            lbl.grid()
                    return handler

                handler = make_hint_handler(key, hint_label)
                entry.bind("<KeyRelease>", handler)
                entry.bind("<FocusOut>", handler)

        # --- Token 显示/隐藏按钮 ---
        token_entry = self._entries["token"]
        show_var = tk.BooleanVar(value=False)

        def _toggle_token():
            token_entry.config(show="" if show_var.get() else "•")

        ttk.Checkbutton(
            form, text="显示", variable=show_var, command=_toggle_token
        ).grid(row=1, column=2, padx=4)

        # --- 提示信息 ---
        tip = tk.Label(
            root,
            text="💡 API Token 可在 UPS Guard 容器启动日志中查看，或通过环境变量 API_TOKEN 设置",
            font=("", 8), foreground="grey", wraplength=540, justify="left",
        )
        tip.pack(padx=20, anchor="w")

        # --- 服务端关机配置（只读展示） ---
        shutdown_frame = ttk.LabelFrame(root, text="服务端关机配置", padding=(12, 6))
        shutdown_frame.pack(fill="x", padx=20, pady=(8, 2))

        sd_row = ttk.Frame(shutdown_frame)
        sd_row.pack(fill="x", pady=2)
        ttk.Label(sd_row, text="关机延迟（秒）：", width=16, anchor="e").pack(side="left")
        self._srv_delay_var = tk.StringVar(value="—")
        ttk.Label(sd_row, textvariable=self._srv_delay_var, foreground="navy").pack(side="left")

        sm_row = ttk.Frame(shutdown_frame)
        sm_row.pack(fill="x", pady=2)
        ttk.Label(sm_row, text="关机提示消息：", width=16, anchor="e").pack(side="left")
        self._srv_message_var = tk.StringVar(value="—")
        ttk.Label(sm_row, textvariable=self._srv_message_var, foreground="navy",
                  wraplength=380, justify="left").pack(side="left")

        srv_info_row = ttk.Frame(shutdown_frame)
        srv_info_row.pack(fill="x", pady=(2, 0))
        self._srv_info_label = tk.Label(
            srv_info_row, text='（点击"从服务端刷新"获取最新配置）',
            font=("", 8), foreground="grey",
        )
        self._srv_info_label.pack(side="left")
        ttk.Button(
            srv_info_row, text="从服务端刷新",
            command=self._refresh_server_shutdown_config,
        ).pack(side="right")

        # --- 开机自启复选框 ---
        self._autostart_var = tk.BooleanVar(value=is_autostart_enabled())

        autostart_label = "开机自动启动"
        autostart_hint = ""
        if sys.platform == "win32":
            autostart_label = "开机自动启动（需要管理员权限）"
            autostart_hint = "将安装 Windows 服务，开机不登录也可自动运行"

        def _toggle_autostart():
            if self._autostart_var.get():
                try:
                    install_autostart()
                    if sys.platform == "win32":
                        self._status_label.config(text="✅ 正在请求管理员权限安装服务，请在 UAC 弹窗中确认", foreground="green")
                    else:
                        self._status_label.config(text="✅ 已设置开机自启", foreground="green")
                    logger.info("Autostart enabled via GUI")
                except Exception as e:
                    self._status_label.config(text=f"❌ 设置失败: {e}", foreground="red")
                    self._autostart_var.set(False)
            else:
                try:
                    remove_autostart()
                    if sys.platform == "win32":
                        self._status_label.config(text="✅ 正在请求管理员权限卸载服务，请在 UAC 弹窗中确认", foreground="green")
                    else:
                        self._status_label.config(text="✅ 已取消开机自启", foreground="green")
                    logger.info("Autostart disabled via GUI")
                except Exception as e:
                    self._status_label.config(text=f"❌ 取消失败: {e}", foreground="red")
                    self._autostart_var.set(True)

        autostart_frame = ttk.Frame(root, padding=(20, 4))
        autostart_frame.pack(fill="x")
        ttk.Checkbutton(
            autostart_frame,
            text=autostart_label,
            variable=self._autostart_var,
            command=_toggle_autostart,
        ).pack(side="left")
        if autostart_hint:
            tk.Label(
                autostart_frame, text=autostart_hint,
                font=("", 8), foreground="grey",
            ).pack(side="left", padx=(8, 0))

        # --- 按钮栏 — 使用两行布局避免遮盖问题 ---
        btn_frame = ttk.Frame(root, padding=(20, 10))
        btn_frame.pack(fill="x", side="bottom")

        # 第一行：状态标签（右键可复制）
        self._status_label = ttk.Label(btn_frame, text="", foreground="grey", wraplength=540)
        self._status_label.pack(fill="x", pady=(0, 6))
        self._status_label.bind("<Button-3>", self._show_status_menu)

        # 第二行：按钮
        btn_row = ttk.Frame(btn_frame)
        btn_row.pack(fill="x")

        ttk.Button(btn_row, text="重置 Agent ID", command=self._reset_agent_id).pack(
            side="left", padx=4
        )
        ttk.Button(btn_row, text="测试连接", command=self._test_connection).pack(
            side="right", padx=4
        )
        ttk.Button(btn_row, text="保存", command=self._save).pack(
            side="right", padx=4
        )

        # 关闭窗口
        root.protocol("WM_DELETE_WINDOW", self._on_window_close)

        # 窗口打开后自动从服务端拉取关机配置（延迟 600 ms 等渲染完成）
        root.after(600, self._refresh_server_shutdown_config)

        root.mainloop()

    # ------------------------------------------------------------------ #
    #  保存
    # ------------------------------------------------------------------ #
    def _save(self):
        from ups_guard_agent.config import AgentConfig

        server = self._entries["server_url"].get().strip()
        token = self._entries["token"].get().strip()
        name = self._entries["agent_name"].get().strip()

        if not server:
            messagebox.showwarning("提示", "请输入服务器地址\n例如：http://192.168.1.100:8000")
            return
        if not token:
            messagebox.showwarning("提示", "请输入 API Token\n可在容器启动日志或环境变量 API_TOKEN 中找到")
            return

        cfg = AgentConfig.load()
        old_server = cfg.server_url
        old_token = cfg.token

        cfg.server_url = server
        cfg.token = token
        cfg.agent_name = name or socket.gethostname()
        cfg.save()

        # 更新只读的 agent_id 显示
        id_entry = self._entries["agent_id"]
        id_entry.config(state="normal")
        id_entry.delete(0, tk.END)
        id_entry.insert(0, cfg.agent_id)
        id_entry.config(state="readonly")

        self._status_label.config(text="✅ 配置已保存", foreground="green")
        logger.info(f"Config saved: server={server} name={cfg.agent_name}")

        if self._on_save:
            self._on_save(cfg)

        # 首次配置（之前没有有效配置）：保存后自动关闭窗口，让程序继续连接
        if not old_server or not old_token:
            logger.info("First-time config saved, closing window to start connection")
            self._root.after(500, self._on_window_close)  # 延迟 0.5 秒关闭，让用户看到保存成功提示

    # ------------------------------------------------------------------ #
    #  重置 Agent ID — 使用与 config.py 一致的长度
    # ------------------------------------------------------------------ #
    def _reset_agent_id(self):
        if not messagebox.askyesno(
            "确认",
            "重置 Agent ID 后，服务端会将本机识别为新设备。\n"
            "（MAC 地址相同时会自动更新关联，不会重复创建任务）\n\n"
            "确定要重置吗？",
        ):
            return

        from ups_guard_agent.config import AgentConfig

        cfg = AgentConfig.load()
        cfg.agent_id = AgentConfig.generate_agent_id()  # 统一使用同一个方法
        cfg.save()

        id_entry = self._entries["agent_id"]
        id_entry.config(state="normal")
        id_entry.delete(0, tk.END)
        id_entry.insert(0, cfg.agent_id)
        id_entry.config(state="readonly")

        self._status_label.config(text="🔄 Agent ID 已重置为 " + cfg.agent_id, foreground="orange")

    # ------------------------------------------------------------------ #
    #  测试连接
    # ------------------------------------------------------------------ #
    def _test_connection(self):
        if self._testing:
            return
        self._testing = True
        self._status_label.config(text="⏳ 正在测试连接…", foreground="grey")

        server = self._entries["server_url"].get().strip()
        token = self._entries["token"].get().strip()

        if not server:
            self._status_label.config(text="❌ 请先输入服务器地址", foreground="red")
            self._testing = False
            return

        def _do_test():
            try:
                import urllib.request
                import json

                # 先测试连通性（/health 不需要认证）
                health_url = server.rstrip("/") + "/health"
                logger.info(f"Testing connection: GET {health_url}")
                t0 = time.monotonic()
                health_req = urllib.request.Request(health_url, method="GET")
                with urllib.request.urlopen(health_req, timeout=5) as resp:
                    elapsed_ms = int((time.monotonic() - t0) * 1000)
                    logger.info(f"Health check: status={resp.status} elapsed={elapsed_ms}ms")
                    health_body = json.loads(resp.read())
                    version = health_body.get("version", "?")

                # 再验证 Token（/api/config 需要认证）
                config_url = server.rstrip("/") + "/api/config"
                masked_token = (token[:4] + "****") if token else ""
                logger.info(f"Testing token: GET {config_url} token={masked_token}")
                t1 = time.monotonic()
                config_req = urllib.request.Request(
                    config_url,
                    headers={"Authorization": f"Bearer {token}"},
                    method="GET",
                )
                with urllib.request.urlopen(config_req, timeout=5) as resp:
                    elapsed_ms = int((time.monotonic() - t1) * 1000)
                    logger.info(f"Token check: status={resp.status} elapsed={elapsed_ms}ms")

                logger.info(f"Connection test passed (v{version})")
                self._update_status(f"✅ 连接成功，Token 验证通过 (v{version})", "green")
            except Exception as e:
                err_msg = str(e)
                logger.warning(f"Connection test failed: {err_msg}")
                # 简化常见错误信息
                if "urlopen error" in err_msg:
                    err_msg = "无法连接到服务器，请检查地址和网络"
                elif "HTTP Error 401" in err_msg or "HTTP Error 403" in err_msg:
                    err_msg = "Token 验证失败，请检查 API Token 是否正确"
                elif "HTTP Error" in err_msg:
                    err_msg = f"服务器错误: {err_msg}"
                self._update_status(f"❌ {err_msg}", "red")
            finally:
                self._testing = False

        threading.Thread(target=_do_test, daemon=True).start()

    def _update_status(self, text: str, color: str):
        if self._root:
            self._root.after(0, lambda: self._status_label.config(text=text, foreground=color))

    # ------------------------------------------------------------------ #
    #  状态栏右键复制
    # ------------------------------------------------------------------ #
    def _show_status_menu(self, event):
        """右键弹出菜单，允许复制状态栏文字"""
        text = self._status_label.cget("text")
        if not text:
            return
        menu = tk.Menu(self._root, tearoff=0)
        menu.add_command(label="复制", command=self._copy_status_to_clipboard)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.destroy()

    def _copy_status_to_clipboard(self):
        """将状态栏当前文字写入系统剪贴板"""
        if self._root:
            text = self._status_label.cget("text")
            self._root.clipboard_clear()
            self._root.clipboard_append(text)
            logger.debug(f"Copied to clipboard: {text}")

    # ------------------------------------------------------------------ #
    #  关闭
    # ------------------------------------------------------------------ #
    def _on_window_close(self):
        """关闭窗口时清理资源"""
        global _window_instance

        logger.info("Settings window closed")
        if self._root:
            self._root.destroy()
            self._root = None

        # 销毁隐藏的根窗口（结束 mainloop）
        if hasattr(self, '_hidden_root') and self._hidden_root:
            self._hidden_root.destroy()
            self._hidden_root = None

        # 清除单例引用，允许再次打开窗口
        with _window_lock:
            if _window_instance is self:
                _window_instance = None

    # ------------------------------------------------------------------ #
    #  从服务端刷新关机配置
    # ------------------------------------------------------------------ #
    def _refresh_server_shutdown_config(self):
        """后台线程：从服务端 /api/config 拉取关机配置并更新 UI"""
        threading.Thread(target=self._do_refresh_server_config, daemon=True).start()

    def _do_refresh_server_config(self):
        from ups_guard_agent.config import AgentConfig
        import urllib.request
        import urllib.error
        import json

        cfg = AgentConfig.load()
        if not cfg.server_url or not cfg.token:
            self._update_srv_info("❌ 请先填写服务器地址和 Token", "red")
            return

        url = cfg.server_url.rstrip("/") + "/api/config"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {cfg.token}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
        except urllib.error.URLError as e:
            self._update_srv_info(f"❌ 无法连接服务端（{e.reason}）", "red")
            return
        except TimeoutError:
            self._update_srv_info("❌ 连接服务端超时，请检查网络", "red")
            return
        except Exception as e:
            self._update_srv_info(f"❌ 获取配置失败：{e}", "red")
            return

        hooks = data.get("pre_shutdown_hooks", [])
        for hook in hooks:
            if hook.get("hook_id") != "agent_shutdown":
                continue
            hook_cfg = hook.get("config", {})
            if hook_cfg.get("agent_id", "") == cfg.agent_id:
                delay = hook_cfg.get("shutdown_delay", "—")
                message = hook_cfg.get("shutdown_message", "（未设置）")
                self._update_srv_delay(str(delay))
                self._update_srv_message(message or "（未设置）")
                self._update_srv_info("✅ 已从服务端同步", "green")
                logger.info(f"Server shutdown config: delay={delay} message={message!r}")
                return

        self._update_srv_info("⚠️ 服务端未找到本机的关机配置（Agent 需先连接一次服务端）", "darkorange")

    def _update_srv_delay(self, value: str):
        if self._root:
            self._root.after(0, lambda: self._srv_delay_var.set(value))

    def _update_srv_message(self, value: str):
        if self._root:
            self._root.after(0, lambda: self._srv_message_var.set(value))

    def _update_srv_info(self, text: str, color: str):
        if self._root:
            self._root.after(
                0, lambda: self._srv_info_label.config(text=text, foreground=color)
            )


