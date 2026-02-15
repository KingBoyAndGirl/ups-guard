# Build stage
FROM python:3.11-slim as builder

# 安装 uv
RUN pip install --no-cache-dir uv

WORKDIR /app

# 复制项目文件
COPY pyproject.toml ./
COPY src ./src

# 使用 uv 安装依赖到临时目录
RUN uv pip install --system -r pyproject.toml

# Runtime stage
FROM python:3.11-slim

# 安装 curl 用于健康检查
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 从 builder 阶段复制已安装的依赖
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用代码
COPY src ./src

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
