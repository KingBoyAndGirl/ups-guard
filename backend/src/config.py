"""配置管理模块"""
import json
import logging
import secrets
from pathlib import Path
from typing import Optional, Any
from pydantic_settings import BaseSettings
from models import Config

logger = logging.getLogger(__name__)

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
        """Get API token or generate a random one"""
        if self.api_token:
            return self.api_token
        
        # Generate random token
        token = secrets.token_urlsafe(32)
        logger.warning("=" * 80)
        logger.warning("API_TOKEN not set. Generated random token:")
        logger.warning(f"  {token}")
        logger.warning("Please save this token and set it as API_TOKEN environment variable")
        logger.warning("All API requests must include: Authorization: Bearer <token>")
        logger.warning("=" * 80)
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
