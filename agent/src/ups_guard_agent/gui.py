"""图形化配置窗口（tkinter）"""
import logging
import socket
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional

from ups_guard_agent.autostart import is_autostart_enabled, install_autostart, remove_autostart

logger = logging.getLogger(__name__)


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
        self._entries: dict = {}
        self._testing = False

    def show(self, wait: bool = False):
        """
        显示配置窗口。

        Args:
            wait: True 时阻塞直到窗口关闭（首次配置场景）
        """
        if wait:
            self._build_and_run()
        else:
            threading.Thread(target=self._build_and_run, daemon=True).start()

    # ------------------------------------------------------------------ #
    #  窗口构建
    # ------------------------------------------------------------------ #
    def _build_and_run(self):
        from ups_guard_agent.config import AgentConfig

        cfg = AgentConfig.load()

        root = tk.Tk()
        self._root = root
        root.title("UPS Guard Agent — 设置")
        root.resizable(False, False)
        root.attributes("-topmost", True)

        # 居中显示 — 加宽窗口
        win_w, win_h = 580, 470
        scr_w = root.winfo_screenwidth()
        scr_h = root.winfo_screenheight()
        x = (scr_w - win_w) // 2
        y = (scr_h - win_h) // 2
        root.geometry(f"{win_w}x{win_h}+{x}+{y}")

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

        # --- 开机自启复选框 ---
        self._autostart_var = tk.BooleanVar(value=is_autostart_enabled())

        def _toggle_autostart():
            if self._autostart_var.get():
                try:
                    install_autostart()
                    self._status_label.config(text="✅ 已设置开机自启", foreground="green")
                    logger.info("Autostart enabled via GUI")
                except Exception as e:
                    self._status_label.config(text=f"❌ 设置失败: {e}", foreground="red")
                    self._autostart_var.set(False)
            else:
                try:
                    remove_autostart()
                    self._status_label.config(text="✅ 已取消开机自启", foreground="green")
                    logger.info("Autostart disabled via GUI")
                except Exception as e:
                    self._status_label.config(text=f"❌ 取消失败: {e}", foreground="red")
                    self._autostart_var.set(True)

        autostart_frame = ttk.Frame(root, padding=(20, 4))
        autostart_frame.pack(fill="x")
        ttk.Checkbutton(
            autostart_frame,
            text="开机自动启动",
            variable=self._autostart_var,
            command=_toggle_autostart,
        ).pack(side="left")

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
                health_req = urllib.request.Request(health_url, method="GET")
                with urllib.request.urlopen(health_req, timeout=5) as resp:
                    health_body = json.loads(resp.read())
                    version = health_body.get("version", "?")

                # 再验证 Token（/api/config 需要认证）
                config_url = server.rstrip("/") + "/api/config"
                config_req = urllib.request.Request(
                    config_url,
                    headers={"Authorization": f"Bearer {token}"},
                    method="GET",
                )
                with urllib.request.urlopen(config_req, timeout=5) as resp:
                    pass  # 200 = Token 正确

                self._update_status(f"✅ 连接成功，Token 验证通过 (v{version})", "green")
            except Exception as e:
                err_msg = str(e)
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
        """关闭窗口时询问用户是退出还是最小化"""
        # 弹出三选一对话框
        result = messagebox.askyesnocancel(
            "关闭设置",
            "请选择操作：\n\n"
            "• 点击「是」— 最小化到系统托盘（后台继续运行）\n"
            "• 点击「否」— 完全退出 Agent\n"
            "• 点击「取消」— 返回设置窗口",
        )

        if result is None:
            # 取消 — 不做任何操作
            return
        elif result:
            # 是 — 最小化到托盘（仅关闭设置窗口）
            if self._root:
                self._root.destroy()
                self._root = None
            # 不调用 on_close，让 Agent 继续在托盘运行
        else:
            # 否 — 完全退出
            if self._root:
                self._root.destroy()
                self._root = None
            if self._on_close:
                self._on_close()


