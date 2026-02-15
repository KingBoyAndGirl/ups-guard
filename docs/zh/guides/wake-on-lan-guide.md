# Wake On LAN (WOL) 配置指南

## 概述

LazyCAT UPS Guard 支持通过 Wake On LAN (WOL) 协议来唤醒已关闭的纳管设备。本指南将详细说明如何配置支持 WOL 的设备。

## 前置条件

### 硬件要求
1. **网卡支持**: 设备网卡必须支持 Wake On LAN 功能
2. **主板支持**: BIOS/UEFI 需要启用 WOL 相关选项
3. **电源连接**: 设备需要保持电源连接（关机状态但插着电源）

### 软件要求
1. 设备需要配置静态 IP 或 DHCP 保留地址
2. 知道设备的 MAC 地址

## 如何获取 MAC 地址

### Windows
```cmd
ipconfig /all
```
查找 "物理地址" 或 "Physical Address"

### Linux/macOS
```bash
ip link show
# 或
ifconfig
```
查找类似 `AA:BB:CC:DD:EE:FF` 格式的地址

## 配置步骤

### 步骤 1: 启用设备的 WOL 功能

#### BIOS/UEFI 设置
1. 重启设备，进入 BIOS/UEFI
2. 找到电源管理相关选项
3. 启用以下选项（名称可能不同）:
   - Wake On LAN
   - Wake On PCI-E
   - Power On by PCI-E
   - Resume by PCI-E Device

#### 操作系统设置

**Windows:**
1. 设备管理器 → 网络适配器
2. 右键网卡 → 属性
3. 电源管理标签页:
   - ✅ 允许此设备唤醒计算机
   - ✅ 只允许魔术数据包唤醒计算机
4. 高级标签页:
   - 启用 "Wake on Magic Packet"

**Linux:**
```bash
# 检查 WOL 状态
sudo ethtool eth0 | grep Wake-on

# 启用 WOL
sudo ethtool -s eth0 wol g

# 永久启用（添加到 /etc/network/interfaces 或 NetworkManager）
```

### 步骤 2: 在 LazyCAT UPS Guard 中配置设备

#### 支持 WOL 的设备类型

LazyCAT UPS Guard 所有设备类型都支持 Wake On LAN 功能，只需配置 MAC 地址即可：

- ✅ **SSH 关机** (Linux/Unix 服务器)
- ✅ **Windows 远程关机** (Windows 服务器)
- ✅ **群晖 NAS 关机** (Synology NAS)
- ✅ **QNAP NAS 关机** (QNAP NAS)
- ✅ **懒猫微服关机** (LazyCAT 微服务)
- ✅ **自定义脚本** (自定义设备)
- ✅ **HTTP API** (通过 API 控制的设备)

#### 方法 1: 通过设置页面添加

1. 打开 **设置** 页面
2. 在 **纳管设备配置** 部分点击 **➕ 添加设备**
3. 选择设备类型并填写信息

##### 示例 1: Linux 服务器 (SSH 关机)

```
设备名称: Linux 服务器
设备类型: SSH 关机
优先级: 1

配置参数:
- 主机地址: 192.168.1.100
- MAC 地址: AA:BB:CC:DD:EE:FF  ← 必填！
- 广播地址: 192.168.1.255 (可选)
- 用户名: admin
- 认证方式: 密码/密钥
```

##### 示例 2: Windows 服务器

```
设备名称: Windows 服务器
设备类型: Windows 远程关机 (SSH)
优先级: 2

配置参数:
- 主机地址: 192.168.1.101
- SSH 端口: 22
- 用户名: Administrator
- 密码: ********
- MAC 地址: BB:CC:DD:EE:FF:11  ← 必填！
- 广播地址: 255.255.255.255 (可选)
- 关机命令: shutdown /s /t 60 /c "UPS power lost"
```

**注意**: Windows 需要先安装 OpenSSH Server

##### 示例 3: 群晖 NAS

```
设备名称: Synology NAS
设备类型: 群晖 NAS 关机
优先级: 3

配置参数:
- NAS 地址: 192.168.1.200
- 端口: 5001
- 用户名: admin
- 密码: ********
- MAC 地址: CC:DD:EE:FF:11:22  ← 必填！
- 广播地址: 255.255.255.255 (可选)
- 使用 HTTPS: 是
```

4. 点击 **保存**

#### 方法 2: 通过配置文件

编辑 `config/config.yaml`:

```yaml
pre_shutdown_hooks:
  # Linux 服务器
  - name: "Linux 服务器"
    type: "ssh_shutdown"
    priority: 1
    config:
      host: "192.168.1.100"
      port: 22
      username: "admin"
      auth_method: "password"
      password: "your_password"
      mac_address: "AA:BB:CC:DD:EE:FF"  # WOL 必需
      broadcast_address: "192.168.1.255"  # 可选
      
  # Windows 服务器
  - name: "Windows 服务器"
    type: "windows_shutdown"
    priority: 2
    config:
      host: "192.168.1.101"
      port: 22
      username: "Administrator"
      password: "windows_password"
      mac_address: "BB:CC:DD:EE:FF:11"  # WOL 必需
      broadcast_address: "255.255.255.255"  # 可选
      shutdown_command: "shutdown /s /t 60 /c \"UPS power lost\""
      
  # 群晖 NAS
  - name: "Synology NAS"
    type: "synology_shutdown"
    priority: 3
    config:
      host: "192.168.1.200"
      port: 5001
      username: "admin"
      password: "nas_password"
      use_https: "true"
      mac_address: "CC:DD:EE:FF:11:22"  # WOL 必需
      broadcast_address: "192.168.1.255"  # 可选
```

### 步骤 3: 测试 WOL 功能

#### 在设置页面测试
1. 设备配置中找到 **🧪 测试 WOL** 按钮
2. 点击测试，查看是否成功发送魔术包

#### 在首页测试
1. 关闭目标设备
2. 等待设备显示为离线状态（灰色）
3. 点击设备卡片上的 **⏻ 开机** 按钮
4. 观察设备是否成功启动

## 首页电源管理功能

### 当前支持的功能

#### 1. 单设备操作

**关机 (🔌 关机)**
- 位置: 设备卡片右上角
- 条件: 设备在线时显示
- 功能: 关闭单个设备

**开机 (⏻ 开机)**
- 位置: 设备卡片右上角
- 条件: 设备离线且配置了 MAC 地址
- 功能: 通过 WOL 唤醒设备

**测试 WOL (🧪 测试WOL)**
- 位置: 设备卡片操作栏
- 条件: 设备在线且有 MAC 地址
- 功能: 测试 WOL 功能（无需关机）

#### 2. 批量操作

**全部关机 (🔌 立即关机)**
- 位置: 首页顶部
- 条件: UPS 电池供电 + 有设备在线
- 功能: 关闭所有在线设备

**全部开机 (⏻ 全部开机)**
- 位置: 首页顶部
- 条件: 所有设备离线
- 功能: 唤醒所有配置了 MAC 地址的设备

### 暂不支持的功能

以下功能需要额外开发:

#### ❌ 休眠 (Hibernate)
- **需求**: 将内存内容保存到硬盘，完全断电
- **实现难度**: 需要各操作系统特定命令
- **Windows**: `shutdown /h`
- **Linux**: `systemctl hibernate`
- **macOS**: `pmset sleepnow` (实际是睡眠)

#### ❌ 睡眠 (Sleep)
- **需求**: 保持内存供电，低功耗模式
- **实现难度**: 需要各操作系统特定命令
- **Windows**: `rundll32.exe powrprof.dll,SetSuspendState 0,1,0`
- **Linux**: `systemctl suspend`
- **macOS**: `pmset sleepnow`

**注意**: 
- 休眠和睡眠后可能无法通过 WOL 唤醒（取决于硬件和配置）
- 建议使用完全关机 + WOL 的方式

## 常见问题

### Q1: WOL 不工作？

**检查清单:**
1. ✅ BIOS 中启用了 WOL
2. ✅ 操作系统中启用了 WOL
3. ✅ MAC 地址配置正确
4. ✅ 设备在同一子网或正确配置了广播地址
5. ✅ 防火墙允许 UDP 9 端口（WOL 魔术包端口）
6. ✅ 设备电源已连接

### Q2: 如何知道 WOL 包发送成功？

查看以下地方:
1. **控制台日志**: 浏览器 F12 → Console
2. **通知**: 成功发送会显示 "✅ 成功发送 WOL 到 X 台设备"
3. **事件日志**: 设置页面 → 日志查看器

### Q3: 广播地址如何填写？

**同一子网**: 使用子网广播地址
- 例如: 192.168.1.0/24 → 192.168.1.255

**不同子网**: 可能需要:
1. 路由器支持 WOL 转发
2. 使用定向广播
3. 或保持默认 255.255.255.255

### Q4: 支持跨子网 WOL 吗？

**部分支持**, 需要:
1. 路由器/交换机支持定向广播
2. 正确配置广播地址
3. 网络设备允许 WOL 包转发

### Q5: 可以通过互联网唤醒设备吗？

**不直接支持**, 但可以:
1. 使用 VPN 连接到内网
2. 在路由器上配置 WOL 转发（端口转发）
3. 使用专门的 WOL 网关设备

## 最佳实践

### 1. 设备命名
使用清晰的名称，便于识别:
- ✅ "开发服务器-Ubuntu"
- ✅ "文件服务器-Synology"
- ❌ "设备1"

### 2. 优先级设置
按照重要性和依赖关系设置优先级:
- 优先级 1: 最先关闭（如普通服务器）
- 优先级 2-5: 依次关闭
- 优先级 10: 最后关闭（如 NAS、数据库服务器）

### 3. 测试流程
新设备配置后建议测试:
1. **关机测试**: 设备能否正常关闭
2. **WOL 测试**: 使用 "🧪 测试WOL" 按钮
3. **完整流程**: 关机 → 等待 → 开机

### 4. MAC 地址管理
- 使用 DHCP 保留地址，避免 IP 变化
- 记录每个设备的 MAC 地址
- 定期检查设备配置的准确性

## 技术细节

### WOL 工作原理
1. UPS Guard 发送魔术包 (Magic Packet)
2. 魔术包格式: 6 字节 0xFF + 16 次目标 MAC 地址
3. 使用 UDP 协议，端口 9 或 7
4. 广播到局域网
5. 目标设备网卡接收到魔术包后唤醒主机

### 代码实现位置
- **后端 WOL 发送**: `backend/src/api/wol.py`
- **前端 WOL 按钮**: `frontend/src/components/DeviceCard.vue`
- **批量唤醒**: `frontend/src/views/Dashboard.vue`

## 进阶配置

### 自定义广播地址
某些网络环境需要指定特定的广播地址:

```yaml
config:
  mac_address: "AA:BB:CC:DD:EE:FF"
  broadcast_address: "192.168.1.255"  # 子网广播
  # 或
  broadcast_address: "192.168.255.255"  # 大段广播
```

### 多网卡设备
如果设备有多个网卡，配置主网卡的 MAC 地址（通常是启用了 WOL 的那个）。

### 虚拟机 WOL
虚拟机通常不支持 WOL，但可以:
1. 唤醒物理主机
2. 通过脚本自动启动虚拟机

## 相关文档

- [设备配置指南](./device-configuration.md)
- [关机前置任务](./shutdown-hooks.md)
- [常见问题](./faq.md)

## 反馈与支持

如有问题或建议，请:
1. 查看项目 Issues
2. 提交新的 Issue
3. 参与项目讨论

---

**最后更新**: 2026-02-13
**版本**: 1.0
