# Docker 通用部署

适用于任何支持 Docker 的 Linux 服务器、Windows、macOS 等平台。

## 系统要求

- Docker Engine 20.10+
- Docker Compose 2.0+
- 至少 512MB RAM
- USB 接口（连接 UPS）

## 快速部署

### 1. 准备配置文件

```bash
# 复制环境变量配置
cp .env.example .env

# 编辑配置（根据实际情况修改）
nano .env
```

### 2. 关键配置项

```bash
# UPS 驱动（根据品牌选择）
UPS_DRIVER=usbhid-ups    # APC、CyberPower、Eaton
# UPS_DRIVER=blazer_usb  # 山特 SANTAK
# UPS_DRIVER=nutdrv_qx   # 其他 Megatec 协议

# 安全配置（建议修改默认密码）
UPSD_PASSWORD=your_secure_password
UPSMON_PASSWORD=your_secure_password
API_TOKEN=your_random_token

# Web 端口
HTTP_PORT=80
```

### 3. 启动服务

```bash
docker-compose up -d
```

### 4. 查看状态

```bash
# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 检查 UPS 连接（先列出发现的 UPS，再查询详情）
docker-compose exec nut-server upsc -l localhost
docker-compose exec nut-server upsc <发现的UPS名称>@localhost
```

## 访问 Web 界面

打开浏览器访问：`http://localhost` 或 `http://<服务器IP>`

## 常见问题

### UPS 未识别

1. 检查 USB 连接：`lsusb`
2. 查看 NUT 日志：`docker-compose logs nut-server`
3. 尝试更换驱动配置

### 权限问题

确保 docker-compose.yml 中 nut-server 服务有 `privileged: true`

## 文件说明

- `docker-compose.yml` - 主编排文件
- `docker-compose.override.yml.example` - 自定义覆盖示例
- `.env.example` - 环境变量模板

