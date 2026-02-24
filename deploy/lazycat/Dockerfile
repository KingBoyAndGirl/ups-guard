# UPS Guard - 懒猫微服单容器 Dockerfile
# 将 NUT + Backend + Frontend 整合到一个容器中

# ==================== 阶段 1: 后端依赖安装 ====================
FROM python:3.11-alpine AS backend-builder

WORKDIR /app

# 先复制依赖声明，利用 Docker 层缓存
COPY backend/pyproject.toml ./

# 安装 uv 并安装依赖到虚拟环境（避免污染系统 Python）
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache -r pyproject.toml

# ==================== 阶段 2: 最终镜像 ====================
FROM python:3.11-alpine

LABEL org.opencontainers.image.title="UPS Guard" \
      org.opencontainers.image.description="懒猫微服 UPS 智能监控与管理应用" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="AGPL-3.0" \
      org.opencontainers.image.source="https://github.com/KingBoyAndGirl/ups-guard"

# 一次性安装所有系统依赖，合并 RUN 减少层数
# --no-cache 避免 apk 缓存占空间
RUN apk add --no-cache \
        nut usbutils libusb-dev eudev \
        curl bash dos2unix procps && \
    # 创建所有必要目录 + 设置权限
    mkdir -p /data /run/nut /etc/nut /var/state/ups /tmp/ups-info && \
    chown -R nut:nut /run/nut /etc/nut /var/state/ups && \
    # udev 规则 - 常见 UPS 厂商 USB 设备
    mkdir -p /etc/udev/rules.d && \
    printf '%s\n' \
        'SUBSYSTEM=="usb", ATTR{idVendor}=="051d", MODE="0666"' \
        'SUBSYSTEM=="usb", ATTR{idVendor}=="0463", MODE="0666"' \
        'SUBSYSTEM=="usb", ATTR{idVendor}=="0665", MODE="0666"' \
        'SUBSYSTEM=="usb", ATTR{idVendor}=="06da", MODE="0666"' \
        'SUBSYSTEM=="usb", ATTR{idVendor}=="0764", MODE="0666"' \
        > /etc/udev/rules.d/99-nut-ups.rules

WORKDIR /app

# 从构建阶段复制已安装的 Python 依赖
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# 按变更频率从低到高排列 COPY，最大化缓存命中
# 1. NUT 配置模板（极少改）
COPY nut/entrypoint.sh /app/nut/entrypoint.sh
COPY nut/*.template /app/nut/

# 2. 启动脚本（偶尔改）
COPY deploy/lazycat/entrypoint.sh /entrypoint.sh

# 3. 前端构建产物（每次前端改动）
COPY frontend/dist ./frontend/dist

# 4. 后端代码（最频繁改动放最后）
COPY backend/src ./backend/src

# 统一处理权限和行尾（一层搞定）
RUN chmod +x /entrypoint.sh /app/nut/entrypoint.sh && \
    dos2unix /entrypoint.sh /app/nut/entrypoint.sh 2>/dev/null || true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]