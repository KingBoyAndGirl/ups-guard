# 部署指南

本目录包含针对不同设备和平台的部署配置文件。

## 目录结构

```
deploy/
├── docker/          # 通用 Docker 部署（适用于任何支持 Docker 的设备）
├── lazycat/         # 懒猫微服专用部署
├── synology/        # 群晖 NAS 部署
└── qnap/            # 威联通 NAS 部署
```

## 部署方式选择

| 设备类型 | 推荐部署方式 | 说明 |
|---------|-------------|------|
| 懒猫微服 | `lazycat/` | 原生应用，一键安装 |
| 群晖 NAS | `synology/` | Container Manager 部署 |
| 威联通 NAS | `qnap/` | Container Station 部署 |
| Linux 服务器 | `docker/` | 通用 Docker Compose |
| Windows/Mac | `docker/` | Docker Desktop |

## 快速开始

### 懒猫微服

```bash
# 使用 lzc-cli 打包
cd deploy/lazycat
./build.sh
# 上传生成的 .lpk 文件到懒猫微服
```

### 通用 Docker

```bash
cd deploy/docker
cp .env.example .env
# 编辑 .env 配置
docker-compose up -d
```

### 群晖 NAS

参考 `synology/README.md` 详细说明。

### 威联通 NAS

参考 `qnap/README.md` 详细说明。

## 注意事项

1. **USB 直通**：所有部署方式都需要将 UPS 的 USB 设备直通给容器
2. **权限**：NUT 服务需要 privileged 权限访问 USB 设备
3. **网络**：确保前端可以访问后端 API

