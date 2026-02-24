# UPS Guard - 懒猫微服单容器 Dockerfile
# 将 NUT + Backend + Frontend 整合到一个容器中

# ==================== 阶段 1: 前端构建 ====================
FROM node:20-alpine AS frontend-builder

WORKDIR /app

ARG NPM_REGISTRY=https://registry.npmjs.org

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm config set registry ${NPM_REGISTRY} && \
    npm ci --no-audit --no-fund

COPY frontend/ ./
RUN npm run build

# ==================== 阶段 2: 后端依赖安装 ====================
FROM python:3.11-alpine AS backend-builder

WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_TRUSTED_HOST=pypi.org

COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache -r pyproject.toml

# ==================== 阶段 3: 最终镜像 ====================
FROM python:3.11-alpine

LABEL org.opencontainers.image.title="UPS Guard" \
      org.opencontainers.image.description="懒猫微服 UPS 智能监控与管理应用" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="AGPL-3.0" \
      org.opencontainers.image.source="https://github.com/KingBoyAndGirl/ups-guard"

RUN apk add --no-cache \
        nut usbutils libusb-dev eudev \
        curl bash dos2unix procps && \
    mkdir -p /data /run/nut /etc/nut /var/state/ups /tmp/ups-info && \
    chown -R nut:nut /run/nut /etc/nut /var/state/ups && \
    mkdir -p /etc/udev/rules.d && \
    printf '%s\n' \
        'SUBSYSTEM=="usb", ATTR{idVendor}=="051d", MODE="0666"' \
        'SUBSYSTEM=="usb", ATTR{idVendor}=="0463", MODE="0666"' \
        'SUBSYSTEM=="usb", ATTR{idVendor}=="0665", MODE="0666"' \
        'SUBSYSTEM=="usb", ATTR{idVendor}=="06da", MODE="0666"' \
        'SUBSYSTEM=="usb", ATTR{idVendor}=="0764", MODE="0666"' \
        > /etc/udev/rules.d/99-nut-ups.rules

WORKDIR /app

# 从构建阶段复制 Python 依赖
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# 按变更频率从低到高排列
COPY nut/entrypoint.sh /app/nut/entrypoint.sh
COPY nut/*.template /app/nut/
COPY deploy/lazycat/entrypoint.sh /entrypoint.sh

# 从阶段 1 复制前端构建产物
COPY --from=frontend-builder /app/dist ./frontend/dist

COPY backend/src ./backend/src

RUN chmod +x /entrypoint.sh /app/nut/entrypoint.sh && \
    dos2unix /entrypoint.sh /app/nut/entrypoint.sh 2>/dev/null || true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
