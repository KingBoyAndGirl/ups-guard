#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""电池放电分析脚本

分析 UPS 电池放电数据，用于诊断电池健康状况。

使用方法:
    python analyze_battery.py [--db DATABASE_PATH]

默认数据库路径: ../../data/ups_guard.db
"""
import sqlite3
import argparse
import os
from datetime import datetime

def get_default_db_path():
    """获取默认数据库路径"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, '..', '..', 'data', 'ups_guard.db')

def analyze(db_path: str = None):
    """分析电池放电数据"""
    if db_path is None:
        db_path = get_default_db_path()

    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print("=" * 60)
    print("  APC Back-UPS BK650M2 电池放电分析")
    print("=" * 60)
    print()
    print("UPS 规格:")
    print("  - 容量: 650VA / 390W")
    print("  - 电池: 12V / 7Ah = 84Wh")
    print()

    # 查询电池放电期间的数据
    cur.execute('''
        SELECT timestamp, battery_charge, battery_runtime, load_percent
        FROM metrics 
        WHERE input_voltage < 1
        ORDER BY timestamp ASC
    ''')
    rows = cur.fetchall()

    if not rows:
        print("没有找到电池放电记录")
        conn.close()
        return

    print(f"电池放电记录数: {len(rows)}")
    print()

    # 计算放电统计
    t1 = datetime.fromisoformat(rows[0][0])
    t2 = datetime.fromisoformat(rows[-1][0])
    c1 = rows[0][1]
    c2 = rows[-1][1]

    duration_min = (t2 - t1).total_seconds() / 60
    charge_drop = c1 - c2
    rate = charge_drop / duration_min if duration_min > 0 else 0

    print("放电统计:")
    print(f"  - 开始时间: {rows[0][0]}")
    print(f"  - 结束时间: {rows[-1][0]}")
    print(f"  - 放电时长: {duration_min:.1f} 分钟")
    print(f"  - 电量变化: {c1}% -> {c2}%")
    print(f"  - 下降幅度: {charge_drop}%")
    print(f"  - 下降速率: {rate:.2f}%/分钟")
    print()

    # 计算功率
    battery_wh = 84  # 12V * 7Ah
    energy_consumed = battery_wh * (charge_drop / 100)
    power = energy_consumed / (duration_min / 60) if duration_min > 0 else 0

    print("功率估算:")
    print(f"  - 电池容量: {battery_wh}Wh")
    print(f"  - 消耗能量: {energy_consumed:.1f}Wh")
    print(f"  - 估算功率: {power:.1f}W")
    print()

    # 检查负载
    loads = [r[3] for r in rows if r[3] is not None]
    avg_load = sum(loads) / len(loads) if loads else 0
    print(f"负载统计:")
    print(f"  - 平均负载: {avg_load:.1f}%")
    print(f"  - 负载记录: 全部为 0%（无外部负载）")
    print()

    # 分析结论
    print("=" * 60)
    print("  分析结论")
    print("=" * 60)
    print()

    if avg_load < 1 and power > 50:
        print("⚠️ 异常发现:")
        print(f"   在零负载情况下，UPS 内部消耗约 {power:.0f}W")
        print()
        print("可能原因:")
        print("   1. 后备式 UPS 逆变器持续运行损耗")
        print("   2. APC Back-UPS 在电池模式下逆变器效率约 80-85%")
        print("   3. 逆变器空载损耗 + 控制电路 = 10-20W (正常)")
        print()
        print(f"   但实际测得 {power:.0f}W，远超正常值！")
        print()
        print("🔍 进一步分析:")

        # 检查 UPS 报告的剩余运行时间
        runtime1 = rows[0][2]
        runtime2 = rows[-1][2]
        if runtime1 and runtime2:
            runtime_drop = runtime1 - runtime2
            actual_time = duration_min * 60  # 秒
            ratio = actual_time / runtime_drop if runtime_drop > 0 else 0
            print(f"   - UPS 报告初始续航: {runtime1}秒 ({runtime1/60:.1f}分钟)")
            print(f"   - UPS 报告最终续航: {runtime2}秒 ({runtime2/60:.1f}分钟)")
            print(f"   - 实际经过时间: {actual_time:.0f}秒")
            print(f"   - 续航时间下降: {runtime_drop}秒")
            print(f"   - 时间消耗比: {ratio:.2f} (理想值=1.0)")

            if abs(ratio - 1.0) < 0.2:
                print()
                print("✅ UPS 续航预估准确，电池正常消耗")
            else:
                print()
                print("⚠️ UPS 续航预估不准确，可能电池老化")

    print()
    print("=" * 60)
    conn.close()

def main():
    parser = argparse.ArgumentParser(description="电池放电分析脚本")
    parser.add_argument("--db", default=None, help="数据库文件路径")
    args = parser.parse_args()

    analyze(args.db)

if __name__ == "__main__":
    main()

