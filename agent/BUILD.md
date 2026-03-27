# UPS Guard Agent 打包指南

本文档介绍如何将 UPS Guard Agent 打包为 Windows 可执行文件 (.exe)。

## 📋 环境要求

- **Python**: >= 3.11
- **包管理器**: [uv](https://github.com/astral-sh/uv) (推荐) 或 pip
- **操作系统**: Windows (打包 Windows 版本)

## 🚀 快速打包

### 方法一：使用 build_exe.py 脚本（推荐）

这是最简单的方式，脚本会自动处理图标转换和 PyInstaller 配置。

```powershell
# 1. 进入 agent 目录
cd agent

# 2. 安装依赖（首次运行）
uv sync --dev

# 3. 执行打包脚本
uv run python build_exe.py
```

打包完成后，可执行文件位于：`agent/dist/UPSGuardAgent.exe`

### 方法二：使用 PyInstaller spec 文件

如果需要更精细的控制，可以直接使用 spec 文件：

```powershell
# 1. 进入 agent 目录
cd agent

# 2. 安装依赖
uv sync --dev

# 3. 使用 spec 文件打包
uv run pyinstaller UPSGuardAgent.spec
```

## 📦 依赖说明

### 运行时依赖
| 包名 | 版本 | 用途 |
|------|------|------|
| websockets | >=12.0 | WebSocket 客户端通信 |
| pystray | >=0.19 | 系统托盘图标 |
| Pillow | >=10.0 | 图像处理（图标） |
| psutil | >=5.9 | 系统信息获取 |

### 开发依赖
| 包名 | 版本 | 用途 |
|------|------|------|
| pyinstaller | >=6.0 | 打包为可执行文件 |
| pytest | >=7.4.0 | 单元测试 |

## 🔧 打包配置详解

### build_exe.py 脚本功能

1. **图标转换**: 自动将 `frontend/public/logo.png` 转换为 Windows ICO 格式
2. **清理构建目录**: 自动清理 `dist/` 和 `build/` 目录
3. **Hidden Imports**: 自动添加所有必要的隐藏导入
4. **资源打包**: 将 `assets/` 目录打包到可执行文件中

### 隐藏导入列表

由于 PyInstaller 静态分析的限制，以下模块需要手动指定：

- `pystray` - 托盘图标
- `PIL` / `PIL._tkinter_finder` - 图像处理
- `psutil` - 系统信息
- `websockets` - WebSocket 客户端
- `ups_guard_agent.*` - 应用模块

## 📁 目录结构

```
agent/
├── build_exe.py          # 打包脚本
├── UPSGuardAgent.spec    # PyInstaller 配置文件
├── UPSGuardAgent.ico     # 应用图标（打包时自动生成）
├── pyproject.toml        # 项目配置
├── src/
│   └── ups_guard_agent/  # 源代码
│       ├── main.py       # 入口点
│       ├── assets/       # 资源文件
│       │   └── logo.png
│       ├── autostart.py  # 开机自启动
│       ├── client.py     # WebSocket 客户端
│       ├── commands.py   # 命令处理
│       ├── config.py     # 配置管理
│       ├── gui.py        # GUI 窗口
│       ├── system_info.py # 系统信息
│       └── tray.py       # 托盘图标
├── dist/                 # 输出目录
│   └── UPSGuardAgent.exe # 打包后的可执行文件
└── build/                # 临时构建目录
```

## ⚠️ 常见问题

### 1. 缺少 logo.png

如果 `frontend/public/logo.png` 不存在，打包会继续但不会有自定义图标。

### 2. PyInstaller 未安装

```powershell
# 确保安装了开发依赖
uv sync --dev
```

### 3. 打包后程序无法运行

检查是否缺少隐藏导入。如果添加了新模块，需要在 `build_exe.py` 中添加对应的 `--hidden-import`。

### 4. 杀毒软件误报

PyInstaller 打包的程序可能被部分杀毒软件误报。这是已知问题，可以：
- 将程序添加到杀毒软件白名单
- 对程序进行代码签名

## 🔄 CI/CD 集成

如果需要在 CI 环境中打包，示例命令：

```bash
cd agent
pip install uv
uv sync --dev
uv run python build_exe.py
```

## 📝 自定义打包

如需自定义打包配置，可以修改 `UPSGuardAgent.spec` 文件：

- **name**: 输出文件名
- **icon**: 图标路径
- **datas**: 需要打包的数据文件
- **hiddenimports**: 隐藏导入
- **console**: 是否显示控制台窗口（设为 False 隐藏）

---

打包成功后，`UPSGuardAgent.exe` 是一个独立的可执行文件，可以直接分发给用户使用。

