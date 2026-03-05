# Changelog

All notable changes to UPS Guard (UPS Guard) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - 新增功能

#### UPS 参数配置 🔧
- **可写参数管理**: 支持直接修改 UPS 硬件参数
  - 电压保护阈值：高压切换点（220-300V）、低压切换点（100-200V）
  - 输入灵敏度：低/中/高三个等级
  - 关机延迟：0-600 秒可配置
  - 基于 NUT SET VAR 和 LIST RW 协议实现
  
- **Dashboard 内联编辑**: 在仪表盘卡片中快速修改参数
  - 电压质量卡片：点击安全区间值可编辑
  - 保护状态总览卡片：点击灵敏度可切换
  - 关机时间线卡片：显示并可编辑关机延迟
  
- **Settings 高级配置面板**: 统一的参数配置界面
  - 四个配置区域：电压保护、灵敏度、关机延迟、所有可写变量列表
  - 当前值与新值对比显示
  - 所有修改前需二次确认
  
- **安全机制**:
  - 白名单验证：只允许修改安全参数
  - 范围验证：数值必须在合理区间内
  - 智能排序：同时设置多个电压阈值时自动优化顺序避免冲突
  - 事件记录：所有修改记录到事件历史（类型：参数修改 🔧）
  
- **API 端点**:
  - `GET /api/ups/writable-vars`: 列出所有可写变量
  - `POST /api/ups/set-var`: 设置参数（带白名单和验证）

## [1.0.0] - 2026-02-15

### 🎉 正式版发布

这是 UPS Guard 的第一个正式版本，标志着项目从测试版本进入生产就绪状态。

### Added - 新增功能

#### 安全加固 🔒
- **API Token 认证**: 实现 Bearer Token 认证机制，保护所有 API 端点
  - 支持环境变量 `API_TOKEN` 自定义认证密钥
  - 未设置时自动生成随机 Token 并在日志中显示
  - `/health` 和 `/ws` 端点不需要认证
  - 所有 `/api/*` 路由需要认证
- **敏感信息加密**: 使用 Fernet 对称加密保护敏感数据
  - 支持环境变量 `ENCRYPTION_KEY` 自定义加密密钥
  - 自动生成并持久化加密密钥到 `/data/.encryption_key`
  - API 返回时敏感字段自动脱敏
- **CORS 收紧**: 仅允许同域和配置的子域名访问
  - 支持环境变量 `ALLOWED_ORIGINS` 自定义允许的来源
  - 默认仅允许 `ups-guard` 子域名和本地开发环境

#### 性能优化 📈
- **SQLite 优化**:
  - 启用 WAL (Write-Ahead Logging) 模式，提高并发性能
  - 设置 `PRAGMA synchronous=NORMAL` 减少 fsync 开销
  - 添加数据库完整性检查
- **批量事务支持**: 批量写入操作使用事务，提高数据一致性

#### 错误恢复与健壮性 🛡️
- **gRPC 连接增强**:
  - 添加连接超时机制（默认 5 秒）
  - 实现重试逻辑（最多 3 次，指数退避）
  - 关机前进行 socket 可达性检查
  - 详细的错误日志（区分连接失败 vs 调用失败）
- **NUT 连接恢复**:
  - 自动重连机制（指数退避，最大 60 秒间隔）
  - 连接状态纳入健康检查 API
  - 记录重连尝试次数和最后错误

### Changed - 功能变更

- 更新依赖包到最新安全版本：
  - `cryptography>=46.0.5` (修复多个安全漏洞)
- 健康检查端点返回更详细的信息（包含 NUT 连接状态）

### Security - 安全修复

- 修复 CORS 配置允许所有来源的安全隐患
- 添加 API 认证，防止未授权访问
- 使用加密存储敏感配置信息
- 更新 cryptography 库至 46.0.5+ 修复已知安全漏洞

---

## 版本说明

- **[1.0.0]**: 首个正式版本，生产就绪，功能完整

## 支持

如有问题或建议，请：
- 提交 [Issue](https://github.com/KingBoyAndGirl/ups-guard/issues)
- 参与 [Discussions](https://github.com/KingBoyAndGirl/ups-guard/discussions)

---

**Legend**
- 🎉 Major release
- ✨ New feature
- 🔒 Security
- 🐛 Bug fix
- 📈 Performance
- 🛡️ Robustness
- 🌍 i18n
- 🔧 Configuration
