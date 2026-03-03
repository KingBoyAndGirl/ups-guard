"""本地配置管理"""
import json
import uuid
import socket
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


CONFIG_DIR = Path.home() / ".ups-guard-agent"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class AgentConfig:
    """Agent 配置"""
    server_url: str = ""
    token: str = ""
    agent_id: str = ""
    agent_name: str = ""

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
                agent_id=str(uuid.uuid4())[:12],
                agent_name=socket.gethostname(),
            )
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)
