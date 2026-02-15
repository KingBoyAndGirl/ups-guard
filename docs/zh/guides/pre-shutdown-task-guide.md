# 关机前置任务配置指南

## 目录
1. [什么是关机前置任务](#什么是关机前置任务)
2. [配置步骤](#配置步骤)
3. [优先级系统](#优先级系统)
4. [超时和失败策略](#超时和失败策略)
5. [设备类型配置示例](#设备类型配置示例)
6. [常见问题和解决方案](#常见问题和解决方案)
7. [最佳实践](#最佳实践)
8. [高级配置](#高级配置)

## 什么是关机前置任务

关机前置任务（Pre-Shutdown Tasks）是在宿主机关机之前，自动关闭其他设备的任务列表。

### 执行流程

```
UPS 断电 → 等待市电恢复 → 超时或电量不足 → 触发关机流程
    ↓
执行关机前置任务（按优先级依次关闭其他设备）
    ↓
所有任务完成 → 宿主机关机
```

### 为什么需要前置任务？

1. **保护数据**: 正常关闭服务器，避免数据丢失
2. **有序关机**: 按依赖关系顺序关闭，避免服务中断
3. **自动化**: 无需人工干预，自动完成整个流程
4. **Wake On LAN**: 来电后可自动唤醒所有设备

## 配置步骤

### 第一步：打开设置页面

1. 点击左侧导航栏 "⚙️ 设置"
2. 滚动到 "关机前置任务" 部分

### 第二步：选择设备类型

点击 "添加关机前置任务" 下拉菜单，选择设备类型：

- **SSH 关机**: Linux/Mac 服务器
- **Windows 远程关机**: Windows PC/服务器
- **群晖 NAS 关机**: Synology NAS
- **威联通 NAS 关机**: QNAP NAS
- **懒猫微服关机**: LazyCAT 微服务
- **自定义脚本关机**: 执行自定义脚本
- **HTTP API 关机**: 调用 HTTP 接口

### 第三步：填写配置信息

点击 "添加" 按钮后，会弹出配置对话框：

#### 基本信息
- **任务名称**: 易于识别的名称，如 "关闭 Ubuntu 服务器"
- **启用此任务**: 勾选以启用，取消勾选暂时禁用
- **优先级**: 1-99，数字越小优先级越高（详见下文）
- **超时时间**: 等待设备关闭的最长时间（秒）
- **失败策略**: 失败时继续或终止后续任务

#### 连接配置
根据设备类型不同，需要填写不同的字段：

**通用字段：**
- `host`: 设备 IP 地址或主机名
- `username`: 登录用户名
- `password`: 登录密码（如适用）
- **`mac_address`**: MAC 地址（用于 Wake On LAN）⭐ **重要**

**SSH 特有：**
- `port`: SSH 端口（默认 22）
- `auth_method`: 认证方式（password 或 key）
- `private_key`: SSH 私钥（如使用密钥认证）

**Windows 特有：**
- `shutdown_command`: 关机命令（可选，默认 `shutdown /s /t 0`）

**Synology 特有：**
- `use_https`: 是否使用 HTTPS（true/false）
- `port`: 端口（可选）

### 第四步：测试配置

⚠️ **重要步骤，不要跳过！**

1. 填写完配置后，点击 "测试配置" 按钮
2. 系统会尝试连接设备并测试关机命令（不会实际关机）
3. 确认测试成功后再点击 "保存"

**如果配置了 MAC 地址：**
- 可以点击 "🧪 测试 WOL" 测试 Wake On LAN 功能
- 确保设备能够被唤醒

### 第五步：保存配置

确认配置无误后，点击 "保存" 按钮。

### 第六步：验证任务列表

保存后，任务会出现在任务列表中，显示：
- ✅ 启用状态
- 📛 任务名称
- 🏷️ 设备类型
- 🔢 优先级
- ⚙️ 配置摘要

## 优先级系统

### 优先级规则

- **数值范围**: 1-99
- **执行顺序**: 数字越小，优先级越高，越先执行
- **并行执行**: 相同优先级的任务会并行执行

### 优先级示例

```
优先级 1: 数据库服务器 A       ← 第一个执行
优先级 1: 数据库服务器 B       ← 与 A 并行执行
优先级 2: 应用服务器 1         ← 等 1 完成后执行
优先级 2: 应用服务器 2         ← 与应用服务器 1 并行
优先级 3: 员工工作站 1-5       ← 等 2 完成后执行
优先级 3: 员工工作站 6-10      ← 与 1-5 并行
```

### 推荐优先级分配

| 设备类型 | 推荐优先级 | 说明 |
|---------|----------|------|
| 数据库服务器 | 1-5 | 最高优先级，最先关闭 |
| 核心业务服务器 | 6-10 | 次高优先级 |
| 应用服务器 | 11-20 | 中等优先级 |
| NAS 存储 | 21-25 | 需要时间刷新缓存 |
| 开发/测试服务器 | 26-30 | 较低优先级 |
| 用户工作站 | 31-40 | 最低优先级，最后关闭 |

### 优先级设计原则

1. **依赖关系**: 被依赖的服务先关闭
2. **数据重要性**: 数据越重要优先级越高
3. **关机耗时**: 耗时长的可以较早开始
4. **并行能力**: 无依赖关系的可以并行

## 超时和失败策略

### 超时时间设置

超时时间是等待设备关闭的最长时间，超过此时间视为失败。

#### 推荐超时时间

| 设备类型 | 推荐超时（秒） | 说明 |
|---------|--------------|------|
| SSH (Linux) | 60-120 | 通常很快 |
| Windows RDP | 120-180 | Windows 关机较慢 |
| Synology NAS | 180-300 | 需要刷新缓存 |
| QNAP NAS | 180-300 | 需要刷新缓存 |
| HTTP API | 30-60 | 取决于 API 响应速度 |

#### 超时处理

- 超时后，系统会记录错误日志
- 根据失败策略决定是否继续
- 不会等待超时设备，继续后续流程

### 失败策略

有两种失败策略可选：

#### 1. 继续执行后续任务（Continue）

**适用场景：**
- 非关键设备
- 可选服务
- 开发/测试环境

**行为：**
- 当前任务失败，记录错误
- 继续执行后续优先级的任务
- 宿主机仍然会关机

**示例：**
```
任务1（优先级1）: 测试服务器 - 失败 ❌
任务2（优先级2）: 数据库服务器 - 成功 ✅  ← 继续执行
任务3（优先级3）: 应用服务器 - 成功 ✅
宿主机关机 ✅
```

#### 2. 终止所有任务（Abort）

**适用场景：**
- 关键服务
- 有依赖关系的服务
- 生产环境核心系统

**行为：**
- 当前任务失败，记录错误
- 立即停止所有后续任务
- 宿主机仍然会关机（安全考虑）

**示例：**
```
任务1（优先级1）: 数据库服务器 - 失败 ❌（策略：终止）
任务2（优先级2）: 应用服务器 - 跳过 ⏭️  ← 被终止
任务3（优先级3）: 测试服务器 - 跳过 ⏭️
宿主机关机 ✅（仍然会关机）
```

### 选择建议

- **关键服务**: 使用 "终止" 策略，避免不一致状态
- **可选服务**: 使用 "继续" 策略，不影响整体流程
- **测试环境**: 使用 "继续" 策略，方便调试

## 设备类型配置示例

### SSH 关机（Linux/Mac）

```yaml
name: "Ubuntu 服务器"
type: "ssh_shutdown"
priority: 1
timeout: 120
on_failure: "continue"
config:
  host: "192.168.1.100"
  port: "22"
  username: "admin"
  auth_method: "password"
  password: "yourpassword"
  mac_address: "AA:BB:CC:DD:EE:FF"  # 用于 WOL
  broadcast_address: "255.255.255.255"  # 可选
```

**SSH 密钥认证示例：**
```yaml
config:
  host: "192.168.1.100"
  port: "22"
  username: "admin"
  auth_method: "key"
  private_key: |
    -----BEGIN OPENSSH PRIVATE KEY-----
    b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAA...
    -----END OPENSSH PRIVATE KEY-----
  mac_address: "AA:BB:CC:DD:EE:FF"
```

### Windows 远程关机

```yaml
name: "Windows 工作站"
type: "windows_shutdown"
priority: 2
timeout: 180
on_failure: "continue"
config:
  host: "192.168.1.101"
  username: "Administrator"
  password: "yourpassword"
  shutdown_command: "shutdown /s /t 60"  # 可选，60秒后关机
  mac_address: "BB:CC:DD:EE:FF:11"  # 用于 WOL
  broadcast_address: "255.255.255.255"  # 可选
```

### Synology NAS 关机

```yaml
name: "Synology NAS"
type: "synology_shutdown"
priority: 3
timeout: 300
on_failure: "abort"  # NAS 关闭失败应终止
config:
  host: "192.168.1.200"
  username: "admin"
  password: "yourpassword"
  use_https: "true"
  port: "5001"  # 可选，默认5000(HTTP)或5001(HTTPS)
  mac_address: "CC:DD:EE:FF:11:22"  # 用于 WOL
  broadcast_address: "255.255.255.255"  # 可选
```

### QNAP NAS 关机

```yaml
name: "QNAP NAS"
type: "qnap_shutdown"
priority: 3
timeout: 300
on_failure: "abort"
config:
  host: "192.168.1.201"
  username: "admin"
  password: "yourpassword"
  use_https: "false"
  mac_address: "DD:EE:FF:11:22:33"  # 用于 WOL
  broadcast_address: "255.255.255.255"  # 可选
```

### HTTP API 关机

```yaml
name: "自定义服务"
type: "http_shutdown"
priority: 4
timeout: 60
on_failure: "continue"
config:
  url: "http://192.168.1.150:8080/api/shutdown"
  method: "POST"
  headers: |
    Authorization: Bearer your-token-here
    Content-Type: application/json
  body: |
    {"action": "shutdown", "delay": 0}
  mac_address: "EE:FF:11:22:33:44"
```

### 自定义脚本关机

```yaml
name: "自定义关机脚本"
type: "custom_script"
priority: 5
timeout: 120
on_failure: "continue"
config:
  script_path: "/path/to/shutdown-script.sh"
  args: "--graceful --timeout=60"
  host: "192.168.1.150"  # 可选，目标设备地址
  mac_address: "EE:FF:11:22:33:44"  # 用于 WOL
  broadcast_address: "255.255.255.255"  # 可选
```

**环境变量说明：**

自定义脚本可以通过环境变量获取配置信息：
- `TARGET_HOST`: 目标设备地址（如果配置了 host 字段）
- `TARGET_MAC`: 目标设备 MAC 地址（如果配置了 mac_address 字段）
- `TARGET_BROADCAST`: 广播地址（如果配置了 broadcast_address 字段）

**脚本示例：**
```bash
#!/bin/bash
# shutdown-remote.sh

echo "Shutting down device at $TARGET_HOST"
echo "Device MAC: $TARGET_MAC"

# 通过 SSH 关闭设备
ssh admin@$TARGET_HOST "sudo shutdown -h now"

# 或者调用其他工具
# wakeonlan -i $TARGET_BROADCAST $TARGET_MAC
```

## 常见问题和解决方案

### 问题 1: 连接超时 (Connection Timeout)

**症状：**
- 测试配置时显示 "连接超时"
- 关机时任务失败

**可能原因：**
1. 设备不在线或网络不可达
2. 防火墙阻止连接
3. SSH/HTTP 服务未启动
4. IP 地址错误

**解决方案：**
```bash
# 1. 检查网络连接
ping 192.168.1.100

# 2. 检查端口是否开放
# Linux/Mac:
telnet 192.168.1.100 22
# Windows:
Test-NetConnection -ComputerName 192.168.1.100 -Port 22

# 3. 检查防火墙规则
# Linux:
sudo ufw status
sudo ufw allow 22/tcp

# Windows:
netsh advfirewall show allprofiles
```

### 问题 2: 认证失败 (Authentication Failed)

**症状：**
- "Authentication failed" 错误
- "Invalid credentials" 错误

**可能原因：**
1. 用户名或密码错误
2. SSH 密钥权限不正确
3. 用户没有管理员权限
4. SSH 配置禁止密码认证

**解决方案：**
```bash
# 1. 验证用户名密码
ssh username@192.168.1.100

# 2. 检查 SSH 密钥权限
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub

# 3. 检查用户权限
sudo -l  # 查看 sudo 权限

# 4. 检查 SSH 配置
cat /etc/ssh/sshd_config | grep PasswordAuthentication
```

### 问题 3: Wake On LAN 不工作

**症状：**
- 发送 WOL 后设备不启动
- "WOL sent but device didn't wake" 错误

**可能原因：**
1. MAC 地址配置错误
2. 设备未启用 WOL
3. BIOS 中 WOL 未开启
4. 网络交换机不支持魔术包
5. 跨子网 WOL 配置问题

**解决方案：**

**1. 验证 MAC 地址：**
```bash
# Linux:
ip link show
ifconfig

# Windows:
ipconfig /all

# Mac:
ifconfig
```

**2. 启用 BIOS/UEFI 中的 WOL：**
- 重启进入 BIOS
- 找到 "Wake On LAN" 或 "Resume By PCI/PCIe Device"
- 设置为 Enabled

**3. 启用操作系统中的 WOL：**

Linux:
```bash
sudo ethtool eth0
sudo ethtool -s eth0 wol g
```

Windows:
- 设备管理器 → 网络适配器 → 属性
- 电源管理 → 允许此设备唤醒计算机
- 高级 → 启用 Wake On Magic Packet

**4. 测试 WOL：**
```bash
# 从另一台机器测试
wakeonlan AA:BB:CC:DD:EE:FF

# 或使用系统内置测试
# 在 Settings 页面点击 "🧪 测试 WOL" 按钮
```

### 问题 4: 设备不关机

**症状：**
- 任务显示成功但设备仍在运行
- 关机命令执行但设备立即重启

**可能原因：**
1. 用户权限不足
2. 关机命令错误
3. 系统设置阻止关机
4. 有进程阻止关机

**解决方案：**

**Linux:**
```bash
# 确认用户有 sudo 权限
sudo shutdown -h now

# 检查是否有进程阻止关机
systemctl list-jobs
```

**Windows:**
```powershell
# 确认有管理员权限
shutdown /s /t 0 /f  # /f 强制关闭应用

# 检查是否有更新阻止
wuauclt /detectnow
```

**Synology/QNAP:**
- 确认用户属于 administrators 组
- 检查 NAS 是否有计划任务阻止关机

### 问题 5: 任务执行顺序错误

**症状：**
- 低优先级任务先执行
- 依赖服务先关闭

**可能原因：**
1. 优先级数字理解错误（越小越先执行）
2. 相同优先级并行执行未考虑到
3. 任务被禁用

**解决方案：**
1. 检查所有任务的优先级设置
2. 确保数字越小，优先级越高
3. 使用不同优先级避免意外并行
4. 在演练模式测试执行顺序

```
正确的优先级设置：
任务1: 优先级 1 ← 最先执行
任务2: 优先级 2 ← 其次执行
任务3: 优先级 3 ← 最后执行

错误的理解（❌）：
任务1: 优先级 3 ← 认为"3"是最高？错误！
任务2: 优先级 2
任务3: 优先级 1
```

## 最佳实践

### 1. 优先级规划

**按依赖关系分层：**
```
第1层 (优先级 1-5): 核心数据库
  ├─ MySQL 主库
  └─ Redis 缓存

第2层 (优先级 6-10): 应用服务
  ├─ Web 服务器 1
  ├─ Web 服务器 2
  └─ API 服务器

第3层 (优先级 11-15): 存储服务
  ├─ Synology NAS
  └─ QNAP NAS

第4层 (优先级 16-20): 开发环境
  ├─ 测试服务器
  └─ CI/CD 服务器

第5层 (优先级 21+): 用户设备
  ├─ 工作站 1-5
  └─ 工作站 6-10
```

### 2. 超时设置

**根据设备特性设置合理超时：**

| 设备类型 | 超时时间 | 理由 |
|---------|---------|------|
| 无状态服务 | 60s | 可以快速关闭 |
| 有数据库的服务 | 120s | 需要时间保存数据 |
| NAS 存储 | 300s | 需要刷新缓存，关闭RAID |
| Windows 桌面 | 180s | Windows关机较慢 |

### 3. 失败策略

**决策树：**
```
这个服务是否关键？
├─ 是 → 其他服务依赖它吗？
│   ├─ 是 → 使用 "终止" 策略
│   └─ 否 → 使用 "继续" 策略
└─ 否 → 使用 "继续" 策略
```

**示例：**
- 数据库服务器：终止（其他服务依赖它）
- 应用服务器：继续（独立服务）
- 开发服务器：继续（非关键）
- NAS：终止（数据安全）

### 4. 测试流程

**在生产环境使用前：**

1. **演练模式测试（推荐）**
   ```
   设置 → 系统配置 → 测试模式 → "演练模式（Dry-Run）"
   ```
   - 连接真实设备
   - 执行完整流程
   - 但不实际关机

2. **单个任务测试**
   - 使用 "测试配置" 按钮
   - 验证连接和认证
   - 检查错误信息

3. **WOL 功能测试**
   - 手动关闭设备
   - 使用 "测试 WOL" 按钮
   - 确认设备能够唤醒

4. **完整流程测试**
   - 选择非工作时间
   - 手动触发关机
   - 观察所有任务执行
   - 验证来电后自动唤醒

### 5. 监控和日志

**监控执行状态：**
- 查看仪表盘的设备状态
- 检查事件日志（Events 页面）
- 关注失败的任务

**日志分析：**
- 记录每次关机的执行情况
- 分析超时和失败原因
- 优化优先级和超时设置

### 6. 文档和标注

**保持配置文档：**
```yaml
# 任务名称要清晰描述用途
name: "DB-Main-MySQL"  # ✅ 好
name: "服务器1"         # ❌ 不清楚

# 添加注释说明特殊配置
# 优先级1：数据库必须最先关闭，因为应用服务器依赖它
priority: 1

# 超时300s：NAS需要时间刷新缓存
timeout: 300
```

### 7. 定期维护

**每月检查：**
- [ ] 测试所有任务连接
- [ ] 验证 WOL 功能
- [ ] 检查设备 IP 是否变更
- [ ] 更新过期的密码
- [ ] 审查优先级设置

**每季度检查：**
- [ ] 移除已淘汰设备
- [ ] 添加新设备
- [ ] 重新评估优先级
- [ ] 进行完整演练测试

## 高级配置

### 1. 并行执行优化

**场景：** 需要关闭10台工作站

**方案1：顺序执行（慢）**
```yaml
- name: "工作站1"
  priority: 1
- name: "工作站2"
  priority: 2
...
# 总时间：10 × 120s = 1200s (20分钟)
```

**方案2：并行执行（快）✅**
```yaml
- name: "工作站1-5"
  priority: 1  # 5台并行
- name: "工作站6-10"
  priority: 1  # 5台并行
# 总时间：120s (2分钟)
```

### 2. 条件性执行

**使用启用/禁用开关：**
```
场景：周末不需要关闭开发服务器

操作：
1. 平时：启用开发服务器任务
2. 周末：禁用开发服务器任务
```

### 3. MAC 地址管理

**所有设备类型现在都支持 MAC 地址：**
- SSH (Linux/Mac): ✅ 支持
- Windows: ✅ 支持
- Synology: ✅ 支持
- QNAP: ✅ 支持
- HTTP API: ✅ 支持
- 自定义脚本: ✅ 支持

**配置后的好处：**
1. 关机时自动关闭设备
2. 来电后自动唤醒设备
3. 手动唤醒功能（仪表盘）
4. 测试 WOL 功能

### 4. 跨子网 WOL

**问题：** 设备在不同子网，WOL 不工作

**解决方案：**
```yaml
config:
  mac_address: "AA:BB:CC:DD:EE:FF"
  broadcast_address: "192.168.1.255"  # 指定目标子网的广播地址
```

**不同网络的广播地址：**
- 192.168.1.0/24 → 192.168.1.255
- 192.168.2.0/24 → 192.168.2.255
- 10.0.0.0/24 → 10.0.0.255
- 255.255.255.255 → 全网广播（不推荐跨子网）

### 5. 自定义关机命令

**Linux/Mac 高级命令：**
```bash
# 延迟关机
shutdown -h +5

# 强制关机
shutdown -h now

# 通知用户
wall "System will shutdown in 5 minutes"

# 组合命令
wall "Shutting down" && sleep 60 && shutdown -h now
```

**Windows 高级命令：**
```powershell
# 延迟关机并显示消息
shutdown /s /t 300 /c "系统将在5分钟后关机"

# 强制关闭程序
shutdown /s /t 0 /f

# 重启而非关机
shutdown /r /t 60
```

### 6. 脚本钩子

**使用自定义脚本实现复杂逻辑：**
```bash
#!/bin/bash
# 关机前备份脚本

# 1. 停止服务
systemctl stop nginx
systemctl stop mysql

# 2. 执行备份
/usr/local/bin/backup.sh

# 3. 等待备份完成
while pgrep backup.sh > /dev/null; do
    sleep 5
done

# 4. 关机
shutdown -h now
```

配置：
```yaml
name: "服务器+备份"
type: "custom_script"
priority: 1
timeout: 600  # 备份需要时间
config:
  script_path: "/usr/local/bin/shutdown-with-backup.sh"
```

## 总结

配置关机前置任务的关键点：

1. ✅ **理解优先级系统**：数字越小越先执行
2. ✅ **设置合理超时**：根据设备类型调整
3. ✅ **选择正确失败策略**：关键服务用"终止"
4. ✅ **配置 MAC 地址**：启用 Wake On LAN
5. ✅ **测试再测试**：使用演练模式验证
6. ✅ **保持文档更新**：清晰的命名和注释
7. ✅ **定期维护**：检查和更新配置

遇到问题？查看本指南的"常见问题和解决方案"部分，或查看系统日志获取详细错误信息。
