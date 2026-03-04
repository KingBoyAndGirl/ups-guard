# Build stage
FROM ghcr.io/astral-sh/uv:0.6-python3.11-bookworm-slim AS builder

WORKDIR /app

# 1️⃣ 先只复制依赖声明文件（利用 Docker 缓存）
COPY pyproject.toml ./

# 2️⃣ 先安装依赖（代码没变时这一层会命中缓存）
RUN uv pip install --system -r pyproject.toml

# 3️⃣ 再复制源代码（代码变更不会触发重新安装依赖）
COPY src ./src

# Runtime stage
FROM python:3.11-slim


WORKDIR /app

# 从 builder 阶段复制已安装的依赖
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用代码
COPY src ./src
COPY tools ./tools

# 版本号通过 ARG 在构建时注入，然后设置为 ENV 供运行时使用
ARG APP_VERSION=0.0.0
ENV APP_VERSION=${APP_VERSION}

# 创建数据目录
RUN mkdir -p /data

# 设置非 root 用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app /data
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 启动应用
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
