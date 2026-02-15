#!/bin/bash
set -e

# UPS Guard Entrypoint for Lazycat Microservice
# This script starts NUT service and the Backend service in a single container

echo "==========================================="
echo "  UPS Guard for Lazycat Microservice"
echo "==========================================="

# 环境变量配置（与 docker-compose.yml 兼容）
# 数据目录（通过 services.binds 挂载到 /data）
DATA_DIR="${DATA_DIR:-/data}"
export DATABASE_PATH="${DATABASE_PATH:-${DATA_DIR}/ups_guard.db}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
export MOCK_MODE="${MOCK_MODE:-false}"

# NUT 配置
export NUT_HOST="${NUT_HOST:-127.0.0.1}"
export NUT_PORT="${NUT_PORT:-3493}"
export NUT_USERNAME="${NUT_USERNAME:-monuser}"
export NUT_PASSWORD="${NUT_PASSWORD:-secret}"

# UPS 配置
export UPS_DRIVER="${UPS_DRIVER:-usbhid-ups}"
export UPS_PORT="${UPS_PORT:-auto}"
export UPSD_LISTEN="${UPSD_LISTEN:-0.0.0.0}"
export UPSD_USER="${UPSD_USER:-admin}"
export UPSD_PASSWORD="${UPSD_PASSWORD:-secret}"
export UPSMON_USER="${UPSMON_USER:-monuser}"
export UPSMON_PASSWORD="${UPSMON_PASSWORD:-secret}"
export DISABLE_SHUTDOWN="${DISABLE_SHUTDOWN:-true}"

echo "Configuration:"
echo "  DATA_DIR: ${DATA_DIR}"
echo "  DATABASE_PATH: ${DATABASE_PATH}"
echo "  LOG_LEVEL: ${LOG_LEVEL}"
echo "  MOCK_MODE: ${MOCK_MODE}"
echo "  UPS_DRIVER: ${UPS_DRIVER}"
echo "  DISABLE_SHUTDOWN: ${DISABLE_SHUTDOWN}"

# 确保数据目录存在
mkdir -p "${DATA_DIR}"

# 创建 NUT 必需目录
mkdir -p /run/nut /etc/nut /var/state/ups /tmp/ups-info
if id nut &>/dev/null; then
    if ! chown -R nut:nut /run/nut /etc/nut /var/state/ups 2>/dev/null; then
        echo "  Warning: Failed to change ownership of NUT directories (may require privileged mode)"
    fi
else
    echo "  Warning: NUT user not found, skipping directory ownership changes"
fi

# 启动 NUT 服务（后台运行）
echo ""
echo "Starting NUT service..."
if [ -f "/app/nut/entrypoint.sh" ]; then
    cd /app/nut
    bash /app/nut/entrypoint.sh &
    NUT_PID=$!
    echo "  NUT service started (PID: ${NUT_PID})"
    # 等待 NUT 服务启动
    sleep 5
    # 验证进程是否仍在运行
    if ! kill -0 ${NUT_PID} 2>/dev/null; then
        echo "  Warning: NUT service process exited unexpectedly"
    fi
else
    echo "  Warning: NUT entrypoint not found at /app/nut/entrypoint.sh"
fi

# 启动后端服务（前台运行）
echo ""
echo "Starting Backend service..."
cd /app
export PYTHONPATH="/app:${PYTHONPATH}"
export STATIC_FILES_DIR="/app/frontend/dist"

echo "  Backend starting on http://0.0.0.0:8000"
exec python3 -m uvicorn backend.src.main:app --host 0.0.0.0 --port 8000
