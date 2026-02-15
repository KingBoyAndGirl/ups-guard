# Win11 本地开发测试指南

本文档详细说明如何在 **Windows 11** 本地环境进行 UPS Guard 开发测试，包括 UPS 设备连接、调试和安全关机验证。

---

## ⚠️ 重要说明：Windows 开发环境 vs Linux 生产环境

> **结论：USB UPS 透传问题仅存在于 Windows 开发环境，在原生 Linux 生产环境中完全正常！**

| 环境 | USB 访问方式 | 是否正常 | 说明 |
|------|-------------|---------|------|
| **群晖/QNAP/Linux 服务器** | 直接挂载 `/dev/bus/usb` | ✅ **正常** | 无虚拟化层，Docker 直接访问硬件 |
| **懒猫微服/Linux NAS** | 直接挂载 `/dev/bus/usb` | ✅ **正常** | 原生 Linux，完美支持 |
| **Windows + Docker Desktop** | usbipd + WSL2 虚拟化 | ❌ **有问题** | USB/IP 协议无法正确透传 HID 描述符 |

**如果你的生产环境是 Linux 系统（NAS、服务器等），请放心部署，USB UPS 可以正常工作！**

本文档描述的 USB 透传问题和 Mock 模式仅针对 **Windows 本地开发调试** 场景。

---

## 📋 目录

1. [环境准备](#1-环境准备)
2. [查看 UPS 设备名称](#2-查看-ups-设备名称)
3. [配置环境变量](#3-配置环境变量)
4. [启动服务](#4-启动服务)
5. [验证 UPS 连接](#5-验证-ups-连接)
6. [安全关机测试流程](#6-安全关机测试流程)
7. [开发调试技巧](#7-开发调试技巧)
8. [常见问题](#8-常见问题)

---

## 1. 环境准备

### 1.1 系统要求

- Windows 11（支持 WSL2）
- Docker Desktop for Windows（已安装并运行）
- UPS 设备通过 USB 连接到 Win11 电脑

### 1.2 确认 Docker 已安装

打开 PowerShell，运行：

```powershell
docker --version
docker-compose --version
```

如果显示版本号，说明 Docker 已安装成功。

### 1.3 确保 Docker Desktop 设置正确

1. 打开 Docker Desktop
2. 进入 **Settings** → **General**
3. 确保以下选项已启用：
   - ✅ Use the WSL 2 based engine
   - ✅ Start Docker Desktop when you log in
4. 进入 **Settings** → **Resources** → **WSL Integration**
5. 确保 WSL 集成已启用

### 1.4 ⚠️ 重要：配置 USB 设备透传（必读）

> **核心问题**：Windows 上的 Docker Desktop 无法直接访问 USB 设备，需要通过 `usbipd-win` 将 USB 设备透传到 WSL2。

**解决方案**：使用 `usbipd-win` + WSL2 Ubuntu + Docker Desktop WSL 集成。

> ✅ **已验证可行**：通过正确配置 usbipd + Docker Desktop WSL 集成，USB UPS 可以在 Windows 开发环境中正常工作！

#### 步骤 1：安装 WSL2 Ubuntu 发行版

```powershell
# 以管理员身份运行 PowerShell
wsl --install Ubuntu-24.04

# 安装完成后，设置 Ubuntu 的用户名和密码
# 然后检查安装结果
wsl -l -v
# 应该看到：
#   NAME                   STATE           VERSION
# * Ubuntu-24.04           Running         2
#   docker-desktop         Running         2
```

#### 步骤 2：安装 usbipd-win

```powershell
# 使用 winget 安装（推荐）
winget install usbipd

# 或者从 GitHub 下载安装：
# https://github.com/dorssel/usbipd-win/releases
```

#### 步骤 3：在 Ubuntu 中安装 USB/IP 客户端

```powershell
# 进入 Ubuntu
wsl -d Ubuntu-24.04

# 在 Ubuntu 中运行：
sudo apt update
sudo apt install linux-tools-generic hwdata
sudo update-alternatives --install /usr/local/bin/usbip usbip /usr/lib/linux-tools/*-generic/usbip 20

# 退出 Ubuntu
exit
```

#### 步骤 4：配置 Docker Desktop 使用 Ubuntu（关键步骤！）

> ⚠️ **这是让 USB 透传正常工作的关键！**

1. 打开 **Docker Desktop** → **Settings** → **Resources** → **WSL Integration**
2. 确保 **Enable integration with my default WSL distro** 已启用
3. 启用 **Ubuntu-24.04** 的集成开关
4. 点击 **Apply & Restart**
5. 等待 Docker Desktop 完全重启

验证配置：
```powershell
# 在 PowerShell 中运行 docker 命令应该正常工作
docker ps

# 同时在 Ubuntu 中也应该能访问 Docker
wsl -d Ubuntu-24.04 -e docker ps
```

#### 步骤 5：启动 Ubuntu 并保持运行

> ⚠️ **关键步骤**：Ubuntu 必须保持运行状态，否则 USB 设备无法附加！

```powershell
# 方法 1：在新窗口中启动 Ubuntu（推荐）
Start-Process -FilePath "wsl" -ArgumentList "-d", "Ubuntu-24.04"

# 方法 2：或者直接进入 Ubuntu
wsl -d Ubuntu-24.04

# 检查 Ubuntu 是否运行
wsl -l -v
# 确保 Ubuntu-24.04 的 STATE 为 "Running"
```

#### 步骤 6：绑定并附加 UPS 设备

```powershell
# 以管理员身份运行 PowerShell

# 1. 列出所有 USB 设备
usbipd list
# 找到 UPS 设备的 BUSID，例如：3-2
# 示例输出：
# BUSID  VID:PID    DEVICE                                          STATE
# 3-2    051d:0002  American Power Conversion USB UPS                Not shared

# 2. 绑定设备（首次需要，如有 USB 过滤器冲突使用 --force）
usbipd bind --busid 3-2 --force

# 3. 附加到 WSL 并启用自动重连（推荐！）
usbipd attach --wsl=Ubuntu-24.04 --busid 3-2 --auto-attach

# 4. 验证附加成功
usbipd list
# STATE 应该显示 "Attached"
# 示例输出：
# 3-2    051d:0002  American Power Conversion USB UPS                Attached
```

> 💡 **提示**：使用 `--auto-attach` 选项后，USB 设备在重新连接时会自动附加到 WSL，非常方便！

#### 步骤 7：验证 Ubuntu 能看到 USB 设备

```powershell
# 在 Ubuntu 中检查 USB 设备
wsl -d Ubuntu-24.04 -e lsusb

# 应该看到类似：
# Bus 001 Device 002: ID 051d:0002 American Power Conversion Uninterruptible Power Supply

# 如果看不到设备，检查 usbipd 状态并重新附加
```

#### 步骤 8：启动 Docker 容器

```powershell
# 方法 1：直接在 PowerShell 中启动（推荐）
cd D:\code\wtj\ups-guard\deploy\docker
docker-compose -f docker-compose.nut-only.yml down
docker-compose -f docker-compose.nut-only.yml up -d --build

# 方法 2：从 Ubuntu 中启动
wsl -d Ubuntu-24.04 -e bash -c "cd /mnt/d/code/wtj/ups-guard/deploy/docker && docker-compose -f docker-compose.nut-only.yml up -d --build"
```

#### 步骤 9：验证 UPS 连接成功

```powershell
# 查看容器日志，确认 UPS 驱动启动成功
docker logs ups-guard-nut --tail 30

# 成功的日志应该显示：
# ✅ NUT 服务就绪，等待连接...
# Connected to UPS [APC_xxxx]: usbhid-ups-APC_xxxx

# 列出已连接的 UPS
docker exec ups-guard-nut upsc -l localhost
# 应该返回 UPS 名称，如：APC_2161

# 查看 UPS 详细状态
docker exec ups-guard-nut upsc APC_2161@localhost
# 应该返回完整的 UPS 状态信息
```

#### 配置 usbipd 自动附加（可选）

```powershell
# 设置自动附加（设备重新连接时自动附加到运行中的 WSL）
usbipd bind --busid 4-2 --force
usbipd attach --wsl=Ubuntu-24.04 --busid 4-2 --auto-attach
```

#### ⚠️ 每次重启电脑后的操作

如果使用了 `--auto-attach`，流程会更简单：

```powershell
# 1. 启动 Ubuntu（保持运行）
Start-Process -FilePath "wsl" -ArgumentList "-d", "Ubuntu-24.04"

# 2. 等待 Ubuntu 启动和 USB 自动附加
Start-Sleep -Seconds 5

# 3. 验证 USB 已附加
usbipd list  # 确认状态为 "Attached"

# 4. 启动 Docker 容器
cd D:\code\wtj\ups-guard\deploy\docker
docker-compose -f docker-compose.nut-only.yml up -d
```

如果没有使用 `--auto-attach`，需要手动附加：

```powershell
# 1. 启动 Ubuntu
Start-Process -FilePath "wsl" -ArgumentList "-d", "Ubuntu-24.04"
Start-Sleep -Seconds 3

# 2. 手动附加 USB 设备
usbipd attach --wsl=Ubuntu-24.04 --busid 3-2

# 3. 验证并启动容器
usbipd list
cd D:\code\wtj\ups-guard\deploy\docker
docker-compose -f docker-compose.nut-only.yml up -d
```

#### 常见问题排查

**问题：`usbipd attach` 报错 "WSL distribution is not running"**
```powershell
# 原因：Ubuntu 没有运行
# 解决：先启动 Ubuntu
Start-Process -FilePath "wsl" -ArgumentList "-d", "Ubuntu-24.04"
Start-Sleep -Seconds 3
usbipd attach --wsl=Ubuntu-24.04 --busid 4-2
```

**问题：`usbipd bind` 需要管理员权限**
```powershell
# 解决：以管理员身份运行 PowerShell
Start-Process powershell -Verb RunAs -ArgumentList "-Command", "usbipd bind --busid 4-2 --force"
```

**问题：Ubuntu 中看不到 USB 设备（lsusb 无输出）**
```powershell
# 1. 检查 usbipd 状态
usbipd list
# 如果状态不是 "Attached"，重新附加

# 2. 确保 Ubuntu 在运行
wsl -l -v

# 3. 重新附加
usbipd attach --wsl=Ubuntu-24.04 --busid 4-2
```

**问题：Docker 容器内看不到 USB 设备**
```powershell
# 1. 确认 Ubuntu 能看到设备
wsl -d Ubuntu-24.04 -e lsusb

# 2. 重启 Docker 容器
docker restart ups-guard-nut

# 3. 检查容器日志
docker logs ups-guard-nut --tail 50
```

**问题：NUT 驱动报 "No matching HID UPS found"**
```powershell
# 原因：USB 设备没有正确透传到容器
# 解决步骤：
# 1. 确认 Ubuntu 运行中
wsl -l -v

# 2. 确认 USB 已附加
usbipd list  # 状态应为 "Attached"

# 3. 在 Ubuntu 中验证
wsl -d Ubuntu-24.04 -e lsusb  # 应能看到 UPS 设备

# 4. 重启容器
docker restart ups-guard-nut
```

**问题：Docker 容器仍然无法访问**
```bash
# 在 Ubuntu 中检查设备权限
ls -la /dev/bus/usb/

# 如果权限不足，可以临时修改
sudo chmod -R 777 /dev/bus/usb/
```

---

## 2. 查看 UPS 设备名称

### 2.1 什么是 UPS_NAME？

`UPS_NAME` 是 NUT (Network UPS Tools) 中用于标识 UPS 设备的名称。这是一个**自定义标识符**，你可以取任何名字（如 `ups`、`myups`、`server-ups` 等）。

**重要说明**：
- `UPS_NAME` 不是从设备读取的，而是你**自己设定**的
- 默认值通常为 `ups`，大多数情况无需修改
- 后端通过 `UPS_NAME@NUT_HOST` 格式连接 UPS

### 2.2 扫描已连接的 UPS 硬件信息

如果你想查看 UPS 的实际硬件信息（品牌、型号等），可以在服务启动后运行：

```powershell
# 进入项目目录
cd D:\code\wtj\ups-guard\deploy\docker

# 启动 NUT 服务后，扫描 USB UPS 设备
docker exec ups-guard-nut nut-scanner -U
```

示例输出：

```ini
[nutdev1]
    driver = "usbhid-ups"
    port = "auto"
    vendorid = "051D"
    productid = "0002"
    product = "Back-UPS XS 1000M"
    vendor = "American Power Conversion"
```

### 2.3 理解扫描结果

| 字段 | 说明 |
|------|------|
| `[nutdev1]` | NUT 扫描器自动生成的临时名称（**不是** UPS_NAME） |
| `driver` | 推荐使用的驱动程序 |
| `port` | USB 端口设置 |
| `vendorid` | USB 厂商 ID，用于识别品牌 |
| `productid` | USB 产品 ID |
| `product` | UPS 型号名称 |
| `vendor` | 厂商名称 |

### 2.4 常见品牌对照表

| USB Vendor ID | 品牌 | 推荐驱动 |
|---------------|------|----------|
| 051d | APC (施耐德) | `usbhid-ups` |
| 0463 | 山特 (SANTAK) | `blazer_usb` |
| 0665 | CyberPower | `usbhid-ups` |
| 06da | 伊顿 (Eaton) | `usbhid-ups` |
| 0764 | 华为 (Huawei) | `nutdrv_qx` |

---

## 3. 配置环境变量

### 3.1 创建环境配置文件

```powershell
# 进入部署目录
cd D:\code\wtj\ups-guard\deploy\docker

# 复制示例配置
Copy-Item .env.example .env

# 使用记事本编辑（或你喜欢的编辑器）
notepad .env
```

### 3.2 关键配置项说明

编辑 `.env` 文件，设置以下关键配置：

```dotenv
# ============================================
# UPS 基本配置
# ============================================

# UPS 设备名称（自定义标识符，默认 ups 即可）
UPS_NAME=ups

# UPS 驱动程序（根据你的 UPS 品牌选择）
# - APC: usbhid-ups
# - 山特: blazer_usb
# - CyberPower: usbhid-ups
# - 伊顿: usbhid-ups
UPS_DRIVER=usbhid-ups

# UPS 端口（auto 自动检测）
UPS_PORT=auto

# ============================================
# NUT 用户配置（建议修改默认密码）
# ============================================
UPSD_USER=admin
UPSD_PASSWORD=your_secure_password

UPSMON_USER=monuser
UPSMON_PASSWORD=your_secure_password

# ============================================
# 后端配置
# ============================================

# 日志级别（开发测试建议用 DEBUG）
LOG_LEVEL=DEBUG

# Mock 模式（连接真实 UPS 必须设为 false）
MOCK_MODE=false

# API Token（建议设置一个安全的 token）
API_TOKEN=your_random_secure_token_here

# ============================================
# 前端配置
# ============================================

# Web 服务端口
HTTP_PORT=8080
```

### 3.3 配置要点总结

| 配置项 | 开发测试推荐值 | 说明 |
|--------|----------------|------|
| `UPS_NAME` | `ups` | 保持默认即可 |
| `UPS_DRIVER` | 根据品牌选择 | 见上方品牌对照表 |
| `MOCK_MODE` | `false` | **必须 false** 才能连真实 UPS |
| `LOG_LEVEL` | `DEBUG` | 便于调试 |

---

## 4. 启动服务

### 4.1 首次启动（构建镜像）

```powershell
cd D:\code\wtj\ups-guard\deploy\docker

# 首次启动，构建所有镜像
docker-compose up -d --build
```

首次构建可能需要 5-10 分钟，请耐心等待。

### 4.2 查看启动日志

```powershell
# 查看所有服务日志
docker-compose logs -f

# 或分别查看各服务
docker-compose logs -f nut-server   # NUT 服务
docker-compose logs -f backend      # 后端服务
docker-compose logs -f frontend     # 前端服务
```

### 4.3 检查服务状态

```powershell
docker-compose ps
```

正常状态应显示所有服务为 `running` 且 `(healthy)`：

```
NAME                 STATUS              PORTS
ups-guard-backend    Up (healthy)
ups-guard-frontend   Up (healthy)        0.0.0.0:80->80/tcp
ups-guard-nut        Up (healthy)        0.0.0.0:3493->3493/tcp
```

---

## 5. 验证 UPS 连接

### 5.1 检查 NUT 服务器状态

```powershell
# 先查看自动发现的 UPS 列表
docker exec ups-guard-nut upsc -l localhost

# 然后使用发现的名称查看 UPS 状态
# 例如，如果上面返回 ups_APC，则执行：
docker exec ups-guard-nut upsc ups_APC@localhost
```

正常输出示例：

```
battery.charge: 100
battery.runtime: 1800
device.mfr: American Power Conversion
device.model: Back-UPS XS 1000M
ups.load: 25
ups.status: OL
...
```

### 5.2 状态值说明

| ups.status 值 | 含义 |
|---------------|------|
| `OL` | Online - 市电供电中（正常） |
| `OB` | On Battery - 电池供电中（断电） |
| `LB` | Low Battery - 电池电量低 |
| `CHRG` | Charging - 充电中 |
| `DISCHRG` | Discharging - 放电中 |

### 5.3 访问 Web 界面

打开浏览器，访问：

```
http://localhost
```

或

```
http://127.0.0.1
```

### 5.4 验证后端 API

```powershell
# 检查健康状态
curl http://localhost:8000/health

# 或使用浏览器访问
start http://localhost:8000/health
```

---

## 6. 安全关机测试流程

### ⚠️ 重要警告

**在执行真实关机测试前，请务必完成以下所有验证步骤！**

### 6.1 第一步：验证 UPS 状态读取 ✅

```powershell
# 查看发现的 UPS 列表
docker exec ups-guard-nut upsc -l localhost

# 使用发现的 UPS 名称查询状态（假设发现的是 ups_APC）
docker exec ups-guard-nut upsc ups_APC@localhost ups.status
```

**预期结果**：返回 `OL`（市电在线）

**如果失败**：检查 UPS 连接和驱动配置，不要继续下一步。

### 6.2 第二步：验证 Web 界面数据 ✅

1. 打开 `http://localhost`
2. 确认 Dashboard 显示：
   - ✅ UPS 品牌/型号正确
   - ✅ 电池电量百分比
   - ✅ 当前状态为"市电供电"
   - ✅ 预计续航时间

**如果数据不显示或异常**：检查后端日志 `docker-compose logs backend`

### 6.3 第三步：验证实时状态更新 ✅

1. 在 Web 界面保持打开
2. 在 NUT 容器中模拟状态变化（可选）
3. 确认 WebSocket 连接正常（页面数据实时更新）

### 6.4 第四步：配置关机参数（Web UI）

1. 访问 `http://localhost` → **设置**
2. 配置**断电关机策略**：
   - 断电后等待时间：建议 **300 秒**（5 分钟）
   - 低电量阈值：建议 **30%**
   - 预计续航阈值：建议 **300 秒**

### 6.5 第五步：模拟断电测试（安全）

**方法 A：使用 Mock 模式测试关机流程**

```powershell
# 修改 .env，启用 Mock 模式
# MOCK_MODE=true

# 重启服务
docker-compose down
docker-compose up -d
```

在 Mock 模式下测试完整关机流程，确认：
- ✅ 断电事件触发
- ✅ 倒计时显示正常
- ✅ 关机命令执行（但不会真正关机）

**方法 B：拔掉 UPS 电源线测试（推荐）**

这是最接近真实场景的测试方法：

1. 确保笔记本有电池，或使用非关键设备测试
2. 拔掉 UPS 的电源线（**不是** USB 线）
3. 观察 Web 界面状态变化
4. 确认状态从 `OL` → `OB`
5. 确认倒计时开始
6. **在倒计时结束前，插回电源线！**
7. 确认关机取消，状态恢复正常

### 6.6 第六步：真实关机测试

**只有在以上所有步骤都通过后，才能进行真实关机测试！**

1. 保存所有工作
2. 配置合理的等待时间（建议 300 秒以上）
3. 拔掉 UPS 电源线
4. 观察系统按预期执行关机
5. 恢复电源，重新启动系统

---

## 7. 开发调试技巧

### 7.1 实时查看日志

```powershell
# 所有服务日志
docker-compose logs -f

# 只看后端日志（最常用）
docker-compose logs -f backend

# 查看最近 100 行
docker-compose logs --tail=100 backend
```

### 7.2 进入容器调试

```powershell
# 进入 NUT 容器
docker exec -it ups-guard-nut /bin/sh

# 进入后端容器
docker exec -it ups-guard-backend /bin/bash
```

### 7.3 重启单个服务

```powershell
# 只重启后端
docker-compose restart backend

# 重新构建后端
docker-compose up -d --build backend
```

### 7.4 清理重建

```powershell
# 停止并删除所有容器
docker-compose down

# 删除数据卷（慎用！会删除配置）
docker-compose down -v

# 完全重建
docker-compose up -d --build
```

### 7.5 热重载开发模式

如需频繁修改代码，可以使用开发模式：

```powershell
# 复制开发配置
Copy-Item docker-compose.override.yml.example docker-compose.override.yml

# 启动（会自动合并配置）
docker-compose up -d
```

开发模式特性：
- 后端代码修改后自动重载
- 前端支持热更新
- 详细 DEBUG 日志

---

## 8. 常见问题

### Q1: 无法检测到 UPS 设备

**现象**：`nut-scanner -U` 无输出或报错

**解决方案**：

1. **确认 USB 连接**：
   - 检查 UPS 的 USB 线是否正确连接到电脑
   - 尝试换一个 USB 端口
   - 确认 UPS 已开机

2. **Windows 设备管理器检查**：
   - 打开设备管理器
   - 查看"电池"或"通用串行总线控制器"下是否有 UPS 设备
   - 如有黄色感叹号，需要安装驱动

3. **Docker Desktop USB 透传**：
   - 确保 Docker Desktop 使用 WSL2 后端
   - 某些情况下 Windows 上 Docker 可能无法直接访问 USB 设备
   - 可能需要使用 `usbipd-win` 工具将 USB 设备透传到 WSL

### Q2: Windows Docker 无法访问 USB 设备 / NUT 报 "No matching HID UPS found"

**现象**：容器启动后 NUT 驱动报错 `No matching HID UPS found`，即使 `lsusb` 能看到设备。

**原因**：USB 设备没有正确透传到 Docker 容器。

**快速检查清单**：
```powershell
# 1. 确认 Ubuntu 正在运行
wsl -l -v  # Ubuntu-24.04 状态应为 "Running"

# 2. 确认 USB 设备已附加
usbipd list  # UPS 设备状态应为 "Attached"

# 3. 确认 Ubuntu 能看到设备
wsl -d Ubuntu-24.04 -e lsusb  # 应显示 UPS 设备

# 4. 确认 Docker Desktop WSL 集成已启用
# Docker Desktop → Settings → Resources → WSL Integration → Ubuntu-24.04 ✅

# 5. 如果以上都正常，重启容器
docker-compose -f docker-compose.nut-only.yml down
docker-compose -f docker-compose.nut-only.yml up -d
```

**常见解决步骤**：

1. **确保 Ubuntu 先启动**：
```powershell
Start-Process -FilePath "wsl" -ArgumentList "-d", "Ubuntu-24.04"
Start-Sleep -Seconds 3
```

2. **重新附加 USB 设备**：
```powershell
usbipd attach --wsl=Ubuntu-24.04 --busid 3-2 --auto-attach
```

3. **重启 Docker 容器**：
```powershell
docker restart ups-guard-nut
```

4. **检查容器日志**：
```powershell
docker logs ups-guard-nut --tail 50
# 成功时应看到：✅ UPS 驱动启动成功
```

### Q3: 前端无法连接后端

**现象**：Web 页面显示"连接失败"

**解决方案**：

```powershell
# 1. 检查后端是否运行
docker-compose ps

# 2. 检查后端日志
docker-compose logs backend

# 3. 测试后端 API
curl http://localhost:8000/health

# 4. 检查 API_TOKEN 是否配置正确
```

### Q4: UPS 状态显示异常

**解决方案**：

```powershell
# 1. 查看发现的 UPS 列表
docker exec ups-guard-nut upsc -l localhost

# 2. 使用发现的名称检查 NUT 服务状态
docker exec ups-guard-nut upsc <发现的UPS名称>@localhost

# 3. 检查驱动是否正确
docker-compose logs nut-server | Select-String "driver"

# 4. 尝试手动指定驱动
# 修改 .env 中的 UPS_DRIVER
```

### Q5: 关机测试不执行

**检查清单**：

1. `MOCK_MODE=false` 是否设置？
2. 关机策略是否在 Web UI 中启用？
3. 等待时间是否设置合理？
4. 查看后端日志确认是否有关机命令发送

---

## 📝 测试检查清单

在正式使用前，请确保完成以下所有检查项：

- [ ] Docker Desktop 运行正常
- [ ] UPS USB 连接正常
- [ ] `.env` 配置正确（特别是 `MOCK_MODE=false`）
- [ ] 服务全部启动并健康
- [ ] `upsc -l localhost` 能发现 UPS 设备
- [ ] 使用发现的 UPS 名称能返回状态
- [ ] Web 界面显示正确的 UPS 信息
- [ ] WebSocket 实时更新正常
- [ ] 关机策略已在 Web UI 配置
- [ ] 模拟断电测试通过（拔电源线后能恢复）
- [ ] 真实关机测试通过

---

## 🔗 相关文档

- [Docker 部署指南](docker-deployment.md)
- [用户指南](user-guide.md)
- [架构说明](architecture.md)
- [常见问题](faq.md)

