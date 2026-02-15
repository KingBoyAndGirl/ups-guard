# UPS Guard - 安装指南

## 系统要求

- 支持 Docker 的设备（Windows、Linux、macOS、懒猫微服、群辉、威联通等）
- 支持 USB 的 UPS 设备
- 至少 1GB 可用存储空间

## 安装方式

### 方式一：Docker Compose 部署（推荐）

适用于任意有 Docker 的设备。详细步骤请参考 [Docker 部署文档](./DOCKER_DEPLOYMENT.md)。

### 方式二：懒猫微服部署

适用于懒猫微服用户，可使用原生应用包（.lpk 格式）安装。

#### 1. 下载应用包

从 GitHub Releases 下载最新版本的 `.lpk` 安装包。

#### 2. 安装应用

在懒猫微服控制面板中：

1. 进入「应用商店」
2. 点击「本地安装」
3. 选择下载的 `.lpk` 文件
4. 等待安装完成

#### 3. 连接 UPS 设备

1. 将 UPS 通过 USB 线缆连接到懒猫微服主机
2. 确保 USB 连接稳定
3. 应用会自动检测 UPS 设备

#### 4. 访问应用

安装完成后，通过以下地址访问：

```
http://your-lazycat-host/ups-guard/
```

或使用子域名：

```
http://ups-guard.your-lazycat-host/
```

## 初次配置

1. **检查 UPS 连接**
   - 在仪表盘页面查看 UPS 状态
   - 确认显示为「市电供电」状态

2. **配置关机策略**
   - 进入「设置」页面
   - 设置停电后等待时间（建议 5-10 分钟）
   - 设置最低电量百分比（建议 20-30%）
   - 设置最终等待时间（建议 30-60 秒）

3. **配置推送通知**（可选）
   - 在「设置」页面添加通知渠道
   - 支持 Server酱 和 PushPlus
   - 测试通知是否正常

## 验证安装

运行以下检查确保安装正常：

1. ✅ 仪表盘显示 UPS 实时数据
2. ✅ WebSocket 连接状态为「已连接」
3. ✅ 历史记录页面显示数据图表
4. ✅ 事件日志记录系统启动事件

## 故障排除

### UPS 显示离线

1. 检查 USB 连接是否正常
2. 确认 UPS 设备已开机
3. 查看应用日志：`docker logs ups-guard-nut-server`
4. 检查 UPS 驱动是否支持（参见 [支持的 UPS 设备](./supported-ups.md)）

### 无法访问应用

1. 检查应用是否正常运行：`docker ps | grep ups-guard`
2. 检查端口是否被占用
3. 查看应用日志：`docker logs ups-guard-backend`

### 通知发送失败

1. 检查网络连接
2. 验证通知渠道配置是否正确
3. 使用「测试通知」功能排查问题

## 卸载应用

### Docker Compose 部署

```bash
docker-compose down -v  # -v 会删除数据卷
```

### 懒猫微服部署

在懒猫微服控制面板中：

1. 进入「应用管理」
2. 找到「UPS Guard」
3. 点击「卸载」
4. 确认卸载操作

注意：卸载会删除所有历史数据。如需保留数据，请先备份数据库文件 `/data/ups_guard.db`。

## 更新应用

### Docker Compose 部署

```bash
git pull
docker-compose down
docker-compose up -d --build
```

### 懒猫微服部署

1. 下载新版本的 `.lpk` 安装包
2. 在应用管理中点击「更新」
3. 选择新版本安装包
4. 等待更新完成

更新过程会保留配置和历史数据。
