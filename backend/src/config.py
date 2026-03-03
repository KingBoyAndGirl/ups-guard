"""配置管理模块"""
import json
import logging
import os
import secrets
from pathlib import Path
from typing import Optional, Any
from pydantic_settings import BaseSettings
from models import Config

logger = logging.getLogger(__name__)

# 版本号：优先从环境变量 APP_VERSION 读取（Dockerfile 构建时注入），回退到默认值
APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")

# 确定项目根目录（backend/src -> backend -> 项目根目录）
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# 确保 data 目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)

# .env 文件路径
ENV_FILE = BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    """环境变量配置"""
    # NUT 配置
    nut_host: str = "nut-server"
    nut_port: int = 3493
    nut_username: str = "monuser"
    nut_password: str = "monuser"
    nut_ups_name: str = ""  # 留空则自动发现

    # 数据库 (默认为项目根目录下的 data 文件夹)
    database_path: str = str(DATA_DIR / "ups_guard.db")

    # 日志
    log_level: str = "INFO"
    
    # Mock 模式
    mock_mode: bool = False
    
    # gRPC socket
    lzc_grpc_socket: str = "/lzcapp/run/sys/lzc-apis.socket"
    
    # 安全配置
    api_token: str = ""  # API Token for authentication, auto-generated if empty
    encryption_key: str = ""  # Encryption key for sensitive data
    allowed_origins: str = ""  # Comma-separated list of allowed origins for CORS
    
    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = 'utf-8'
        case_sensitive = False
    
    def get_or_generate_api_token(self) -> str:
        """
        获取 API Token，优先级：
        1. 持久化文件（/data/.api_token）—— 支持 Web 修改后跨部署保持
        2. 环境变量 API_TOKEN
        3. 自动生成并持久化
        """
        # 1. 尝试从持久化文件读取
        token_from_file = _read_persisted_token()
        if token_from_file:
            # 同步到内存，后续不再读文件
            self.api_token = token_from_file
            return token_from_file

        # 2. 环境变量中有设置
        if self.api_token:
            # 将环境变量中的 Token 同步到持久化文件
            _write_persisted_token(self.api_token)
            return self.api_token

        # 3. 都没有，自动生成
        token = secrets.token_urlsafe(32)
        logger.warning("=" * 80)
        logger.warning("API_TOKEN not set. Generated random token:")
        logger.warning(f"  {token}")
        logger.warning("Token has been persisted to data directory")
        logger.warning("=" * 80)

        # 持久化并更新内存
        _write_persisted_token(token)
        self.api_token = token
        return token


settings = Settings()

# 解析数据库路径（支持相对路径）
def resolve_database_path(path: str) -> str:
    """
    解析数据库路径，支持相对路径
    - 绝对路径直接使用
    - 相对路径相对于项目根目录（backend 的父目录）解析
    """
    p = Path(path)
    if p.is_absolute():
        return str(p)
    else:
        # 相对路径，相对于项目根目录
        resolved = (PROJECT_ROOT / path).resolve()
        return str(resolved)

# 解析后的数据库路径
settings.database_path = resolve_database_path(settings.database_path)

# 确保数据库目录存在
db_dir = Path(settings.database_path).parent
db_dir.mkdir(parents=True, exist_ok=True)

# 启动时打印关键配置（调试用）
logger.info(f"Loaded settings from: {ENV_FILE}")
logger.info(f"NUT_HOST: {settings.nut_host}")
logger.info(f"NUT_PORT: {settings.nut_port}")
logger.info(f"NUT_UPS_NAME: {settings.nut_ups_name or '(auto-discover)'}")
logger.info(f"DATABASE_PATH: {settings.database_path}")


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, db):
        self.db = db
        self._cache: Optional[Config] = None
    
    async def get_config(self) -> Config:
        """获取配置"""
        if self._cache is None:
            await self._load_config()
        return self._cache
    
    async def _load_config(self):
        """从数据库加载配置"""
        config_dict = {}
        rows = await self.db.fetch_all("SELECT key, value FROM config")
        for row in rows:
            key = row['key']
            value = row['value']
            
            # 解析值类型
            if key in ['shutdown_wait_minutes', 'shutdown_battery_percent', 
                      'shutdown_final_wait_seconds', 'estimated_runtime_threshold',
                      'sample_interval_seconds', 'history_retention_days',
                      'poll_interval_seconds', 'cleanup_interval_hours', 'wol_delay_seconds',
                      'device_status_check_interval_seconds',
                      'retry_notification_max', 'retry_hook_max', 'retry_http_max',
                      'retry_wol_count', 'retry_db_max']:
                config_dict[key] = int(value)
            elif key in ['retry_notification_delay', 'retry_hook_delay', 'retry_wol_delay', 'retry_db_delay']:
                config_dict[key] = float(value)
            elif key in ['notify_channels', 'notify_events', 'pre_shutdown_hooks']:
                config_dict[key] = json.loads(value)
            elif key in ['notification_enabled', 'wol_on_power_restore', 'retry_http_exponential']:
                config_dict[key] = value.lower() in ('true', '1', 'yes')
            elif key in ['test_mode', 'shutdown_method']:
                config_dict[key] = value
            else:
                config_dict[key] = value
        
        self._cache = Config(**config_dict)

    async def update_config(self, config: Config):
        """更新配置"""
        for key, value in config.dict().items():
            if isinstance(value, (list, dict)):
                value_str = json.dumps(value)
            else:
                value_str = str(value)
            
            await self.db.execute(
                "INSERT OR REPLACE INTO config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (key, value_str)
            )
        
        self._cache = config

    async def get_value(self, key: str, default: Any = None) -> Any:
        """获取单个配置项"""
        config = await self.get_config()
        return getattr(config, key, default)
    
    async def set_value(self, key: str, value: Any):
        """设置单个配置项"""
        config = await self.get_config()
        setattr(config, key, value)
        await self.update_config(config)


# 全局配置管理器实例
config_manager: Optional[ConfigManager] = None


async def get_config_manager() -> ConfigManager:
    """获取配置管理器实例"""
    global config_manager
    if config_manager is None:
        from db.database import get_db
        db = await get_db()
        config_manager = ConfigManager(db)
    return config_manager


# ---------- Token 持久化文件操作 ---------- #

def _get_token_file_path() -> Path:
    """
    获取 Token 持久化文件路径。
    优先使用 /data 目录（懒猫挂载的持久化卷），
    回退到 DATA_DIR（本地开发环境）。
    """
    # 从 DATABASE_PATH 推断 data 目录
    db_path = os.environ.get("DATABASE_PATH", "")
    if db_path:
        data_dir = Path(db_path).parent
        if data_dir != Path(".") and (data_dir.exists() or data_dir.parent.exists()):
            return data_dir / ".api_token"

    # 回退到项目 data 目录
    return DATA_DIR / ".api_token"


def _read_persisted_token() -> str | None:
    """从持久化文件读取 Token，不存在或为空则返回 None"""
    token_file = _get_token_file_path()
    if token_file.exists():
        token = token_file.read_text(encoding="utf-8").strip()
        if token:
            logger.debug(f"Loaded API Token from {token_file}")
            return token
    return None


def _write_persisted_token(token: str) -> None:
    """将 Token 写入持久化文件"""
    token_file = _get_token_file_path()
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(token + "\n", encoding="utf-8")
    # 设置文件权限为仅 owner 可读写（安全）
    try:
        token_file.chmod(0o600)
    except OSError:
        pass  # Windows 或权限受限环境下忽略
    logger.info(f"API Token persisted to {token_file}")


def persist_api_token(new_token: str) -> None:
    """
    持久化 API Token（供 Web UI 修改 Token 时调用）。

    写入持久化文件 + 同步更新 settings 内存。
    同时保持 .env 兼容（本地开发环境）。
    """
    # 1. 写入持久化文件（主要）
    _write_persisted_token(new_token)

    # 2. 同步更新 settings 实例
    settings.api_token = new_token

    # 3. 同时写入 .env 文件（兼容本地开发环境）
    _persist_to_env_file(new_token)

    logger.info("API Token updated and persisted")


def _persist_to_env_file(new_token: str) -> None:
    """将 Token 写入 .env 文件（兼容本地开发环境）"""
    env_path = ENV_FILE
    lines: list[str] = []

    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines(keepends=True)

    found = False
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("API_TOKEN=") or stripped.startswith("API_TOKEN ="):
            lines[i] = f"API_TOKEN={new_token}\n"
            found = True
            break

    if not found:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append(f"API_TOKEN={new_token}\n")

    try:
        env_path.write_text("".join(lines), encoding="utf-8")
    except OSError as e:
        logger.debug(f"Failed to write .env file (expected in container): {e}")

