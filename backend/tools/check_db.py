#!/usr/bin/env python3
"""检查数据库状态"""
import sqlite3

conn = sqlite3.connect('../data/ups_guard.db')
cursor = conn.cursor()

# 列出所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables:', [t[0] for t in tables])

# 检查 battery_test_reports 表是否存在
if ('battery_test_reports',) in tables:
    cursor.execute("SELECT * FROM battery_test_reports ORDER BY id DESC LIMIT 5")
    rows = cursor.fetchall()
    print(f'\nBattery Test Reports: {len(rows)} rows')
    for row in rows:
        print(row)
else:
    print('\nTable battery_test_reports does not exist!')

conn.close()

