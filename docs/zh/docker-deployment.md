# Docker 部署指南

本文档介绍如何使用 Docker Compose 在任何支持 Docker 的设备上部署 UPS Guard 系统。

## 系统要求

- Docker Engine 20.10+
- Docker Compose 2.0+
- 硬件：至少 512MB RAM，1GB 磁盘空间
- USB 接口（用于连接 UPS 设备）

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/KingBoyAndGirl/ups-guard.git
cd ups-guard
```

### 2. 配置环境变量

复制环境变量示例文件并根据实际情况修改：

```bash
cp .env.example .env
nano .env  # 或使用其他编辑器
```

关键配置项：

```bash
# UPS 设备配置
UPS_NAME=ups
UPS_DRIVER=usbhid-ups  # 根据 UPS 品牌选择驱动
UPS_PORT=auto

# NUT 用户密码（建议修改）
UPSD_USER=admin
UPSD_PASSWORD=your_secure_password
UPSMON_USER=monuser
UPSMON_PASSWORD=your_secure_password

# API Token（建议手动设置）
API_TOKEN=your_random_secure_token

# HTTP 端口
HTTP_PORT=80
```

### 3. 启动服务

```bash
docker-compose up -d
```

首次启动会自动：
- 构建所有服务镜像
- 创建数据卷
- 启动 NUT Server、Backend 和 Frontend 服务
- 自动检测 USB 连接的 UPS 设备

### 4. 访问 Web 界面

打开浏览器访问：`http://localhost` 或 `http://<your-server-ip>`

### 5. 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f nut-server
docker-compose logs -f frontend
```

## UPS 驱动配置

### 自动检测

启动时，NUT Server 会自动扫描 USB 设备并尝试识别 UPS 品牌：

```bash
docker-compose logs nut-server | grep "UPS 品牌识别"
```

### 手动配置

如果自动识别失败，可以在 `.env` 文件中手动指定驱动：

#### 常见 UPS 品牌驱动对照表

| 品牌 | USB Vendor ID | 推荐驱动 |
|------|---------------|----------|
| APC (施耐德) | 051d | `usbhid-ups` |
| 山特 (SANTAK) | 0463 | `blazer_usb` |
| CyberPower | 0665 | `usbhid-ups` |
| 伊顿 (Eaton) | 06da | `usbhid-ups` |
| 华为 | 0764 | `nutdrv_qx` |
| 山特 Castle | 0001 | `nutdrv_qx` |

#### 查看 USB Vendor/Product ID

```bash
docker exec ups-guard-nut nut-scanner -U
```

示例输出：

```
[nutdev1]
    driver = "usbhid-ups"
    port = "auto"
    vendorid = "051D"
    productid = "0002"
    product = "Back-UPS XS 1000M"
    vendor = "American Power Conversion"
```

根据输出修改 `.env` 中的 `UPS_DRIVER` 配置。

## 开发模式

开发/测试模式使用 Mock 数据，无需连接真实 UPS 设备。

### 1. 创建开发配置

```bash
cp docker-compose.override.yml.example docker-compose.override.yml
```

### 2. 启动开发模式

```bash
docker-compose up -d
```

Docker Compose 会自动合并 `docker-compose.yml` 和 `docker-compose.override.yml`，启用 Mock 模式。

### 3. 开发模式特性

- 使用 `dummy-ups` 驱动（不需要真实 UPS）
- 后端使用 Mock 数据
- 前端支持热重载（修改代码自动刷新）
- 详细日志输出（LOG_LEVEL=DEBUG）

## 纳管设备配置

UPS Guard 支持在断电时自动关闭多台设备。

### 1. 访问设置页面

打开 Web 界面 → 设置 → 预关机任务

### 2. 添加设备

支持的设备类型：

- **SSH 远程关机**：Linux/macOS 服务器
- **Windows 远程关机**：Windows 系统
- **群晖关机**：Synology NAS
- **威联通关机**：QNAP NAS
- **HTTP API**：自定义 REST API
- **自定义脚本**：Shell/Python 脚本

### 3. 查看设备状态

在 Dashboard 页面的"纳管设备"区域可以：
- 查看所有设备的在线状态
- 测试设备连接
- 查看最后检测时间
- 实时查看关机执行进度

### 4. 关机执行流程

断电触发关机时：
1. 按优先级分组（数字小的先执行）
2. 同优先级的设备并行关机
3. 实时显示每台设备的执行状态
4. 所有设备关机完成后，关闭本机

## 常见问题

### Q1: 无法检测到 UPS 设备

**解决方法：**

1. 检查 USB 连接：
   ```bash
   lsusb | grep -i ups
   ```

2. 检查 NUT Server 日志：
   ```bash
   docker-compose logs nut-server
   ```

3. 尝试手动指定驱动：
   修改 `.env` 中的 `UPS_DRIVER` 和 `UPS_PORT`

### Q2: 权限不足无法访问 USB 设备

**解决方法：**

确保 Docker 容器有 USB 设备访问权限：

```bash
# 添加当前用户到 dialout 组
sudo usermod -aG dialout $USER

# 重启 Docker 服务
sudo systemctl restart docker

# 重启容器
docker-compose restart nut-server
```

### Q3: Frontend 无法连接 Backend

**解决方法：**

1. 检查 Backend 是否正常运行：
   ```bash
   docker-compose logs backend
   curl http://localhost:8000/health
   ```

2. 检查 API Token 配置：
   确保 `.env` 中的 `API_TOKEN` 已设置

3. 检查防火墙：
   确保端口 80 和 3493 未被占用或被防火墙阻止

### Q4: WebSocket 连接失败

**解决方法：**

1. 检查 Nginx 配置：
   ```bash
   docker exec ups-guard-frontend cat /etc/nginx/conf.d/default.conf
   ```

2. 检查浏览器控制台错误

3. 尝试使用 HTTP 而非 HTTPS（开发环境）

## 数据备份与恢复

### 备份

```bash
# 备份配置和历史数据
docker run --rm -v ups-data:/data -v $(pwd):/backup alpine \
  tar czf /backup/ups-guard-backup.tar.gz /data
```

### 恢复

```bash
# 恢复数据
docker run --rm -v ups-data:/data -v $(pwd):/backup alpine \
  tar xzf /backup/ups-guard-backup.tar.gz -C /
```

## 升级

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build
```

## 卸载

```bash
# 停止并移除所有容器
docker-compose down

# 删除数据卷（注意：会删除所有配置和历史数据）
docker-compose down -v

# 删除镜像
docker rmi $(docker images | grep ups-guard | awk '{print $3}')
```

## 安全建议

1. **修改默认密码**：修改 `.env` 中的所有密码
2. **设置 API Token**：不要使用自动生成的 Token，手动设置一个强密码
3. **限制网络访问**：使用防火墙限制 Web 界面访问
4. **定期备份**：定期备份配置和历史数据
5. **更新系统**：定期更新 Docker 镜像和系统

## 技术支持

- GitHub Issues: https://github.com/KingBoyAndGirl/ups-guard/issues
- 文档：查看 `docs/` 目录下的其他文档

## 许可证

本项目采用 GPL-3.0 许可证。详见 [LICENSE](../LICENSE) 文件。
