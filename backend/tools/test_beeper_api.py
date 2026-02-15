#!/usr/bin/env python3
"""测试蜂鸣器 API"""
import requests
import time

API_BASE = "http://localhost:8000"
TOKEN = "dev-token-123"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

print("测试蜂鸣器 API...")
print("=" * 50)

# 测试 beeper.on
print("\n1. 发送 beeper.on 命令...")
try:
    r = requests.post(
        f"{API_BASE}/api/ups/command",
        json={"command": "beeper.on"},
        headers=headers,
        timeout=10
    )
    print(f"   Status: {r.status_code}")
    print(f"   Response: {r.text}")
except Exception as e:
    print(f"   Error: {e}")

# 等待 2 秒
print("\n2. 等待 2 秒...")
time.sleep(2)

# 测试 beeper.off
print("\n3. 发送 beeper.off 命令...")
try:
    r = requests.post(
        f"{API_BASE}/api/ups/command",
        json={"command": "beeper.off"},
        headers=headers,
        timeout=10
    )
    print(f"   Status: {r.status_code}")
    print(f"   Response: {r.text}")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "=" * 50)
print("测试完成!")

