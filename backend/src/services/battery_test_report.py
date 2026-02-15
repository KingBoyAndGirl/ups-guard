"""电池测试报告服务"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# 全局变量：当前正在进行的测试
_current_test: Optional[Dict[str, Any]] = None
_test_samples: List[Dict[str, Any]] = []
_sampling_task: Optional[asyncio.Task] = None


class BatteryTestReportService:
    """电池测试报告服务"""

    def __init__(self, db):
        self.db = db

    async def start_test(self, test_type: str, test_type_label: str, ups_data: Dict[str, Any]) -> int:
        """
        开始一个新的电池测试

        返回: 测试报告 ID
        """
        global _current_test, _test_samples

        now = datetime.now(timezone.utc)

        # 插入新报告记录
        cursor = await self.db.execute(
            """
            INSERT INTO battery_test_reports (
                test_type, test_type_label, started_at, result,
                start_battery_charge, start_battery_voltage, start_battery_runtime,
                start_load_percent, start_input_voltage,
                ups_manufacturer, ups_model, ups_serial
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                test_type,
                test_type_label,
                now.isoformat(),
                'in_progress',
                ups_data.get('battery_charge'),
                ups_data.get('battery_voltage'),
                ups_data.get('battery_runtime'),
                ups_data.get('load_percent'),
                ups_data.get('input_voltage'),
                ups_data.get('ups_manufacturer'),
                ups_data.get('ups_model'),
                ups_data.get('ups_serial'),
            )
        )
        await self.db.conn.commit()

        report_id = cursor.lastrowid

        # 设置当前测试
        _current_test = {
            'id': report_id,
            'test_type': test_type,
            'started_at': now,
        }
        _test_samples = [{
            'timestamp': now.isoformat(),
            'battery_charge': ups_data.get('battery_charge'),
            'battery_voltage': ups_data.get('battery_voltage'),
            'battery_runtime': ups_data.get('battery_runtime'),
        }]

        logger.info(f"Started battery test report #{report_id} ({test_type_label})")
        return report_id

    async def add_sample(self, ups_data: Dict[str, Any]):
        """添加采样数据"""
        global _test_samples

        if _current_test is None:
            return

        now = datetime.now(timezone.utc)
        _test_samples.append({
            'timestamp': now.isoformat(),
            'battery_charge': ups_data.get('battery_charge'),
            'battery_voltage': ups_data.get('battery_voltage'),
            'battery_runtime': ups_data.get('battery_runtime'),
        })

    async def complete_test(self, result: str, result_text: str, ups_data: Dict[str, Any]) -> Optional[int]:
        """
        完成电池测试

        返回: 测试报告 ID，如果没有正在进行的测试返回 None
        """
        global _current_test, _test_samples

        if _current_test is None:
            logger.warning("No battery test in progress")
            return None

        report_id = _current_test['id']
        started_at = _current_test['started_at']
        now = datetime.now(timezone.utc)
        duration = int((now - started_at).total_seconds())

        # 添加最后一个采样点
        _test_samples.append({
            'timestamp': now.isoformat(),
            'battery_charge': ups_data.get('battery_charge'),
            'battery_voltage': ups_data.get('battery_voltage'),
            'battery_runtime': ups_data.get('battery_runtime'),
        })

        # 更新报告
        await self.db.execute(
            """
            UPDATE battery_test_reports SET
                completed_at = ?,
                duration_seconds = ?,
                result = ?,
                result_text = ?,
                end_battery_charge = ?,
                end_battery_voltage = ?,
                end_battery_runtime = ?,
                end_load_percent = ?,
                end_input_voltage = ?,
                samples = ?
            WHERE id = ?
            """,
            (
                now.isoformat(),
                duration,
                result,
                result_text,
                ups_data.get('battery_charge'),
                ups_data.get('battery_voltage'),
                ups_data.get('battery_runtime'),
                ups_data.get('load_percent'),
                ups_data.get('input_voltage'),
                json.dumps(_test_samples),
                report_id,
            )
        )
        await self.db.conn.commit()

        logger.info(f"Completed battery test report #{report_id}: {result}")

        # 清除当前测试
        _current_test = None
        _test_samples = []

        return report_id

    async def cancel_test(self) -> Optional[int]:
        """取消当前测试"""
        global _current_test, _test_samples

        if _current_test is None:
            return None

        report_id = _current_test['id']
        now = datetime.now(timezone.utc)
        started_at = _current_test['started_at']
        duration = int((now - started_at).total_seconds())

        await self.db.execute(
            """
            UPDATE battery_test_reports SET
                completed_at = ?,
                duration_seconds = ?,
                result = ?,
                result_text = ?,
                samples = ?
            WHERE id = ?
            """,
            (
                now.isoformat(),
                duration,
                'cancelled',
                '测试已取消',
                json.dumps(_test_samples),
                report_id,
            )
        )
        await self.db.conn.commit()

        logger.info(f"Cancelled battery test report #{report_id}")

        _current_test = None
        _test_samples = []

        return report_id

    async def get_current_test(self) -> Optional[Dict[str, Any]]:
        """获取当前正在进行的测试"""
        return _current_test

    async def get_report(self, report_id: int) -> Optional[Dict[str, Any]]:
        """获取单个测试报告"""
        row = await self.db.fetch_one(
            "SELECT * FROM battery_test_reports WHERE id = ?",
            (report_id,)
        )

        if not row:
            return None

        return self._row_to_report(row)

    async def get_reports(
        self,
        limit: int = 20,
        test_type: Optional[str] = None,
        result: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取测试报告列表，支持筛选"""
        # 构建查询
        query = "SELECT * FROM battery_test_reports WHERE 1=1"
        params = []

        # 测试类型筛选
        if test_type:
            query += " AND test_type = ?"
            params.append(test_type)

        # 结果筛选
        if result:
            query += " AND result = ?"
            params.append(result)

        # 开始日期筛选
        if start_date:
            query += " AND started_at >= ?"
            params.append(f"{start_date}T00:00:00")

        # 结束日期筛选
        if end_date:
            query += " AND started_at <= ?"
            params.append(f"{end_date}T23:59:59")

        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        rows = await self.db.fetch_all(query, tuple(params))

        return [self._row_to_report(row) for row in rows]

    async def get_latest_report(self) -> Optional[Dict[str, Any]]:
        """获取最新的测试报告"""
        row = await self.db.fetch_one(
            "SELECT * FROM battery_test_reports ORDER BY started_at DESC LIMIT 1"
        )

        if not row:
            return None

        return self._row_to_report(row)

    def _row_to_report(self, row) -> Dict[str, Any]:
        """将数据库行转换为报告字典"""
        samples = []
        if row['samples']:
            try:
                samples = json.loads(row['samples'])
            except:
                pass

        # 计算电量变化
        charge_change = None
        if row['start_battery_charge'] is not None and row['end_battery_charge'] is not None:
            charge_change = row['end_battery_charge'] - row['start_battery_charge']

        return {
            'id': row['id'],
            'test_type': row['test_type'],
            'test_type_label': row['test_type_label'],
            'started_at': row['started_at'],
            'completed_at': row['completed_at'],
            'duration_seconds': row['duration_seconds'],
            'result': row['result'],
            'result_text': row['result_text'],
            'start_data': {
                'battery_charge': row['start_battery_charge'],
                'battery_voltage': row['start_battery_voltage'],
                'battery_runtime': row['start_battery_runtime'],
                'load_percent': row['start_load_percent'],
                'input_voltage': row['start_input_voltage'],
            },
            'end_data': {
                'battery_charge': row['end_battery_charge'],
                'battery_voltage': row['end_battery_voltage'],
                'battery_runtime': row['end_battery_runtime'],
                'load_percent': row['end_load_percent'],
                'input_voltage': row['end_input_voltage'],
            },
            'charge_change': charge_change,
            'ups_info': {
                'manufacturer': row['ups_manufacturer'],
                'model': row['ups_model'],
                'serial': row['ups_serial'],
            },
            'samples': samples,
            'sample_count': len(samples),
        }


# 全局服务实例
_report_service: Optional[BatteryTestReportService] = None


async def get_battery_test_report_service() -> BatteryTestReportService:
    """获取电池测试报告服务实例"""
    global _report_service
    if _report_service is None:
        from db.database import get_db
        db = await get_db()
        _report_service = BatteryTestReportService(db)
    return _report_service

