# UPS 检测和诊断工具

本目录包含用于检测、诊断和分析 UPS 的独立脚本工具。

## 工具列表

### test_nut_parameters.py - NUT 参数测试脚本

测试 UPS 通过 NUT 协议提供的所有参数，可生成详细的 Markdown 报告。

```bash
# 基本用法（仅在终端显示）
python test_nut_parameters.py

# 自动生成报告文件（推荐）
python test_nut_parameters.py --auto-filename

# 指定输出文件
python test_nut_parameters.py --output report.md

# 测试所有 NUT 标准变量
python test_nut_parameters.py --test-all --auto-filename

# 指定 NUT 服务器地址
python test_nut_parameters.py --host 192.168.1.100 --port 3493
```

**参数说明:**
- `--host`: NUT 服务器地址（默认: localhost）
- `--port`: NUT 服务器端口（默认: 3493）
- `--ups`: UPS 名称（默认: ups）
- `--output, -o`: 输出到指定的 Markdown 文件
- `--auto-filename, -a`: 自动生成文件名并保存报告（格式: ups-<品牌>-<型号>-<序列号>.md）
- `--output-dir, -d`: 输出目录（配合 --auto-filename 使用，默认: ./reports）
- `--test-all`: 测试所有 NUT 标准变量（约 500+ 个）
- `--show-all-standard`: 显示所有 NUT 标准变量列表
- `--hide-missing`: 隐藏不可用的参数

### check_ups.py - UPS 状态快速诊断

快速诊断 UPS 连接状态和数据获取问题。

```bash
python check_ups.py
```

### analyze_battery.py - 电池放电分析

分析 UPS 电池放电数据，用于诊断电池健康状况。

```bash
# 使用默认数据库路径
python analyze_battery.py

# 指定数据库路径
python analyze_battery.py --db /path/to/ups_guard.db
```

## 报告输出

使用 `--auto-filename` 参数时，报告会自动保存到 `./reports/` 目录下，文件名格式为：
```
ups-<品牌>-<型号>-<序列号>.md
```

例如：
```
reports/ups-apc-back-ups-bk650m2-ch-9B2543A10629.md
```

## 示例

生成完整的 UPS 参数测试报告：

```bash
cd backend/tools
python test_nut_parameters.py --auto-filename --test-all
```

这将自动连接 NUT 服务器，获取 UPS 信息，并在 `reports/` 目录下生成详细的 Markdown 报告。

