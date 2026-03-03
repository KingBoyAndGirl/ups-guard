"""本地配置管理"""
import json
import uuid
import socket
from dataclasses import dataclass, asdict
from pathlib import Path


CONFIG_DIR = Path.home() / ".ups-guard-agent"
CONFIG_FILE = CONFIG_DIR / "config.json"

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
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls) -> "AgentConfig":
        """从文件加载配置"""
        if not CONFIG_FILE.exists():
            return cls(
                agent_id=cls.generate_agent_id(),
                agent_name=socket.gethostname(),
            )
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)
