#!/usr/bin/env python3
"""查看最新报告"""
import requests
import json

headers = {'Authorization': 'Bearer dev-token-123'}
r = requests.get('http://localhost:8000/api/ups/test-reports?limit=1', headers=headers)
report = r.json()['reports'][0]

print("最新测试报告:")
print(f"  ID: {report['id']}")
print(f"  类型: {report['test_type_label']}")
print(f"  结果: {report['result']} - {report['result_text']}")
print(f"  时长: {report['duration_seconds']} 秒")
print(f"  开始电量: {report['start_data']['battery_charge']}%")
print(f"  结束电量: {report['end_data']['battery_charge']}%")
print(f"  电量变化: {report['charge_change']}%")
print(f"  采样点: {report['sample_count']}")
print(f"  UPS: {report['ups_info']['model']}")

print("\n采样数据预览（前5个）:")
for i, sample in enumerate(report['samples'][:5]):
    print(f"  {i+1}. {sample['timestamp'][-8:]}: {sample['battery_charge']}%")

