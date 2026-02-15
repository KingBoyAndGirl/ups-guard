# UPS Guard - 懒猫微服单容器 Dockerfile
# 将 NUT + Backend + Frontend 整合到一个容器中
# 基于 Alpine 以减小镜像大小

FROM python:3.11-alpine

# 镜像元数据（符合 OCI 标准）
LABEL org.opencontainers.image.title="UPS Guard"
LABEL org.opencontainers.image.description="懒猫微服 UPS 智能监控与管理应用"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.licenses="AGPL-3.0"
LABEL org.opencontainers.image.source="https://github.com/KingBoyAndGirl/ups-guard"
LABEL org.opencontainers.image.documentation="https://github.com/KingBoyAndGirl/ups-guard#readme"
LABEL org.opencontainers.image.vendor="KingBoyAndGirl"

# 安装系统依赖：NUT、工具（移除 nginx 和 supervisor）
RUN apk add --no-cache \
    nut \
    usbutils \
    libusb-dev \
    eudev \
    curl \
    bash \
    dos2unix \
    procps

# 设置工作目录
WORKDIR /app

# 复制后端代码和依赖
COPY backend/pyproject.toml ./backend/
RUN pip install --no-cache-dir uv && \
    cd /app/backend && \
    uv pip install --system --no-cache -r pyproject.toml

COPY backend/src ./backend/src

# 复制前端构建产物（需要先在本地构建）
COPY frontend/dist ./frontend/dist

# 复制 NUT entrypoint（使用已验证的脚本）
COPY nut/entrypoint.sh /app/nut/entrypoint.sh
COPY nut/*.template /app/nut/

# 复制懒猫专用启动脚本
COPY deploy/lazycat/entrypoint.sh /entrypoint.sh

# 设置权限和转换行尾
RUN chmod +x /entrypoint.sh /app/nut/entrypoint.sh && \
    dos2unix /entrypoint.sh /app/nut/entrypoint.sh 2>/dev/null || true

# 创建必要目录和设置权限
RUN mkdir -p /data /run/nut /etc/nut /var/state/ups /tmp/ups-info && \
    chown -R nut:nut /run/nut /etc/nut /var/state/ups

# udev 规则 - 允许访问常见 UPS 厂商的 USB 设备
RUN mkdir -p /etc/udev/rules.d && \
    echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="051d", MODE="0666"' > /etc/udev/rules.d/99-nut-ups.rules && \
    echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="0463", MODE="0666"' >> /etc/udev/rules.d/99-nut-ups.rules && \
    echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="0665", MODE="0666"' >> /etc/udev/rules.d/99-nut-ups.rules && \
    echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="06da", MODE="0666"' >> /etc/udev/rules.d/99-nut-ups.rules && \
    echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="0764", MODE="0666"' >> /etc/udev/rules.d/99-nut-ups.rules

# 暴露端口（后端直接对外服务）
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动
ENTRYPOINT ["/entrypoint.sh"]

