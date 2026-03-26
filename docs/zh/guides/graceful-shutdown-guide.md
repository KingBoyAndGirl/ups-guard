# 🛡️ 纳管设备优雅关机指南

> **先保存数据 → 再退出应用 → 最后关机** — 完整配置教程

---

## 目录

1. [核心原理](#核心原理)
2. [预关机命令机制详解](#预关机命令机制详解)
3. [场景配置大全](#场景配置大全)
   - [懒猫微服](#场景-1纳管另一台懒猫微服)
   - [Linux 服务器（数据库+Web）](#场景-2linux-服务器跑数据库--web)
   - [Windows 工作站](#场景-3windows-工作站agent-方式)
   - [群晖 NAS（Docker 应用）](#场景-4群晖-nas-上跑了-docker-应用)
   - [开发环境多服务](#场景-5开发环境多服务编排)
4. [超时控制详解](#超时控制详解)
5. [紧急关机 vs 正常关机](#紧急关机-vs-正常关机)
6. [多设备优先级编排](#多设备优先级编排)
7. [完整实战案例](#完整实战案例)
8. [常见问题](#常见问题)
9. [检查清单](#检查清单)

---

## 核心原理

UPS Guard 的关机前置任务支持 **预关机命令**（Pre Commands），会在最终关机命令执行前 **逐行顺序执行**，每行等待上一行完成后再继续。这就是实现"保存 → 退出 → 关机"的关键。

### 执行时序图

```
SSH / Agent 连接到目标设备
        │
        ▼
┌───────────────────────────────────────┐
│  预关机命令（逐行顺序执行，每行等完成）     │
│                                       │
│  第 1 行: 保存数据（等待完成）  ✅        │
│       ↓                              │
│  第 2 行: 停止应用（等待完成）  ✅        │
│       ↓                              │
│  第 3 行: 清理资源（等待完成）  ✅        │
│       ↓                              │
│  第 4 行: 同步磁盘（等待完成）  ✅        │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  关机命令：poweroff                    │
│  （发出后不等待响应，连接会断开）         │
└───────────────────────────────────────┘
```

### 源码验证

SSH 关机插件的核心逻辑：

```python
# 逐行执行预关机命令，每条等待完成
if pre_commands_str:
    pre_commands = [cmd.strip() for cmd in pre_commands_str.split("\n") if cmd.strip()]
    for cmd in pre_commands:
        result = await conn.run(cmd, check=False, timeout=30)  # 每条超时 30 秒
        if result.exit_status != 0:
            logger.warning(f"Pre-command failed: {cmd}")

# 全部预命令执行完毕后，才执行关机
await conn.run(shutdown_command, check=False)
```

**关键特性：**

| 特性 | 说明 |
|------|------|
| ✅ 顺序执行 | 每行命令等上一行完成后再执行 |
| ✅ 单行超时 | 每条预关机命令超时 30 秒（SSH）|
| ✅ 失败容忍 | 某条命令失败不会阻塞后续命令 |
| ✅ 先于关机 | 所有预命令完成后才发送 `poweroff` |
| ⚠️ 紧急跳过 | Agent 方式在电量极低时会跳过预命令 |

---

## 预关机命令机制详解

### SSH 方式 vs Agent 方式

| 对比项 | SSH 远程关机 | Agent 客户端关机 |
|--------|-----------|---------------|
| 连接方式 | 服务端 SSH → 目标设备 | 客户端主动反连服务端 |
| 适用设备 | Linux / macOS / 懒猫微服 | Windows / Linux / macOS |
| 需要开放端口 | ✅ 需要 SSH 22 端口 | ❌ 无需开放任何端口 |
| 单行命令超时 | 30 秒（硬编码） | 无固定限制（由 Agent 控制） |
| 紧急模式跳过 | ❌ 不跳过（整体超时保障） | ✅ 自动跳过预命令 |
| 关机延迟 | 无（立即 `poweroff`） | 可配置（默认 60 秒，Windows 显示倒计时） |
| 强制关闭应用 | 需手动 `kill` | 紧急模式自动 `/f` |

### 预关机命令的编写规则

```bash
# ✅ 正确：每行一条独立命令
redis-cli BGSAVE
sleep 5
systemctl stop nginx
systemctl stop postgresql
sync

# ❌ 错误：不要用 && 连接多条命令（只算一行，30 秒超时可能不够）
redis-cli BGSAVE && sleep 5 && systemctl stop nginx && systemctl stop postgresql

# ✅ 如果命令可能耗时较长，用后台 + sleep 控制
nohup /opt/backup.sh &
sleep 20

# ✅ 忽略可能不存在的命令的错误
redis-cli BGSAVE 2>/dev/null || true
docker stop myapp 2>/dev/null || true
```

---

## 场景配置大全

### 场景 1：纳管另一台懒猫微服

**背景**：UPS Guard 运行在主机 A，需要远程关闭另一台懒猫微服 B。

> ⚠️ 旧的 `lazycat_shutdown` 插件**已废弃**（只停 lzc-docker，遗漏 docker 和 pg-docker）。
> ✅ 推荐使用 **SSH 远程关机** + 预关机命令。

#### 界面配置

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 插件类型 | SSH 远程关机 (Linux/macOS) | — |
| 任务名称 | 懒猫微服-客厅 | 描述清楚是哪台 |
| 主机地址 | 192.168.1.x | 目标懒猫微服 IP |
| SSH 端口 | 22 | — |
| 用户名 | root | 需要 root 权限停容器 |
| 认证方式 | 密码 或 私钥 | 推荐私钥更安全 |
| 优先级 | 5 | 根据实际需要 |
| 超时时间 | 180 | 停容器 + 关机需要时间 |
| 失败策略 | 继续 | 不影响其他设备 |
| MAC 地址 | AA:BB:CC:DD:EE:FF | 用于来电唤醒 |

#### 预关机命令

```bash
# ① 保存：通知核心容器做数据持久化
docker exec lzc-docker sync 2>/dev/null || true
docker exec pg-docker su - postgres -c "pg_ctl checkpoint -D /var/lib/postgresql/data" 2>/dev/null || true

# ② 退出：优雅停止懒猫的 3 个核心容器
docker stop lzc-docker pg-docker docker

# ③ 同步磁盘缓存
sync
```

#### 关机命令

```bash
poweroff
```

---

### 场景 2：Linux 服务器（跑数据库 + Web）

**背景**：一台 Ubuntu 服务器上跑了 MySQL + Redis + Nginx。

#### 预关机命令

```bash
# ① 保存数据
# MySQL：刷新所有表并锁定（确保数据写入磁盘）
mysql -u root -p'yourpass' -e "FLUSH TABLES WITH READ LOCK; SYSTEM sleep 3; UNLOCK TABLES;" 2>/dev/null || true

# Redis：触发 RDB 快照
redis-cli BGSAVE 2>/dev/null || true

# 等待 Redis 保存完成
sleep 5

# ② 退出应用
systemctl stop nginx
systemctl stop mysql
systemctl stop redis

# ③ 同步磁盘
sync
```

#### 关机命令

```bash
sudo shutdown -h now
```

---

### 场景 3：Windows 工作站（Agent 方式）

**背景**：Windows 11 工作站，用户可能正在编辑文件。

> 💡 Windows 推荐使用 **Agent 客户端关机** 插件，无需开放 SSH 端口。

#### 界面配置

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 插件类型 | Agent 客户端关机 | — |
| Agent ID | windows-desk-01 | Agent 安装时生成 |
| 关机延迟 | 120 秒 | 给用户 2 分钟手动保存 |
| 关机提示消息 | UPS 电量不足，请立即保存工作，系统将在 2 分钟后关机 | Windows 系统弹窗提示 |
| 超时时间 | 300 | 预命令 + 120 秒延迟 |

#### 预关机命令

```powershell
# ① 保存：优雅关闭 Office（触发自动保存）
powershell -Command "(Get-Process WINWORD -ErrorAction SilentlyContinue) | ForEach-Object { $_.CloseMainWindow() }"
powershell -Command "(Get-Process EXCEL -ErrorAction SilentlyContinue) | ForEach-Object { $_.CloseMainWindow() }"
powershell -Command "(Get-Process POWERPNT -ErrorAction SilentlyContinue) | ForEach-Object { $_.CloseMainWindow() }"

# ② 等待 Office 保存（给 15 秒）
powershell -Command "Start-Sleep -Seconds 15"

# ③ 退出：停止数据库等服务
net stop "MySQL80"
net stop "W3SVC"

# ④ 刷新磁盘缓存
powershell -Command "Write-VolumeCache C"
```

#### 执行流程

```
预关机命令执行（约 30 秒）
    ↓
关机命令下发，Windows 开始 120 秒倒计时
    ↓
屏幕弹窗：「UPS 电量不足，请立即保存工作，系统将在 2 分钟后关机」
    ↓
120 秒后执行 shutdown /s
```

> ⚠️ **超时设置**：`任务超时` ≥ 预关机命令耗时 + 关机延迟秒数。此例中：30 + 120 = 150 秒，设置 300 秒留出余量。

---

### 场景 4：群晖 NAS 上跑了 Docker 应用

**背景**：群晖 NAS 上用 Docker 跑了 Jellyfin 和 Home Assistant，需要先停容器再关机。

> 群晖的 `synology_shutdown` 插件通过 API 关机，无法执行预关机命令。如果需要先停容器，改用 **SSH 远程关机**。

#### 预关机命令

```bash
# ① 保存：通知 Home Assistant 保存状态
docker exec homeassistant python -c "import requests; requests.post('http://localhost:8123/api/services/homeassistant/stop')" 2>/dev/null || true

# ② 退出：优雅停止 Docker 容器
docker stop jellyfin homeassistant
sleep 5

# ③ 停止 Docker 服务（可选，群晖会自动处理）
# synoservicecfg --stop Docker 2>/dev/null || true

# ④ 同步
sync
```

#### 关机命令

```bash
sudo poweroff
```

---

### 场景 5：开发环境多服务编排

**背景**：一台 Linux 服务器跑了 Docker Compose 编排的微服务（API + 前端 + 数据库 + 缓存 + 消息队列）。

#### 预关机命令

```bash
# ① 保存：各服务数据持久化
docker exec redis redis-cli BGSAVE 2>/dev/null || true
docker exec postgres pg_ctl checkpoint -D /var/lib/postgresql/data 2>/dev/null || true
sleep 5

# ② 退出：按依赖关系反向停止（先停前端，后停数据库）
cd /opt/myproject && docker compose stop frontend api worker
sleep 3
cd /opt/myproject && docker compose stop redis rabbitmq postgres

# ③ 确保所有容器停止
docker stop $(docker ps -q) 2>/dev/null || true

# ④ 同步磁盘
sync
```

---

## 超时控制详解

### 三层超时体系

```
┌──────────────────────────────────────────────────┐
│ 第 1 层：单条预关机命令超时                          │
│ SSH 方式：每条 30 秒                               │
│ Agent 方式：无固定限制                              │
├──────────────────────────────────────────────────┤
│ 第 2 层：设备任务超时                               │
│ 在设置页面为每个设备配置                             │
│ 默认 120 秒，可设置 30-600 秒                       │
│ 包含：所有预命令 + 关机命令 + 关机延迟               │
├──────────────────────────────────────────────────┤
│ 第 3 层：全局关机前置任务超时                         │
│ 由 HookExecutor 的 default_timeout 控制            │
│ 默认 120 秒（可被单设备超时覆盖）                    │
└──────────────────────────────────────────────────┘
```

### 超时计算公式

```
设备任务超时 ≥ (预关机命令行数 × 30s) + 关机延迟 + 安全余量
```

| 场景 | 预命令行数 | 关机延迟 | 推荐超时 |
|------|:---------:|:-------:|:-------:|
| 简单 Linux（无预命令） | 0 | 0 | 60s |
| Linux + 停容器 | 5 行 | 0 | 180s |
| 懒猫微服 | 4 行 | 0 | 180s |
| Windows Agent | 4 行 | 120s | 300s |
| 大型数据库备份 | 3 行 + sleep | 0 | 600s |

### 单条命令超时应对策略

如果某个操作需要超过 30 秒（SSH 方式的单行硬编码超时）：

```bash
# ❌ 错误：这条命令如果超过 30 秒会被 kill
/opt/heavy-backup.sh

# ✅ 正确：后台执行 + sleep 等待
nohup /opt/heavy-backup.sh &
sleep 60

# ✅ 正确：用 timeout 命令控制
timeout 25 /opt/quick-save.sh || true
```

---

## 紧急关机 vs 正常关机

系统会根据 UPS 剩余电量和续航时间自动判断关机模式：

### 对比表

| 对比项 | 正常关机 | 紧急关机 |
|--------|:-------:|:-------:|
| 触发条件 | 断电等待超时 / 电量 < 阈值 | 续航 < 3 分钟 |
| 预关机命令 | ✅ 完整执行 | ⚠️ Agent 跳过 / SSH 受整体超时限制 |
| 关机延迟 | 使用配置值（如 120s） | Agent 缩短到 10s |
| 强制关闭应用 | ❌ 优雅关闭 | ✅ Agent 加 `/f` 强制 |
| 通知用户 | ✅ 正常消息 | ✅ 紧急消息 |

### Agent 紧急关机行为

```python
# 紧急时的关机参数
params = {
    "delay": 10,        # 缩短延迟到 10 秒（正常 60 秒）
    "force": True,      # Windows 加 /f 强制关闭应用
    "message": "..."    # 紧急关机提示
}

# 跳过预关机命令
if self.urgent and pre_commands_str:
    logger.warning("URGENT shutdown — skipping pre_commands")
```

### 最佳实践

为了兼顾正常和紧急场景：

1. **预关机命令尽量精简**：只做必要的保存操作，不要包含耗时很长的任务
2. **超时设置合理**：不要设太大，紧急时系统没那么多时间等
3. **关键数据用服务自身保护**：如 MySQL 的 `innodb_flush_log_at_trx_commit=1`，Redis 的 AOF 持久化

---

## 多设备优先级编排

### 执行机制

```python
# 按优先级分组 → 同优先级并行 → 不同优先级串行
priority_groups = defaultdict(list)
for hook in enabled_hooks:
    priority_groups[hook["priority"]].append(hook)

for priority in sorted(priority_groups.keys()):
    # 同优先级并行执行（asyncio.gather）
    tasks = [execute(hook) for hook in priority_groups[priority]]
    await asyncio.gather(*tasks)
```

### 编排原则：先保存后关机

```
优先级 1（最先执行）: 触发所有设备的数据保存
  ├─ 数据库服务器：保存操作放在预关机命令里
  └─ NAS：数据持久化

优先级 5（中间执行）: 关闭业务应用
  ├─ Web 服务器 A  ← 并行
  └─ Web 服务器 B  ← 并行

优先级 10（较晚执行）: 关闭基础设施
  ├─ 懒猫微服 B    ← 预命令先停容器
  └─ 群晖 NAS      ← 并行

优先级 20（最后执行）: 关闭非关键设备
  ├─ Windows 工作站 1  ← 并行
  ├─ Windows 工作站 2  ← 并行
  └─ Windows 工作站 3  ← 并行

所有设备完成后 → 关闭宿主机 A（UPS Guard 所在主机）
```

### 跨设备数据依赖

如果设备 B 的应用依赖设备 A 的数据库：

```
优先级 1: 设备 B（先关闭应用，因为它依赖 A 的数据库）
    预命令：停止 Web 应用
    关机：poweroff

优先级 2: 设备 A（后关闭数据库）
    预命令：MySQL checkpoint → 停止 MySQL
    关机：poweroff
```

> ⚠️ 注意：先关**依赖方**（Web 应用），再关**被依赖方**（数据库）。

---

## 完整实战案例

### 家庭 + 小型办公环境

```
宿主机 A：懒猫微服（运行 UPS Guard + 日常应用）
  ├─ UPS: 瓦力方程 W120（12V DC UPS，给路由器/光猫供电）
  │
  └─ 纳管设备：
      ├─ 懒猫微服 B（客厅 NAS，跑 Jellyfin + Photo）
      ├─ 群晖 DS923+（存储重要数据）
      ├─ Windows 工作站（日常办公）
      └─ Linux 服务器（开发用）
```

#### 配置方案

| 设备 | 插件类型 | 优先级 | 超时 | 失败策略 | 预关机命令 |
|------|---------|:------:|:----:|:-------:|---------|
| Linux 服务器 | SSH 关机 | 1 | 180s | 继续 | 保存 DB → 停服务 → sync |
| 群晖 DS923+ | SSH 关机 | 3 | 300s | 终止 | 停 Docker → sync |
| 懒猫微服 B | SSH 关机 | 5 | 180s | 继续 | 停 3 容器 → sync |
| Windows 工作站 | Agent 关机 | 10 | 300s | 继续 | 关 Office → 停服务 |

#### 执行时间轴

```
00:00  UPS 断电检测
         ↓
05:00  等待 5 分钟，市电未恢复
         ↓
05:01  开始执行关机前置任务
         ↓
05:01  [优先级 1] Linux 服务器
         ├─ 预命令: redis-cli BGSAVE (3s)
         ├─ 预命令: sleep 5 (5s)
         ├─ 预命令: systemctl stop nginx mysql redis (10s)
         ├─ 预命令: sync (1s)
         └─ 关机命令: poweroff ✅
         ↓
05:21  [优先级 3] 群晖 NAS
         ├─ 预命令: docker stop jellyfin homeassistant (15s)
         ├─ 预命令: sync (1s)
         └─ 关机命令: poweroff ✅
         ↓
05:40  [优先级 5] 懒猫微服 B
         ├─ 预命令: docker stop lzc-docker pg-docker docker (20s)
         ├─ 预命令: sync (1s)
         └─ 关机命令: poweroff ✅
         ↓
06:02  [优先级 10] Windows 工作站
         ├─ 预命令: 关闭 Office (5s)
         ├─ 预命令: sleep 15 (15s)
         ├─ 预命令: 停数据库服务 (5s)
         └─ 关机延迟 120 秒倒计时...
         ↓
08:10  宿主机 A 执行关机 ✅

总计用时：约 3 分钟（+ Windows 延迟 2 分钟）
```

---

## 常见问题

### Q1：预关机命令执行失败会怎样？

**不会阻塞关机流程。** 某条预命令失败后会打印警告日志，继续执行下一条命令，最终仍会执行关机命令。

```
预命令 1: redis-cli BGSAVE     → ✅ 成功
预命令 2: systemctl stop nginx → ✅ 成功  
预命令 3: 某个不存在的命令       → ⚠️ 失败（日志记录，继续）
预命令 4: sync                 → ✅ 成功
关机命令: poweroff             → ✅ 执行
```

### Q2：预命令超过 30 秒怎么办？

SSH 方式每条命令硬编码 30 秒超时。对于耗时操作：

```bash
# 方案一：后台执行 + sleep
nohup /opt/long-task.sh &
sleep 25   # 在 30 秒超时内

# 方案二：提前在系统层面保障
# 如设置 MySQL 事务自动刷盘，不依赖关机时的手动保存
```

### Q3：能否区分"保存失败就不关机"的场景？

当前系统中，单条预命令失败不会阻止关机。如果你需要"保存失败则终止"的行为：

```bash
# 把保存和验证写成一条命令，失败时主动 exit 阻塞后续
redis-cli BGSAVE && redis-cli LASTSAVE || exit 1
```

但即使预命令全部失败，**关机命令仍会执行**（这是安全设计：UPS 电量有限，必须关机）。

### Q4：多台设备同时关机，SSH 连接会不会来不及？

同优先级的设备 **并行执行**（`asyncio.gather`），每个设备独立 SSH 连接，互不影响。10 台工作站设为同一优先级可以同时关机，总时间 = 最慢的那台。

### Q5：市电恢复了，正在执行的预关机命令会停吗？

**会。** 系统在每个优先级组执行前会检查取消标志。如果在执行过程中市电恢复且用户点击了"取消关机"，后续优先级的设备会被跳过。但已经 SSH 连上并正在执行的命令不会被中断（需要命令自然结束或超时）。

---

## 检查清单

部署前逐项确认：

### 每台纳管设备

- [ ] SSH / Agent 连接测试通过
- [ ] 预关机命令在目标设备上手动测试过
- [ ] 关机命令在目标设备上手动测试过（注意：会真的关机！）
- [ ] 超时设置 ≥ 预命令总耗时 + 关机延迟
- [ ] MAC 地址填写正确（用于来电唤醒）
- [ ] 优先级设置合理（依赖方先关）

### 整体验证

- [ ] 使用 **演练模式（Dry-Run）** 测试完整流程
- [ ] 观察仪表盘的实时关机进度（每个设备状态：⏳→🔄→✅/❌）
- [ ] 检查事件日志确认所有设备成功关闭
- [ ] 测试 WOL 唤醒所有设备
- [ ] 切换回 **生产模式** 后进行一次真实断电测试（选在非工作时间）

### 定期维护（每月）

- [ ] 测试所有设备连接
- [ ] 确认 IP 地址未变更
- [ ] 更新过期密码/密钥
- [ ] 检查预关机命令是否仍然适用（应用变更后可能需要更新）
- [ ] 验证 WOL 功能