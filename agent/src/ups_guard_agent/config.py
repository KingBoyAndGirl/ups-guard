"""本地配置管理"""
import json
import logging
import uuid
import socket
import sys
from dataclasses import dataclass, asdict
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
LOG_FILE = APP_DIR / "ups-guard-agent.log"
STATUS_FILE = APP_DIR / "ups-guard-agent-status.json"

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
            f"Config saved to {CONFIG_FILE}: server_url={self.server_url} "
            f"agent_id={self.agent_id} agent_name={self.agent_name} token={masked_token}"
        )

    @classmethod
    def load(cls) -> "AgentConfig":
        """从文件加载配置"""
        logger.info(f"Loading config from {CONFIG_FILE}")
        if not CONFIG_FILE.exists():
            # 兼容旧版：尝试从 ~/.ups-guard-agent/config.json 迁移
            old_config = Path.home() / ".ups-guard-agent" / "config.json"
            if old_config.exists():
                logger.info(f"Migrating config from {old_config} to {CONFIG_FILE}")
                try:
                    with open(old_config, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    cfg = cls(**data)
                    cfg.save()  # 保存到新位置
                    return cfg
                except Exception as e:
                    logger.warning(f"Failed to migrate old config: {e}")

            logger.info("No config file found, creating default config")
            return cls(
                agent_id=cls.generate_agent_id(),
                agent_name=socket.gethostname(),
            )
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg = cls(**data)
        masked_token = (cfg.token[:4] + "****") if cfg.token else ""
        logger.info(
            f"Config loaded: server_url={cfg.server_url} agent_id={cfg.agent_id} "
            f"agent_name={cfg.agent_name} token={masked_token}"
        )
        return cfg
