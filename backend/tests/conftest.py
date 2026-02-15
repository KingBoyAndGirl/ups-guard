"""pytest fixtures for UPS Guard tests

重要：所有测试必须使用 Mock 模式
-------------------------------
为了确保测试的安全性、可重复性和独立性，所有测试用例必须：
1. 使用 Mock 对象避免实际的网络连接（SSH、HTTP等）
2. 使用 dry_run 或 mock test_mode，禁止使用 production 模式
3. 不执行实际的系统命令（如关机、重启等）
4. 不依赖外部服务（数据库、API等）

所有 fixtures 提供的对象都是 Mock 对象，不会执行实际操作。
"""
import asyncio
import tempfile
import pytest
import pytest_asyncio
import aiosqlite
from pathlib import Path
import importlib
import sys

# 添加 src 到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 自动导入所有插件以触发注册
plugins_dir = Path(__file__).parent.parent / "src" / "plugins"
if plugins_dir.exists():
    for plugin_file in plugins_dir.glob("*.py"):
        if plugin_file.stem not in ["__init__", "base", "registry"]:
            try:
                importlib.import_module(f"plugins.{plugin_file.stem}")
            except Exception as e:
                print(f"Warning: Failed to import plugin {plugin_file.stem}: {e}")

from models import Config
from services.nut_client import MockNutClient
from services.lzc_shutdown import MockShutdown


@pytest.fixture
def event_loop():
    """创建事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def temp_db():
    """创建临时数据库"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    # 初始化数据库
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    
    # 创建表
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        )
    """)
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            battery_charge REAL,
            battery_runtime INTEGER,
            input_voltage REAL,
            output_voltage REAL,
            load_percent REAL,
            temperature REAL
        )
    """)
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await conn.commit()
    
    # 创建包装类以提供与Database类兼容的接口
    class DatabaseWrapper:
        def __init__(self, conn):
            self.conn = conn
        
        async def execute(self, query: str, params: tuple = ()):
            cursor = await self.conn.execute(query, params)
            await self.conn.commit()
            return cursor
        
        async def fetch_one(self, query: str, params: tuple = ()):
            async with self.conn.execute(query, params) as cursor:
                return await cursor.fetchone()
        
        async def fetch_all(self, query: str, params: tuple = ()):
            async with self.conn.execute(query, params) as cursor:
                return await cursor.fetchall()
        
        async def commit(self):
            await self.conn.commit()
    
    db = DatabaseWrapper(conn)
    
    yield db
    
    await conn.close()
    Path(db_path).unlink()


@pytest.fixture
def mock_nut_client():
    """创建 Mock NUT 客户端"""
    return MockNutClient(
        host="localhost",
        port=3493,
        username="test",
        password="test",
        ups_name="ups"
    )


class TestMockShutdown:
    """测试用的 Mock 关机客户端，添加了 shutdown_called 追踪"""
    
    def __init__(self, socket_path: str = None):
        self.shutdown_called = False
        self.reboot_called = False
    
    async def shutdown(self) -> bool:
        """模拟关机"""
        self.shutdown_called = True
        return True
    
    async def reboot(self) -> bool:
        """模拟重启"""
        self.reboot_called = True
        return True


@pytest.fixture
def mock_shutdown_client():
    """创建 Mock 关机客户端"""
    return TestMockShutdown()


@pytest.fixture
def test_config():
    """测试配置"""
    return Config(
        shutdown_wait_minutes=1,
        shutdown_battery_percent=20,
        shutdown_final_wait_seconds=5,
        estimated_runtime_threshold=3,
        notify_channels=[],
        notify_events=["POWER_LOST", "POWER_RESTORED"],
        sample_interval_seconds=10,
        history_retention_days=7
    )
