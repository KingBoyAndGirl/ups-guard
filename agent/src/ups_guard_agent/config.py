"""本地配置管理"""
import json
import logging
import uuid
import socket
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_app_dir() -> Path:
    """获取应用数据目录（exe 所在目录 / 当前工作目录）"""
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后，使用 exe 所在目录
        return Path(sys.executable).parent
    # 源码运行，使用当前工作目录
    return Path.cwd()


APP_DIR = _get_app_dir()
CONFIG_FILE = APP_DIR / "ups-guard-agent.json"
STATUS_FILE = APP_DIR / "ups-guard-agent-status.json"
LOG_DIR = APP_DIR / "logs"

# 日志保留策略
LOG_MAX_FILES = 10          # 最多保留的日志文件数量
LOG_MAX_AGE_DAYS = 7        # 日志文件最大保留天数
LOG_MAX_SIZE_MB = 5         # 单个日志文件最大大小（MB）


def get_log_file() -> Path:
    """生成带时间戳的日志文件路径，每次启动使用新文件"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return LOG_DIR / f"agent_{timestamp}.log"


def cleanup_old_logs() -> None:
    """清理旧日志文件：按数量和天数两个维度清理"""
    if not LOG_DIR.exists():
        return

    log_files = sorted(
        LOG_DIR.glob("agent_*.log"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,  # 最新的在前
    )

    now = datetime.now()
    kept = 0

    for f in log_files:
        # 超过最大保留数量，删除
        if kept >= LOG_MAX_FILES:
            try:
                f.unlink()
                logger.debug(f"已删除旧日志（超出数量限制）: {f.name}")
            except Exception:
                pass
            continue

        # 超过最大保留天数，删除
        try:
            from datetime import timedelta
            file_age = now - datetime.fromtimestamp(f.stat().st_mtime)
            if file_age > timedelta(days=LOG_MAX_AGE_DAYS):
                f.unlink()
                logger.debug(f"已删除旧日志（超出 {LOG_MAX_AGE_DAYS} 天）: {f.name}")
                continue
        except Exception:
            pass

        kept += 1

    # 同时清理旧版的单文件日志（如果存在）
    legacy_log = APP_DIR / "ups-guard-agent.log"
    if legacy_log.exists():
        try:
            legacy_log.unlink()
        except Exception:
            pass

# Agent ID 统一长度（UUID 前 12 位，含连字符，如 887bb0c1-89f）
_AGENT_ID_LENGTH = 12


@dataclass
class AgentConfig:
    """Agent 配置"""
    server_url: str = ""
    token: str = ""
    agent_id: str = ""
    agent_name: str = ""

    @staticmethod
    def generate_agent_id() -> str:
        """生成 Agent ID（统一使用此方法，避免长度不一致）"""
        return str(uuid.uuid4())[:_AGENT_ID_LENGTH]

    def save(self):
        """保存配置到文件"""
        APP_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)
        masked_token = (self.token[:4] + "****") if self.token else ""
        logger.info(
            f"配置已保存到 {CONFIG_FILE}: server_url={self.server_url} "
            f"agent_id={self.agent_id} agent_name={self.agent_name} token={masked_token}"
        )

    @classmethod
    def load(cls) -> "AgentConfig":
        """从文件加载配置"""
        logger.info(f"正在加载配置: {CONFIG_FILE}")
        if not CONFIG_FILE.exists():
            # 兼容旧版：尝试从 ~/.ups-guard-agent/config.json 迁移
            old_config = Path.home() / ".ups-guard-agent" / "config.json"
            if old_config.exists():
                logger.info(f"正在迁移旧配置: {old_config} -> {CONFIG_FILE}")
                try:
                    with open(old_config, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    cfg = cls(**data)
                    cfg.save()
                    return cfg
                except Exception as e:
                    logger.warning(f"迁移旧配置失败: {e}")

            logger.info("未找到配置文件，创建默认配置")
            return cls(
                agent_id=cls.generate_agent_id(),
                agent_name=socket.gethostname(),
            )
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg = cls(**data)
        masked_token = (cfg.token[:4] + "****") if cfg.token else ""
        logger.info(
            f"配置已加载: server_url={cfg.server_url} agent_id={cfg.agent_id} "
            f"agent_name={cfg.agent_name} token={masked_token}"
        )
        return cfg
