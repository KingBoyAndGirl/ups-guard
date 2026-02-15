# 📚 文档索引

## 快速开始

- [📖 README](README.md) - 项目简介和功能特性
- [⚙️ 安装指南](install.md) - 详细安装步骤
- [🐳 Docker部署](docker-deployment.md) - Docker容器化部署
- [👤 用户手册](user-guide.md) - 完整使用指南

## 功能指南

- [🔔 推送通知设置](push-setup.md) - 配置各种通知渠道
- [🔧 关机前任务](guides/pre-shutdown-task-guide.md) - 配置关机前执行的任务
- [🌐 网络唤醒](guides/wake-on-lan-guide.md) - WOL远程唤醒配置

## 故障排查

- [❓ 常见问题](faq.md) - FAQ和故障排查指南
- [📋 支持的UPS](supported-ups.md) - 兼容的UPS型号列表
- [🔋 深度测试工作原理](troubleshooting/deep-test-actual-behavior.md) - 深度测试的技术说明
- [⚡ 大容量电池测试指南](troubleshooting/large-capacity-battery-test-guide.md) - 2000VA+大容量UPS测试

## 开发文档

- [🏗️ 系统架构](architecture.md) - 技术架构和设计
- [🔌 插件开发](development/plugin-dev.md) - 自定义通知插件开发
- [💻 本地开发(Win11)](development/win11-local-dev.md) - Windows环境开发指南

## 更新日志

- [📝 Changelog](changelog.md) - 版本更新历史

---

## 📂 文档结构

```
docs/zh/
├── README.md                     # 项目简介
├── INDEX.md                      # 本文件，文档导航
├── install.md                    # 安装指南
├── docker-deployment.md          # Docker部署
├── user-guide.md                 # 用户手册
├── faq.md                        # 常见问题
├── supported-ups.md              # 支持的UPS
├── push-setup.md                 # 推送设置
├── architecture.md               # 系统架构
├── changelog.md                  # 更新日志
├── guides/                       # 功能指南
│   ├── pre-shutdown-task-guide.md
│   └── wake-on-lan-guide.md
├── troubleshooting/              # 故障排查详细指南
│   ├── deep-test-actual-behavior.md
│   └── large-capacity-battery-test-guide.md
└── development/                  # 开发文档
    ├── plugin-dev.md
    └── win11-local-dev.md
```

## 🧪 测试环境

本项目已在以下环境验证：
- **操作系统**：Windows 11
- **部署平台**：懒猫微服（Docker环境）
- **UPS型号**：APC Back-UPS BK650M2-CH (650VA)
- **NUT版本**：2.8.3

**开发者**： (王.W)

---

> 💡 **提示**：如果您在其他环境（Linux、macOS、群晖等）或其他UPS型号上使用，欢迎反馈兼容性信息。
