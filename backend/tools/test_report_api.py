#!/usr/bin/env python3
"""测试电池测试报告 API"""
import requests
import time

API_BASE = "http://localhost:8000"
TOKEN = "dev-token-123"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

print("=" * 60)
print("测试电池测试报告功能")
print("=" * 60)

# 1. 先获取当前报告（可能没有测试类型）
print("\n1. 获取当前测试报告...")
try:
    r = requests.get(f"{API_BASE}/api/ups/test-report", headers=headers, timeout=10)
    if r.status_code == 200:
        report = r.json()
        test_info = report.get('test_info', {})
        print(f"   测试结果: {test_info.get('result')}")
        print(f"   测试类型: {test_info.get('type_label', '未记录')}")
        print(f"   开始时间: {test_info.get('started_at', '未记录')}")
    else:
        print(f"   错误: {r.status_code} - {r.text}")
except Exception as e:
    print(f"   异常: {e}")

# 2. 获取历史报告列表
print("\n2. 获取历史报告列表...")
try:
    r = requests.get(f"{API_BASE}/api/ups/test-reports?limit=5", headers=headers, timeout=10)
    if r.status_code == 200:
        data = r.json()
        reports = data.get('reports', [])
        print(f"   找到 {len(reports)} 个历史报告")
        for report in reports[:3]:
            print(f"   - #{report['id']}: {report['test_type_label']} - {report['result']} ({report['started_at'][:19]})")
    else:
        print(f"   错误: {r.status_code} - {r.text}")
except Exception as e:
    print(f"   异常: {e}")

# 3. 执行快速测试
print("\n3. 执行快速电池测试...")
try:
    r = requests.post(f"{API_BASE}/api/ups/test-battery/quick", headers=headers, timeout=10)
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        print(f"   Response: {r.json()}")
    else:
        print(f"   Error: {r.text}")
except Exception as e:
    print(f"   异常: {e}")

# 4. 等待测试完成
print("\n4. 等待 20 秒让测试完成...")
time.sleep(20)

# 5. 再次获取历史报告
print("\n5. 获取更新后的历史报告...")
try:
    r = requests.get(f"{API_BASE}/api/ups/test-reports?limit=5", headers=headers, timeout=10)
    if r.status_code == 200:
        data = r.json()
        reports = data.get('reports', [])
        print(f"   找到 {len(reports)} 个历史报告")
        if reports:
            latest = reports[0]
            print(f"\n   最新报告详情:")
            print(f"   - ID: #{latest['id']}")
            print(f"   - 类型: {latest['test_type_label']}")
            print(f"   - 结果: {latest['result']} - {latest.get('result_text', 'N/A')}")
            print(f"   - 时长: {latest.get('duration_seconds', 'N/A')} 秒")
            print(f"   - 开始电量: {latest.get('start_data', {}).get('battery_charge', 'N/A')}%")
            print(f"   - 结束电量: {latest.get('end_data', {}).get('battery_charge', 'N/A')}%")
            print(f"   - 电量变化: {latest.get('charge_change', 'N/A')}")
            print(f"   - 采样点数: {latest.get('sample_count', 0)}")
    else:
        print(f"   错误: {r.status_code} - {r.text}")
except Exception as e:
    print(f"   异常: {e}")

print("\n" + "=" * 60)
print("测试完成!")
print("=" * 60)

