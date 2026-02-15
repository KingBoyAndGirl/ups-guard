"""数据库管理模块"""
import aiosqlite
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Database:
    """数据库管理类"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None
    
    async def connect(self):
        """连接数据库"""
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        
        # 启用 WAL 模式以提高并发性能
        await self.conn.execute("PRAGMA journal_mode=WAL")
        
        # 减少 fsync 开销
        await self.conn.execute("PRAGMA synchronous=NORMAL")

        
        # 初始化数据库结构
        await self._init_schema()
        
        # 完整性检查
        await self._integrity_check()
    
    async def close(self):
        """关闭数据库连接"""
        if self.conn:
            await self.conn.close()
    
    async def _init_schema(self):
        """初始化数据库结构"""
        schema_file = Path(__file__).parent / "schema.sql"
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema = f.read()
        
        await self.conn.executescript(schema)
        await self.conn.commit()

        # Run migrations
        await self._run_migrations()
    
    async def _run_migrations(self):
        """运行数据库迁移"""
        try:
            # Migration 1: Add test_mode column to events table if it doesn't exist
            cursor = await self.conn.execute("PRAGMA table_info(events)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'test_mode' not in column_names:
                await self.conn.execute("ALTER TABLE events ADD COLUMN test_mode TEXT DEFAULT 'production'")
                await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_events_test_mode ON events(test_mode)")
                await self.conn.commit()

            # Migration 2: Add test_mode column to metrics table if it doesn't exist
            cursor = await self.conn.execute("PRAGMA table_info(metrics)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'test_mode' not in column_names:
                await self.conn.execute("ALTER TABLE metrics ADD COLUMN test_mode TEXT DEFAULT 'production'")
                await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_test_mode ON metrics(test_mode)")
                await self.conn.commit()

            # Migration 3: Create battery_test_reports table if it doesn't exist
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS battery_test_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_type TEXT NOT NULL,
                    test_type_label TEXT NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    duration_seconds INTEGER,
                    result TEXT,
                    result_text TEXT,
                    start_battery_charge REAL,
                    start_battery_voltage REAL,
                    start_battery_runtime INTEGER,
                    start_load_percent REAL,
                    start_input_voltage REAL,
                    end_battery_charge REAL,
                    end_battery_voltage REAL,
                    end_battery_runtime INTEGER,
                    end_load_percent REAL,
                    end_input_voltage REAL,
                    ups_manufacturer TEXT,
                    ups_model TEXT,
                    ups_serial TEXT,
                    samples TEXT,
                    metadata TEXT
                )
            """)
            await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_battery_test_reports_started_at ON battery_test_reports(started_at)")
            await self.conn.commit()

            # Migration 4: Create monitoring_stats table if it doesn't exist
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL UNIQUE,
                    monitoring_mode TEXT NOT NULL,
                    event_mode_active BOOLEAN DEFAULT 0,
                    communication_count INTEGER DEFAULT 0,
                    avg_response_time_ms REAL,
                    min_response_time_ms REAL,
                    max_response_time_ms REAL,
                    uptime_seconds INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_monitoring_stats_date ON monitoring_stats(date)")
            await self.conn.commit()

        except Exception as e:
            logger.error(f"Error during migrations: {e}")
    
    async def _integrity_check(self):
        """执行数据库完整性检查"""
        try:
            async with self.conn.execute("PRAGMA integrity_check") as cursor:
                result = await cursor.fetchone()
                # result 是一个 Row 对象，result[0] 是检查结果
                if result and result[0] == "ok":
                    logger.debug("Database integrity check passed")
                else:
                    logger.error(f"Database integrity check failed: {result[0] if result else 'unknown'}")
        except Exception as e:
            logger.error(f"Error during integrity check: {e}")
    
    async def execute(self, query: str, params: tuple = ()):
        """执行SQL语句"""
        async with self.conn.execute(query, params) as cursor:
            await self.conn.commit()
            return cursor
    
    async def fetch_one(self, query: str, params: tuple = ()):
        """查询单行"""
        async with self.conn.execute(query, params) as cursor:
            return await cursor.fetchone()
    
    async def fetch_all(self, query: str, params: tuple = ()):
        """查询多行"""
        async with self.conn.execute(query, params) as cursor:
            return await cursor.fetchall()
    
    async def execute_many(self, query: str, params_list: list):
        """批量执行SQL语句（使用事务）"""
        async with self.conn.execute("BEGIN"):
            try:
                for params in params_list:
                    await self.conn.execute(query, params)
                await self.conn.commit()
            except Exception as e:
                await self.conn.rollback()
                logger.error(f"Transaction failed, rolled back: {e}")
                raise


# 全局数据库实例
db: Optional[Database] = None


async def get_db() -> Database:
    """获取数据库实例"""
    global db
    if db is None:
        raise RuntimeError("Database not initialized")
    return db


async def init_db(db_path: str):
    """初始化数据库"""
    global db
    db = Database(db_path)
    await db.connect()


async def close_db():
    """关闭数据库"""
    global db
    if db:
        await db.close()
        db = None
