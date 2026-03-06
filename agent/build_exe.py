"""
UPS Guard Agent — PyInstaller 打包脚本

用法:
    cd agent
    uv run python build_exe.py

输出: agent/dist/UPSGuardAgent.exe
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ------------------------------------------------------------------ #
#  路径常量
# ------------------------------------------------------------------ #
AGENT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = AGENT_DIR.parent
LOGO_PNG = REPO_ROOT / "frontend" / "public" / "logo.png"
ICON_ICO = AGENT_DIR / "UPSGuardAgent.ico"
ENTRY = AGENT_DIR / "src" / "ups_guard_agent" / "main.py"
ASSETS_DIR = AGENT_DIR / "src" / "ups_guard_agent" / "assets"
DIST_DIR = AGENT_DIR / "dist"
BUILD_DIR = AGENT_DIR / "build"
OUTPUT_NAME = "UPSGuardAgent"


def convert_png_to_ico(png_path: Path, ico_path: Path) -> None:
    """将 PNG 转换为 Windows ICO 格式（需要 Pillow）"""
    from PIL import Image  # type: ignore

    img = Image.open(png_path)
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format="ICO", sizes=sizes)
    print(f"[build] Icon converted: {ico_path}")


def run_pyinstaller(icon_path) -> None:
    """调用 PyInstaller 进行打包"""
    # Bundle assets directory (logo.png etc.) for GUI window icons
    sep = ";" if sys.platform == "win32" else ":"
    add_data_assets = f"{ASSETS_DIR}{sep}ups_guard_agent/assets"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        f"--name={OUTPUT_NAME}",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--add-data={add_data_assets}",
        "--hidden-import=pystray",
        "--hidden-import=PIL",
        "--hidden-import=PIL._tkinter_finder",
        "--hidden-import=psutil",
        "--hidden-import=websockets",
        "--hidden-import=ups_guard_agent.autostart",
        "--hidden-import=ups_guard_agent.config",
        "--hidden-import=ups_guard_agent.gui",
        "--hidden-import=ups_guard_agent.tray",
        "--hidden-import=ups_guard_agent.client",
        "--hidden-import=ups_guard_agent.commands",
        "--hidden-import=ups_guard_agent.system_info",
        "--hidden-import=ups_guard_agent.win_service",
        "--hidden-import=win32serviceutil",
        "--hidden-import=win32service",
        "--hidden-import=win32event",
        "--hidden-import=servicemanager",
        "--hidden-import=win32api",
        str(ENTRY),
    ]
    if icon_path is not None:
        cmd.insert(4, f"--icon={icon_path}")
    print(f"[build] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=AGENT_DIR)
    if result.returncode != 0:
        print("[build] PyInstaller failed!", file=sys.stderr)
        sys.exit(result.returncode)


def main() -> None:
    print(f"[build] Agent dir  : {AGENT_DIR}")
    print(f"[build] Entry point: {ENTRY}")
    print(f"[build] Logo PNG   : {LOGO_PNG}")

    if not ENTRY.exists():
        print(f"[build] ERROR: entry point not found: {ENTRY}", file=sys.stderr)
        sys.exit(1)

    # 图标转换
    if LOGO_PNG.exists():
        convert_png_to_ico(LOGO_PNG, ICON_ICO)
        icon_arg = ICON_ICO
    else:
        print(f"[build] WARNING: logo.png not found at {LOGO_PNG}, building without icon")
        icon_arg = None

    # 清理上次构建产物
    for d in (DIST_DIR, BUILD_DIR):
        if d.exists():
            shutil.rmtree(d)
            print(f"[build] Cleaned: {d}")

    # 打包
    run_pyinstaller(icon_arg)

    exe = DIST_DIR / f"{OUTPUT_NAME}.exe"
    if exe.exists():
        size_mb = exe.stat().st_size / 1024 / 1024
        print(f"[build] ✅ Done: {exe}  ({size_mb:.1f} MB)")
    else:
        # Linux / macOS 没有 .exe 后缀
        binary = DIST_DIR / OUTPUT_NAME
        if binary.exists():
            size_mb = binary.stat().st_size / 1024 / 1024
            print(f"[build] ✅ Done: {binary}  ({size_mb:.1f} MB)")
        else:
            print(f"[build] WARNING: expected output not found in {DIST_DIR}", file=sys.stderr)

    # 清理临时 ico
    if ICON_ICO.exists():
        ICON_ICO.unlink()


if __name__ == "__main__":
    main()
