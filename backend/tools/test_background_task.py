#!/usr/bin/env python3
"""测试后台任务是否正常运行"""
import requests
import time

API_BASE = "http://localhost:8000"
headers = {"Authorization": "Bearer dev-token-123", "Content-Type": "application/json"}

print("=" * 50)
print("测试后台监控任务")
print("=" * 50)

# 1. 触发快速测试
print("\n1. 触发快速测试...")
r = requests.post(f"{API_BASE}/api/ups/test-battery/quick", headers=headers)
print(f"   响应: {r.status_code} - {r.json()}")

# 2. 每隔 3 秒检查一次，共检查 10 次
for i in range(10):
    time.sleep(3)
    print(f"\n{i+1}. 等待 {(i+1)*3} 秒后检查...")
    
    r = requests.get(f"{API_BASE}/api/ups/test-reports?limit=1", headers=headers)
    reports = r.json().get('reports', [])
    
    if reports:
        latest = reports[0]
        print(f"   ID: #{latest['id']}")
        print(f"   结果: {latest['result']}")
        print(f"   采样点: {latest['sample_count']}")
        
        # 如果测试完成，退出
        if latest['result'] != 'in_progress':
            print(f"\n测试已完成: {latest['result']}")
            print(f"测试时长: {latest.get('duration_seconds')} 秒")
            print(f"开始电量: {latest.get('start_data', {}).get('battery_charge')}%")
            print(f"结束电量: {latest.get('end_data', {}).get('battery_charge')}%")
            break
    else:
        print("   没有报告")

print("\n" + "=" * 50)
print("测试结束")
print("=" * 50)

