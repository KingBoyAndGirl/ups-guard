# 群晖 NAS 部署指南

在群晖 NAS 上通过 Container Manager (Docker) 部署 UPS Guard。

## 前提条件

- 群晖 DSM 7.0+
- 已安装 Container Manager 套件
- UPS 通过 USB 连接到群晖 NAS

## 部署步骤

### 1. 准备工作

1. 打开 **Container Manager**
2. 进入 **项目** 页面

### 2. 创建项目

#### 方式一：使用 docker-compose.yml

1. 点击 **创建**
2. 项目名称：`ups-guard`
3. 路径：选择一个目录（如 `/docker/ups-guard`）
4. 来源：选择「创建 docker-compose.yml」
5. 粘贴 `docker-compose.yml` 内容

#### 方式二：上传文件

1. 将本目录的文件上传到群晖
2. 在 Container Manager 中导入

### 3. 配置环境变量

在项目设置中添加环境变量，或创建 `.env` 文件：

```bash
# UPS 配置
UPS_NAME=ups
UPS_DRIVER=usbhid-ups
UPS_PORT=auto

# 密码配置
UPSD_USER=admin
UPSD_PASSWORD=your_password
UPSMON_USER=monuser
UPSMON_PASSWORD=your_password

# API Token
API_TOKEN=your_random_token

# 端口
HTTP_PORT=9080
```

### 4. USB 设备直通

**重要**：需要将 UPS USB 设备直通给容器。

在 `docker-compose.yml` 中确保：

```yaml
nut-server:
  privileged: true
  volumes:
    - /dev/bus/usb:/dev/bus/usb
```

### 5. 启动项目

点击 **构建** 启动所有服务。

## 访问 Web 界面

`http://<群晖IP>:9080`

## 与群晖联动关机

UPS Guard 支持在断电时自动关闭群晖 NAS：

1. 进入 UPS Guard 设置
2. 添加关机 Hook → 选择「群晖 NAS 关机」
3. 配置群晖 IP、用户名、密码

## 注意事项

### 端口冲突

如果 80 端口被占用，修改 `HTTP_PORT` 为其他端口（如 9080）。

### 权限问题

如果 USB 设备无法识别：

1. 确认 `privileged: true` 已设置
2. SSH 登录群晖检查：`lsusb`
3. 查看容器日志排查问题

### DSM 防火墙

确保防火墙允许访问配置的端口。

## 常见 UPS 驱动

| 品牌 | 驱动 |
|------|------|
| APC | `usbhid-ups` |
| CyberPower | `usbhid-ups` |
| 山特 | `blazer_usb` |
| 伊顿 | `usbhid-ups` |

