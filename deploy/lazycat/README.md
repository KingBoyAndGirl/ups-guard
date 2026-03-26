# UPS Guard - 懒猫微服部署指南

## 文件说明

| 文件 | 说明 |
|------|------|
| `.env` | 部署配置（Docker Hub 用户名等） |
| `deploy-to-lazycat.ps1` | Windows 部署脚本 |
| `deploy-to-lazycat.sh` | Mac/Linux 部署脚本 |
| `Dockerfile` | Docker 镜像构建配置 |
| `entrypoint.sh` | 容器启动脚本 |
| `lzc-manifest.yml` | 懒猫应用清单 |
| `lzc-build.yml` | LPK 构建配置 |
| `lzc-icon.png` | 应用图标 |

## 快速部署

### Windows (PowerShell)

```powershell
# 1. 配置 .env 文件
#    设置 DOCKERHUB_USERNAME 为你的 Docker Hub 用户名

# 2. 运行部署脚本
.\deploy-to-lazycat.ps1
```

### Mac/Linux (Bash)

```bash
# 1. 配置 .env 文件
#    设置 DOCKERHUB_USERNAME 为你的 Docker Hub 用户名

# 2. 添加执行权限并运行
chmod +x deploy-to-lazycat.sh
./deploy-to-lazycat.sh
```

## 命令行参数

| 参数 | PowerShell | Bash | 说明 |
|------|------------|------|------|
| 详细输出 | `-Verbose` | `-v` | 显示详细构建日志 |
| 自动安装 | `-AutoInstall` | `-a` | 跳过安装确认 |
| 帮助 | `-Help` | `-h` | 显示帮助信息 |

## 部署流程

脚本会自动完成以下步骤：

1. 构建前端
2. 构建 Docker 镜像
3. 推送到 Docker Hub
4. 复制到懒猫 Registry
5. 更新 manifest 中的镜像地址
6. 构建并安装 LPK 包

## 版本管理

版本号从 `lzc-manifest.yml` 中的 `version` 字段自动提取，修改该字段即可更新版本。
