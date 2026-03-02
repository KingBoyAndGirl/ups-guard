# ⚡ UPS Guard

通用 UPS 智能监控与管理应用，支持在任意 Docker 环境中部署，可同时纳管 Windows、Linux、macOS、群辉、威联通、懒猫微服等多种设备。

Universal UPS monitoring and management application that supports deployment on any device with Docker (Windows, Mac, Linux, Synology, QNAP, LazyCAT, etc.) with centralized management of multiple devices.

**开发者 / Developer**： 王.W

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL%203.0-blue.svg)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/KingBoyAndGirl/ups-guard)](https://github.com/KingBoyAndGirl/ups-guard/releases)
[![Version](https://img.shields.io/badge/version-1.0.0-brightgreen.svg)](https://github.com/KingBoyAndGirl/ups-guard/releases/tag/v1.0.0)

> 📖 **Language / 语言**: [中文文档](docs/zh/README.md) | [English Documentation](docs/en/README.md) | [Documentation Index / 文档索引](docs/zh/INDEX.md)

## 🧪 测试环境 / Tested Environment

本项目已在以下环境验证 / This project has been tested in the following environment:
- **操作系统 / OS**：Windows 11
- **部署平台 / Platform**：懒猫微服 (LazyCAT Micro Services) - Docker
- **UPS型号 / UPS Model**：APC Back-UPS BK650M2-CH (650VA)
- **NUT版本 / NUT Version**：2.8.3

> ⚠️ **注意 / Note**：其他操作系统和UPS型号尚未测试 / Other OS and UPS models have not been tested yet. 欢迎反馈兼容性信息 / Compatibility feedback is welcome.

## ✨ 功能特性

### v1.0 正式版 🎉
- 🔒 **安全加固** - API Token 认证、敏感数据加密、CORS 限制
- 🌍 **国际化支持** - 中英文双语界面和通知消息
- 📈 **性能优化** - SQLite WAL 模式、数据降采样、懒加载
- 🛡️ **错误恢复** - gRPC/NUT 自动重连、事务保护、详细日志
- 🐳 **优化部署** - 多阶段构建、健康检查、轻量镜像
- 🌙 **深色模式** - 支持亮色/暗色/跟随系统三种主题，自动适配所有组件
- 📱 **移动端适配** - 完整的响应式设计，支持手机、平板、桌面各种屏幕
- 📊 **数据管理** - 可视化数据库大小和记录统计，一键清理历史数据
- 🔔 **更多推送渠道** - 新增钉钉、Telegram、邮件 SMTP、通用 Webhook 支持

### 核心功能
- 🔌 **实时监控** - WebSocket 实时推送 UPS 状态，无需刷新
- 🔋 **智能关机** - 停电后自动倒计时关机，市电恢复自动取消
- 📈 **数据可视化** - ECharts 实时曲线图，直观展示电量、电压、负载等指标
- 📱 **推送通知** - 支持 6 种通知渠道：Server酱、PushPlus、钉钉、Telegram、邮件、Webhook
- 📝 **历史记录** - 完整的事件日志和指标采样，最长保留 90 天
- 🔧 **灵活配置** - 关机策略、通知渠道、采样间隔等均可自定义
- 🔌 **插件系统** - 支持自定义通知插件，轻松扩展通知渠道
- 🎨 **现代界面** - Vue 3 + TypeScript，简洁卡片风格，深色模式，响应式设计
- 🐳 **容器化部署** - 三服务架构，一键安装，开箱即用

## 📸 界面预览

### 仪表盘
- 实时状态监控（在线/电池供电/低电量）
- 电池电量仪表盘
- 输入/输出电压、负载百分比、温度等关键指标
- 实时数据曲线图
- 最近事件列表

<img width="2940" height="4458" alt="image" src="https://github.com/user-attachments/assets/368003c4-2278-48d2-87a5-2b242d44613c" />

<img width="2940" height="1604" alt="image" src="https://github.com/user-attachments/assets/9cb624a3-3cf9-4765-aed8-1b42a4e453b3" />


### 设置页面
- 关机策略配置（等待时间、最低电量、最终等待）
- 推送通知配置（多渠道支持）
- 数据采样和保留设置

<img width="2940" height="5530" alt="image" src="https://github.com/user-attachments/assets/9398e9f8-4608-47b4-a10a-46db0cba9b72" />


### 历史记录
- 长期趋势图表（24 小时）
- 事件时间线

<img width="2940" height="2730" alt="image" src="https://github.com/user-attachments/assets/e5b13832-8392-4ac5-adc7-f5b0a1f42d49" />

## 🚀 快速开始

### 部署方式

UPS Guard 支持在任意有 Docker 的设备上运行，可通过 USB 连接 UPS，并远程管理局域网内的其他设备：

| 设备类型 | 部署方式 | 配置文件位置 |
|---------|---------|-------------|
| 懒猫微服 | 原生应用安装 | [`deploy/lazycat/`](deploy/lazycat/) |
| 群晖 NAS | Container Manager | [`deploy/synology/`](deploy/synology/) |
| 威联通 NAS | Container Station | [`deploy/qnap/`](deploy/qnap/) |
| Linux/Windows/Mac | Docker Compose | [`deploy/docker/`](deploy/docker/) |

> 📁 完整部署配置文件请查看 [`deploy/`](deploy/) 目录

### Docker 部署（通用部署）

支持在任何有 Docker 的设备上运行（Win11、Mac、Linux、群辉、威联通等）。

#### 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/KingBoyAndGirl/ups-guard.git
cd ups-guard/deploy/docker

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，根据实际情况修改配置

# 3. 启动服务
docker-compose up -d

# 4. 访问 Web 界面
# 浏览器打开 http://localhost
```

详细 Docker 部署指南请查看 [Docker 部署文档](docs/zh/docker-deployment.md) ([English](docs/en/docker-deployment.md))。

### 懒猫微服部署

#### 系统要求

- 懒猫微服 LZCOS 系统
- 支持 USB 的 UPS 设备
- 至少 1GB 可用存储空间

#### 安装步骤

1. **下载应用包**
   ```bash
   # 从 GitHub Releases 下载最新版本
   wget https://github.com/KingBoyAndGirl/ups-guard/releases/latest/download/ups-guard.lpk
   ```

2. **安装应用**
   - 进入懒猫微服控制面板
   - 应用商店 → 本地安装
   - 选择 `ups-guard.lpk` 文件
   - 等待安装完成

3. **连接 UPS**
   - 通过 USB 连接 UPS 到懒猫微服主机
   - 应用会自动检测设备

4. **访问应用**
   ```
   http://your-lazycat-host/ups-guard/
   ```

5. **配置 API Token (v1.0+)**
   
   首次启动时，应用会自动生成 API Token 并在日志中打印。建议在懒猫控制面板中设置环境变量：
   
   - 进入应用设置
   - 添加环境变量 `API_TOKEN=<your-token>`
   - 重启应用
   
   前端访问时会自动使用配置的 Token 进行认证。

详细安装指南请查看 [安装文档](docs/zh/install.md) ([English](docs/en/install.md))。

## ⚙️ 配置说明

### 环境变量

**NUT 配置**
- `NUT_HOST`: NUT 服务器地址（默认: `nut-server`）
- `NUT_PORT`: NUT 服务器端口（默认: `3493`）
- `NUT_USERNAME`: NUT 用户名（默认: `monuser`）
- `NUT_PASSWORD`: NUT 密码（默认: `secret`）
- `NUT_UPS_NAME`: UPS 设备名称（默认: `ups`）

**安全配置**
- `API_TOKEN`: API 认证 Token（未设置则自动生成）
- `ENCRYPTION_KEY`: 敏感数据加密密钥（未设置则自动生成并保存）
- `ALLOWED_ORIGINS`: CORS 允许的来源（逗号分隔，默认仅允许同域）

**数据库配置**
- `DATABASE_PATH`: 数据库文件路径（默认: `/data/ups_guard.db`）

**其他**
- `LOG_LEVEL`: 日志级别（默认: `INFO`）
- `MOCK_MODE`: 开发模式（默认: `false`）

## 📚 文档 / Documentation

> 💡 **提示**: 本项目提供中英文双语文档 / This project provides bilingual documentation in Chinese and English.

### 中文文档
- [完整文档索引](docs/index.md) - 所有文档导航页
- [项目介绍](docs/zh/README.md) - 详细的项目说明
- [安装指南](docs/zh/install.md) - 完整的安装和配置步骤
- [用户指南](docs/zh/user-guide.md) - 详细使用说明
- [Docker 部署指南](docs/zh/docker-deployment.md) - Docker 环境部署
- [支持的 UPS 设备](docs/zh/supported-ups.md) - 兼容设备列表
- [推送通知配置](docs/zh/push-setup.md) - 通知渠道配置教程
- [插件开发指南](docs/zh/plugin-dev.md) - 自定义通知插件开发
- [架构文档](docs/zh/architecture.md) - 系统架构和技术细节
- [常见问题](docs/zh/faq.md) - FAQ
- [更新日志](docs/zh/changelog.md) - 版本历史

### English Documentation
- [Documentation Index](docs/index.md) - All documentation navigation
- [Project Overview](docs/en/README.md) - Detailed project introduction
- [Installation Guide](docs/en/install.md) - Complete installation and configuration
- [User Guide](docs/en/user-guide.md) - Detailed usage instructions
- [Docker Deployment Guide](docs/en/docker-deployment.md) - Docker environment deployment
- [Supported UPS Devices](docs/en/supported-ups.md) - Compatible device list
- [Push Notification Setup](docs/en/push-setup.md) - Notification channel configuration
- [Plugin Development Guide](docs/en/plugin-dev.md) - Custom plugin development
- [Architecture](docs/en/architecture.md) - System architecture and technical details
- [FAQ](docs/en/faq.md) - Frequently asked questions
- [Changelog](docs/en/changelog.md) - Version history

## 🛠️ 技术栈

### 后端
- **语言**: Python 3.11+
- **框架**: FastAPI + Uvicorn
- **依赖管理**: uv
- **数据库**: SQLite + aiosqlite
- **UPS 通信**: Network UPS Tools (NUT)
- **系统集成**: gRPC (LZCOS API)

### 前端
- **框架**: Vue 3 (Composition API)
- **语言**: TypeScript
- **构建工具**: Vite
- **包管理器**: pnpm
- **图表**: ECharts
- **状态管理**: Pinia
- **路由**: Vue Router

### 部署
- **容器化**: Docker + Docker Compose
- **打包格式**: 懒猫原生应用 lpk 格式（懒猫微服专用）
- **反向代理**: Nginx

## 🏗️ 项目结构

```
ups-guard/
├── backend/              # Python FastAPI 后端
│   ├── src/
│   │   ├── api/          # REST API 端点
│   │   ├── db/           # 数据库模型和 schema
│   │   ├── models/       # Pydantic 数据模型
│   │   ├── plugins/      # 通知插件
│   │   ├── services/     # 核心业务逻辑
│   │   └── main.py       # 应用入口
│   ├── Dockerfile
│   └── pyproject.toml    # uv 依赖配置
├── frontend/             # Vue 3 前端
│   ├── src/
│   │   ├── components/   # UI 组件
│   │   ├── composables/  # 组合式函数
│   │   ├── views/        # 页面视图
│   │   ├── router/       # 路由配置
│   │   └── stores/       # 状态管理
│   ├── Dockerfile
│   └── package.json
├── nut/                  # NUT Server 容器
│   ├── Dockerfile
│   └── entrypoint.sh
├── deploy/               # 部署配置文件
│   ├── docker/           # 通用 Docker 部署
│   ├── lazycat/          # 懒猫微服部署
│   ├── synology/         # 群晖 NAS 部署
│   └── qnap/             # 威联通 NAS 部署
└── docs/                 # 文档
```

## 🔧 开发

### 本地开发环境

```bash
# 克隆仓库
git clone https://github.com/KingBoyAndGirl/ups-guard.git
cd ups-guard

# 启动后端（Mock 模式）
cd backend
uv pip install -r pyproject.toml
MOCK_MODE=true uvicorn src.main:app --reload

# 启动前端
cd frontend
pnpm install
pnpm dev
```

访问 `http://localhost:5173` 查看前端。

### 构建应用

```bash
# 构建所有容器
./build.sh

# 或使用 lzc-cli（懒猫微服打包，需安装 lzc-cli）
lzc-cli package -m lzc-manifest.yml -o ups-guard.lpk
```

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

请确保：
- 遵循现有代码风格
- 添加必要的测试
- 更新相关文档
- 圈复杂度不超过 20

## 📄 开源协议

本项目采用 **AGPL-3.0 + 商业授权双协议**模式。

- **AGPL-3.0**: 个人使用和开源项目免费，需遵守开源协议
- **商业授权**: 闭源商业使用需获得商业授权

详见：
- [AGPL-3.0 协议](LICENSE)
- [商业授权协议](COMMERCIAL_LICENSE.md)

## 🙏 致谢

- [Network UPS Tools](https://networkupstools.org/) - UPS 通信协议
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Python Web 框架
- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
- [ECharts](https://echarts.apache.org/) - 数据可视化图表库

## 📧 联系我们

- GitHub: [@KingBoyAndGirl](https://github.com/KingBoyAndGirl)
- Issues: [提交问题](https://github.com/KingBoyAndGirl/ups-guard/issues)
- Discussions: [参与讨论](https://github.com/KingBoyAndGirl/ups-guard/discussions)

---

## ⭐ Star History

<a href="https://star-history.com/#KingBoyAndGirl/ups-guard&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=KingBoyAndGirl/ups-guard&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=KingBoyAndGirl/ups-guard&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=KingBoyAndGirl/ups-guard&type=Date" />
 </picture>
</a>

---

如果这个项目对您有帮助，请给个 ⭐️ Star 支持一下！
