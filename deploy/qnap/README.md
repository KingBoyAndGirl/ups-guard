# 威联通 NAS 部署指南

在威联通 NAS 上通过 Container Station 部署 UPS Guard。

## 前提条件

- QTS 5.0+ 或 QuTS hero
- 已安装 Container Station 套件
- UPS 通过 USB 连接到威联通 NAS

## 部署步骤

### 1. 准备工作

1. 打开 **Container Station**
2. 进入 **创建** → **创建应用程序**

### 2. 创建应用

#### 使用 YAML 配置

1. 选择「创建应用程序」
2. 应用名称：`ups-guard`
3. 选择「YAML」配置方式
4. 粘贴 `docker-compose.yml` 内容
5. 配置环境变量

### 3. 配置环境变量

点击「环境」选项卡，添加以下变量：

| 变量名 | 值 | 说明 |
|-------|-----|------|
| UPS_NAME | ups | UPS 名称 |
| UPS_DRIVER | usbhid-ups | UPS 驱动 |
| UPSD_PASSWORD | your_password | NUT 管理密码 |
| UPSMON_PASSWORD | your_password | NUT 监控密码 |
| API_TOKEN | random_token | API 认证令牌 |
| HTTP_PORT | 9080 | Web 端口 |

### 4. USB 设备直通

**重要步骤**：

1. 在 YAML 中确保 `privileged: true`
2. 挂载 USB 设备：`/dev/bus/usb:/dev/bus/usb`

### 5. 存储路径

修改数据卷路径为威联通实际路径：

```yaml
volumes:
  - /share/Container/ups-guard/data:/data
```

### 6. 创建并启动

点击 **创建** 启动所有容器。

## 访问 Web 界面

`http://<威联通IP>:9080`

## 与威联通联动关机

UPS Guard 支持在断电时自动关闭威联通 NAS：

1. 进入 UPS Guard 设置
2. 添加关机 Hook → 选择「威联通 NAS 关机」
3. 配置威联通 IP、用户名、密码

## 注意事项

### Container Station 版本

- 推荐使用 Container Station 3.x
- 旧版本可能不支持某些 YAML 语法

### 网络模式

如果遇到网络问题，可尝试使用 `host` 网络模式。

### 日志查看

在 Container Station 中点击容器，查看「日志」选项卡。

## 常见问题

### USB 设备未识别

1. SSH 登录威联通：`ssh admin@<IP>`
2. 检查 USB 设备：`lsusb`
3. 确认驱动配置正确

### 容器无法启动

检查：
1. 端口是否被占用
2. 存储路径是否存在
3. 容器日志错误信息

