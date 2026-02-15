#!/usr/bin/env python3
"""快速检查 UPS 测试状态"""
import asyncio

async def main():
    r, w = await asyncio.open_connection('localhost', 3493)

    async def cmd(c):
        w.write(f'{c}\n'.encode())
        await w.drain()
        result = []
        while True:
            line = await asyncio.wait_for(r.readline(), timeout=2)
            s = line.decode().strip()
            if s.startswith('END') or s.startswith('ERR'):
                break
            result.append(s)
        return result

    ups_list = await cmd('LIST UPS')
    if not ups_list:
        print("无法获取 UPS 列表")
        return

    # 找到 UPS 行 (跳过 BEGIN)
    ups = None
    for line in ups_list:
        parts = line.split()
        if len(parts) >= 2 and parts[0] == 'UPS':
            ups = parts[1]
            break

    if not ups:
        print(f"无法解析 UPS 名称: {ups_list}")
        return

    vars_to_check = ['ups.status', 'ups.test.result', 'ups.beeper.status', 'battery.charge']

    print(f'UPS: {ups}')
    print('-' * 40)
    for v in vars_to_check:
        res = await cmd(f'GET VAR {ups} {v}')
        if res:
            # 格式: VAR <ups> <var> "<value>"
            line = res[0]
            if '"' in line:
                val = line.split('"')[1]
            else:
                val = line
        else:
            val = 'N/A'
        print(f'{v}: {val}')
    w.close()

if __name__ == '__main__':
    asyncio.run(main())

