#!/bin/bash
set -e

echo "Configuring NUT server..."

# 日志级别控制 (debug, info, warn, error)
LOG_LEVEL=${LOG_LEVEL:-info}

log_debug() {
    if [ "$LOG_LEVEL" = "debug" ]; then
        echo "$(date): [DEBUG] $*"
    fi
}

log_info() {
    if [ "$LOG_LEVEL" = "debug" ] || [ "$LOG_LEVEL" = "info" ]; then
        echo "$(date): [INFO] $*"
    fi
}

log_warn() {
    if [ "$LOG_LEVEL" != "error" ]; then
        echo "$(date): [WARN] $*"
    fi
}

log_error() {
    echo "$(date): [ERROR] $*"
}

# 从环境变量读取配置，提供默认值
UPS_NAME=${UPS_NAME:-}  # 留空则自动生成
UPS_DRIVER=${UPS_DRIVER:-usbhid-ups}
UPS_PORT=${UPS_PORT:-auto}
UPS_DESC=${UPS_DESC:-}  # 留空则自动生成
UPSD_LISTEN=${UPSD_LISTEN:-0.0.0.0}
UPSD_USER=${UPSD_USER:-admin}
UPSD_PASSWORD=${UPSD_PASSWORD:-secret}
UPSMON_USER=${UPSMON_USER:-monuser}
UPSMON_PASSWORD=${UPSMON_PASSWORD:-secret}
# 是否禁用自动关机（开发/测试环境设为 true）
DISABLE_SHUTDOWN=${DISABLE_SHUTDOWN:-false}
# 传统的关机命令（仅当 DISABLE_SHUTDOWN=false 时使用）
SHUTDOWN_CMD=${SHUTDOWN_CMD:-"/sbin/shutdown -h +0"}
# 低电量阈值覆盖（解决某些 UPS 报告异常阈值的问题，如 APC 的 95%）
# 设置为合理值（如 20），UPS 电量低于此值才触发低电量警告
BATTERY_CHARGE_LOW=${BATTERY_CHARGE_LOW:-20}
# 低运行时间阈值覆盖（秒），剩余时间低于此值触发低电量警告
BATTERY_RUNTIME_LOW=${BATTERY_RUNTIME_LOW:-180}

# 用于自动生成 UPS_NAME 的变量
AUTO_BRAND=""
AUTO_SERIAL=""
AUTO_MODEL=""

# 自动发现 UPS 设备
echo "Scanning for UPS devices..."
if command -v nut-scanner &> /dev/null; then
    # 尝试扫描 USB UPS 设备
    SCAN_RESULT=$(nut-scanner -U 2>/dev/null || echo "")
    
    if [ -n "$SCAN_RESULT" ]; then
        echo "UPS devices found:"
        echo "$SCAN_RESULT"
        
        # 提取 Vendor ID, Product ID, Serial, Product Name
        VENDOR_ID=$(echo "$SCAN_RESULT" | grep "vendorid =" | head -1 | sed 's/.*vendorid = "\([^"]*\)".*/\1/')
        PRODUCT_ID=$(echo "$SCAN_RESULT" | grep "productid =" | head -1 | sed 's/.*productid = "\([^"]*\)".*/\1/')
        AUTO_SERIAL=$(echo "$SCAN_RESULT" | grep "serial =" | head -1 | sed 's/.*serial = "\([^"]*\)".*/\1/')
        AUTO_MODEL=$(echo "$SCAN_RESULT" | grep "product =" | head -1 | sed 's/.*product = "\([^"]*\)".*/\1/')

        # UPS 品牌识别映射表
        UPS_BRAND="Unknown"
        RECOMMENDED_DRIVER=""
        
        if [ -n "$VENDOR_ID" ]; then
            # 转换为小写进行匹配
            VENDOR_ID_LOWER=$(echo "$VENDOR_ID" | tr '[:upper:]' '[:lower:]')
            case "$VENDOR_ID_LOWER" in
                "051d")
                    UPS_BRAND="APC (施耐德)"
                    AUTO_BRAND="APC"
                    RECOMMENDED_DRIVER="usbhid-ups"
                    ;;
                "0463")
                    UPS_BRAND="山特 (SANTAK)"
                    AUTO_BRAND="SANTAK"
                    RECOMMENDED_DRIVER="blazer_usb"
                    ;;
                "0665")
                    UPS_BRAND="CyberPower"
                    AUTO_BRAND="CyberPower"
                    RECOMMENDED_DRIVER="usbhid-ups"
                    ;;
                "0764")
                    UPS_BRAND="华为 (Huawei)"
                    AUTO_BRAND="Huawei"
                    RECOMMENDED_DRIVER="nutdrv_qx"
                    ;;
                "06da")
                    UPS_BRAND="伊顿 (Eaton)"
                    AUTO_BRAND="Eaton"
                    RECOMMENDED_DRIVER="usbhid-ups"
                    ;;
                "0001")
                    UPS_BRAND="山特 (SANTAK Castle)"
                    AUTO_BRAND="SANTAK"
                    RECOMMENDED_DRIVER="nutdrv_qx"
                    ;;
                *)
                    UPS_BRAND="Generic (Vendor: $VENDOR_ID)"
                    AUTO_BRAND="UPS"
                    RECOMMENDED_DRIVER="usbhid-ups"
                    ;;
            esac
            
            echo "═══════════════════════════════════════"
            echo "  UPS 品牌识别"
            echo "═══════════════════════════════════════"
            echo "  品牌: $UPS_BRAND"
            echo "  Vendor ID: $VENDOR_ID"
            echo "  Product ID: $PRODUCT_ID"
            echo "  序列号: $AUTO_SERIAL"
            echo "  型号: $AUTO_MODEL"
            echo "  推荐驱动: $RECOMMENDED_DRIVER"
            echo "═══════════════════════════════════════"
            
            # 将识别结果写入共享文件，供后端读取
            mkdir -p /tmp/ups-info
            cat > /tmp/ups-info/brand.json << BRAND_EOF
{
  "brand": "$UPS_BRAND",
  "vendor_id": "$VENDOR_ID",
  "product_id": "$PRODUCT_ID",
  "serial": "$AUTO_SERIAL",
  "model": "$AUTO_MODEL",
  "recommended_driver": "$RECOMMENDED_DRIVER"
}
BRAND_EOF
        fi
        
        # 从扫描结果中提取驱动信息
        if echo "$SCAN_RESULT" | grep -q "driver ="; then
            DETECTED_DRIVER=$(echo "$SCAN_RESULT" | grep "driver =" | head -1 | sed 's/.*driver = "\([^"]*\)".*/\1/')
            DETECTED_PORT=$(echo "$SCAN_RESULT" | grep "port =" | head -1 | sed 's/.*port = "\([^"]*\)".*/\1/' || echo "auto")
            
            if [ -n "$DETECTED_DRIVER" ]; then
                echo "Detected driver: $DETECTED_DRIVER"
                UPS_DRIVER=$DETECTED_DRIVER
                if [ -n "$DETECTED_PORT" ]; then
                    echo "Detected port: $DETECTED_PORT"
                    UPS_PORT=$DETECTED_PORT
                fi
            fi
        fi
    else
        echo "No UPS devices detected via nut-scanner"
        echo "Using dummy driver for development/testing mode"
        UPS_DRIVER="dummy-ups"
        UPS_PORT="dummy.dev"
        AUTO_BRAND="dummy"

        # 创建 dummy.dev 模拟数据文件（dummy-ups 驱动需要）
        cat > /etc/nut/dummy.dev << 'DUMMY_EOF'
# Dummy UPS data for development/testing
ups.status: OL
ups.load: 25
ups.realpower.nominal: 500
battery.charge: 100
battery.voltage: 13.4
battery.voltage.nominal: 12.0
battery.runtime: 3600
input.voltage: 230.0
input.voltage.nominal: 230
input.frequency: 50.0
output.voltage: 230.0
output.frequency: 50.0
device.mfr: Dummy
device.model: Dummy UPS
device.type: ups
ups.mfr: Dummy
ups.model: Dummy UPS
ups.serial: DUMMY001
DUMMY_EOF
        echo "Created dummy.dev simulation file"
    fi
else
    echo "nut-scanner not available, using configured driver: $UPS_DRIVER"
fi

# 自动生成 UPS_NAME（如果未手动指定）
# 格式: <品牌>_<序列号后4位> 例如: APC_0629
if [ -z "$UPS_NAME" ]; then
    if [ -n "$AUTO_BRAND" ] && [ -n "$AUTO_SERIAL" ]; then
        # 取序列号后4位
        SERIAL_SUFFIX=$(echo "$AUTO_SERIAL" | tail -c 5)
        UPS_NAME="${AUTO_BRAND}_${SERIAL_SUFFIX}"
    elif [ -n "$AUTO_BRAND" ]; then
        UPS_NAME="${AUTO_BRAND}"
    else
        UPS_NAME="ups"
    fi
    echo "Auto-generated UPS_NAME: $UPS_NAME"
fi

# 自动生成 UPS_DESC（如果未手动指定）
if [ -z "$UPS_DESC" ]; then
    if [ -n "$AUTO_MODEL" ]; then
        UPS_DESC="$AUTO_MODEL"
    else
        UPS_DESC="UPS Device"
    fi
    echo "Auto-generated UPS_DESC: $UPS_DESC"
fi

# 生成 ups.conf
# 构建可选参数
EXTRA_DRIVER_OPTS=""
if [ -n "$VENDOR_ID" ]; then
    EXTRA_DRIVER_OPTS="${EXTRA_DRIVER_OPTS}    vendorid = \"$VENDOR_ID\"
"
fi
if [ -n "$PRODUCT_ID" ]; then
    EXTRA_DRIVER_OPTS="${EXTRA_DRIVER_OPTS}    productid = \"$PRODUCT_ID\"
"
fi

# 对于 APC UPS，添加子驱动强制匹配（解决 device->Product 为 NULL 的问题）
VENDOR_ID_LOWER=$(echo "$VENDOR_ID" | tr '[:upper:]' '[:lower:]')
if [ "$VENDOR_ID_LOWER" = "051d" ]; then
    # APC UPS - 使用 apc 子驱动
    EXTRA_DRIVER_OPTS="${EXTRA_DRIVER_OPTS}    # APC UPS 专用配置
    subdriver = apc
"
fi

cat > /etc/nut/ups.conf << EOF
# 由 entrypoint.sh 自动生成
# Driver discovery result: $UPS_DRIVER on $UPS_PORT
maxretry = 5
retrydelay = 3
user = root

[$UPS_NAME]
    driver = $UPS_DRIVER
    port = $UPS_PORT
    desc = "$UPS_DESC"
${EXTRA_DRIVER_OPTS}    # 覆盖 UPS 报告的异常低电量阈值
    # 某些 UPS（如 APC BK650M2）会报告 battery.charge.low = 95%，导致误触发关机
    override.battery.charge.low = $BATTERY_CHARGE_LOW
    override.battery.runtime.low = $BATTERY_RUNTIME_LOW
    # 忽略 UPS 硬件报告的 LB (Low Battery) 标志
    # 让 NUT 使用上面的阈值来判断低电量，而不是依赖 UPS 硬件判断
    ignorelb
    # 增加轮询间隔，减少 USB 通信压力（低电量时 UPS 响应可能变慢）
    pollinterval = 5
EOF

echo "Generated ups.conf with driver: $UPS_DRIVER"
echo "低电量阈值: battery.charge.low=${BATTERY_CHARGE_LOW}%, battery.runtime.low=${BATTERY_RUNTIME_LOW}s"

# 生成 upsd.conf
cat > /etc/nut/upsd.conf << EOF
# 由 entrypoint.sh 自动生成
LISTEN $UPSD_LISTEN 3493
EOF

# 生成 upsd.users
cat > /etc/nut/upsd.users << EOF
# 由 entrypoint.sh 自动生成
[$UPSD_USER]
    password = $UPSD_PASSWORD
    actions = SET
    instcmds = ALL
    upsmon primary

[$UPSMON_USER]
    password = $UPSMON_PASSWORD
    actions = SET
    instcmds = ALL
    upsmon primary
EOF

# 生成 upsmon.conf
# 根据 DISABLE_SHUTDOWN 环境变量决定关机行为
if [ "$DISABLE_SHUTDOWN" = "true" ]; then
    ACTUAL_SHUTDOWN_CMD="/bin/echo 'UPS Guard: Shutdown signal received (handled by backend)'"
    echo "注意：自动关机已禁用（DISABLE_SHUTDOWN=true）"
else
    ACTUAL_SHUTDOWN_CMD="$SHUTDOWN_CMD"
fi

cat > /etc/nut/upsmon.conf << EOF
# 由 entrypoint.sh 自动生成
MONITOR $UPS_NAME@localhost 1 $UPSMON_USER $UPSMON_PASSWORD primary
MINSUPPLIES 1
SHUTDOWNCMD "$ACTUAL_SHUTDOWN_CMD"
NOTIFYCMD /usr/sbin/upssched
POLLFREQ 5
POLLFREQALERT 5
HOSTSYNC 15
# 增加 DEADTIME 避免刚连接时误判
DEADTIME 25
POWERDOWNFLAG /etc/killpower
NOTIFYMSG ONLINE "UPS %s is online"
NOTIFYMSG ONBATT "UPS %s is on battery"
NOTIFYMSG LOWBATT "UPS %s has low battery"
NOTIFYMSG FSD "UPS %s: forced shutdown in progress"
NOTIFYMSG COMMOK "Communications with UPS %s established"
NOTIFYMSG COMMBAD "Communications with UPS %s lost"
NOTIFYMSG SHUTDOWN "Auto logout and shutdown proceeding"
NOTIFYMSG REPLBATT "UPS %s battery needs to be replaced"
NOTIFYMSG NOCOMM "UPS %s is unavailable"
NOTIFYMSG NOPARENT "upsmon parent process died - shutdown impossible"
# 移除 WALL（容器中没有 wall 命令）
NOTIFYFLAG ONLINE SYSLOG
NOTIFYFLAG ONBATT SYSLOG
NOTIFYFLAG LOWBATT SYSLOG
NOTIFYFLAG FSD SYSLOG
NOTIFYFLAG COMMOK SYSLOG
NOTIFYFLAG COMMBAD SYSLOG
NOTIFYFLAG SHUTDOWN SYSLOG
NOTIFYFLAG REPLBATT SYSLOG
NOTIFYFLAG NOCOMM SYSLOG
NOTIFYFLAG NOPARENT SYSLOG
RBWARNTIME 43200
NOCOMMWARNTIME 300
FINALDELAY 5
EOF

# 设置权限
chmod 640 /etc/nut/upsd.users
chmod 640 /etc/nut/upsmon.conf
chown root:nut /etc/nut/*

# 生成 nut.conf
cat > /etc/nut/nut.conf << EOF
MODE=standalone
EOF

# 创建状态目录
mkdir -p /var/state/ups
chown nut:nut /var/state/ups

# 创建运行目录并设置权限
mkdir -p /var/run/nut
chown root:nut /var/run/nut
chmod 770 /var/run/nut

echo "Starting UPS driver..."

# 显示 USB 设备信息（调试用）
echo "═══════════════════════════════════════"
echo "  USB 设备检查"
echo "═══════════════════════════════════════"
if command -v lsusb &> /dev/null; then
    echo "lsusb 输出:"
    lsusb 2>/dev/null | grep -i "ups\|apc\|cyber\|eaton\|051d\|0665\|06da" || echo "  (未找到已知 UPS 设备)"
else
    echo "lsusb 不可用，检查 /dev/bus/usb:"
    ls -la /dev/bus/usb/ 2>/dev/null || echo "  /dev/bus/usb 不存在"
fi
echo "═══════════════════════════════════════"

# 如果是非 dummy 驱动，尝试多次启动
if [ "$UPS_DRIVER" != "dummy-ups" ]; then
    DRIVER_STARTED=false
    for attempt in 1 2 3; do
        echo "尝试启动 UPS 驱动 (第 ${attempt}/3 次)..."
        if timeout 30 upsdrvctl start 2>&1; then
            echo "✅ UPS 驱动启动成功"
            DRIVER_STARTED=true
            break
        else
            echo "⚠️  第 ${attempt} 次启动失败"
            if [ $attempt -lt 3 ]; then
                echo "等待 3 秒后重试..."
                sleep 3
                # 尝试停止可能残留的驱动进程
                timeout 5 upsdrvctl stop >/dev/null 2>&1 || true
            fi
        fi
    done

    if [ "$DRIVER_STARTED" = false ]; then
        echo ""
        echo "═══════════════════════════════════════"
        echo "  ⚠️  UPS 驱动启动失败"
        echo "═══════════════════════════════════════"
        echo "  可能原因:"
        echo "  1. UPS 处于低电量保护模式"
        echo "  2. USB 设备权限问题"
        echo "  3. USB 连接不稳定"
        echo ""
        echo "  建议: 等待 UPS 电池充电后重试"
        echo "  服务将继续运行，等待 UPS 恢复"
        echo "═══════════════════════════════════════"
        echo ""
    fi
else
    # dummy 驱动直接启动
    timeout 30 upsdrvctl start || {
        echo "Warning: Failed to start dummy driver."
    }
fi

echo "Starting upsd..."
# 启动 upsd（前台模式，但放到后台运行）
/usr/sbin/upsd -D &
UPSD_PID=$!
sleep 1

echo "Starting upsmon..."
# 启动 upsmon（前台模式，但放到后台运行）
/usr/sbin/upsmon -D &
UPSMON_PID=$!
sleep 1

echo "NUT server started successfully"
echo "Driver: $UPS_DRIVER"
echo "Port: $UPS_PORT"
echo "upsd PID: $UPSD_PID"
echo "upsmon PID: $UPSMON_PID"

# UPS 驱动监控和自动重连函数（增强版 v2）
monitor_ups_driver() {
    local check_interval=${UPS_MONITOR_INTERVAL:-15}  # 默认每15秒检查一次
    local base_reconnect_delay=${UPS_RECONNECT_DELAY:-5}  # 基础重连延迟
    local max_fast_retries=${UPS_MAX_FAST_RETRIES:-5}  # 快速重试次数（默认5次）
    local usb_scan_interval=${UPS_USB_SCAN_INTERVAL:-10}  # USB 设备不存在时的扫描间隔（默认10秒）

    local retry_count=0
    local consecutive_failures=0
    local last_success_time=$(date +%s)
    local usb_device_missing=false  # 标记 USB 设备是否丢失
    local usb_missing_retry_count=0  # USB 设备丢失后的重试计数

    echo "═══════════════════════════════════════"
    echo "  UPS 驱动自动监控已启动 (v2)"
    echo "═══════════════════════════════════════"
    echo "  检查间隔: ${check_interval}s"
    echo "  USB 扫描间隔: ${usb_scan_interval}s"
    echo "  重连策略: 智能指数退避"
    echo "  快速重试: 前 ${max_fast_retries} 次"
    echo "  当前驱动: ${UPS_DRIVER}"
    echo "═══════════════════════════════════════"

    # 如果是 dummy 驱动，使用简化的监控模式，但仍然扫描真实设备
    if [ "$UPS_DRIVER" = "dummy-ups" ]; then
        echo ""
        echo "🔧 Dummy 模式：等待真实 UPS 设备连接"
        echo "   每 ${usb_scan_interval}s 扫描一次 USB 设备"
        echo ""
        echo "✅ NUT 服务就绪（Dummy 模式）"
        echo ""

        local scan_count=0

        # Dummy 模式下定期扫描 USB 设备，发现真实设备后切换
        while true; do
            sleep $usb_scan_interval
            scan_count=$((scan_count + 1))

            # 检查 upsd 进程是否存活
            if ! kill -0 $UPSD_PID 2>/dev/null; then
                echo "$(date): ⚠️  upsd 进程已退出，尝试重启..."
                /usr/sbin/upsd -D &
                UPSD_PID=$!
                echo "$(date): ✅ upsd 已重启 (PID: $UPSD_PID)"
            fi

            # 检查 upsmon 进程是否存活
            if ! kill -0 $UPSMON_PID 2>/dev/null; then
                echo "$(date): ⚠️  upsmon 进程已退出，尝试重启..."
                /usr/sbin/upsmon -D &
                UPSMON_PID=$!
                echo "$(date): ✅ upsmon 已重启 (PID: $UPSMON_PID)"
            fi

            # 定期扫描 USB 设备，检查是否有真实 UPS 连接
            if command -v nut-scanner &> /dev/null; then
                SCAN_RESULT=$(nut-scanner -U 2>/dev/null || echo "")
                if [ -n "$SCAN_RESULT" ]; then
                    echo "$(date): 🎉 发现真实 UPS 设备！正在切换..."
                    echo "$SCAN_RESULT"

                    # 提取设备信息
                    local found_vendor=$(echo "$SCAN_RESULT" | grep "vendorid =" | head -1 | sed 's/.*vendorid = "\([^"]*\)".*/\1/' || echo "unknown")
                    local found_product=$(echo "$SCAN_RESULT" | grep "productid =" | head -1 | sed 's/.*productid = "\([^"]*\)".*/\1/' || echo "unknown")
                    local found_driver=$(echo "$SCAN_RESULT" | grep "driver =" | head -1 | sed 's/.*driver = "\([^"]*\)".*/\1/' || echo "usbhid-ups")
                    local found_port=$(echo "$SCAN_RESULT" | grep "port =" | head -1 | sed 's/.*port = "\([^"]*\)".*/\1/' || echo "auto")
                    local found_serial=$(echo "$SCAN_RESULT" | grep "serial =" | head -1 | sed 's/.*serial = "\([^"]*\)".*/\1/' || echo "")
                    local found_model=$(echo "$SCAN_RESULT" | grep "product =" | head -1 | sed 's/.*product = "\([^"]*\)".*/\1/' || echo "UPS Device")

                    # 根据 Vendor ID 识别品牌
                    local new_brand="UPS"
                    local vendor_lower=$(echo "$found_vendor" | tr '[:upper:]' '[:lower:]')
                    case "$vendor_lower" in
                        "051d") new_brand="APC" ;;
                        "0463") new_brand="SANTAK" ;;
                        "0665") new_brand="CyberPower" ;;
                        "0764") new_brand="Huawei" ;;
                        "06da") new_brand="Eaton" ;;
                    esac

                    # 生成新的 UPS 名称
                    local new_ups_name
                    if [ -n "$found_serial" ]; then
                        local serial_suffix=$(echo "$found_serial" | tail -c 5)
                        new_ups_name="${new_brand}_${serial_suffix}"
                    else
                        new_ups_name="${new_brand}"
                    fi

                    echo "$(date): 📝 配置真实 UPS: name=${new_ups_name}, driver=${found_driver}"

                    # 停止 dummy 驱动
                    echo "$(date): 🔄 停止 Dummy 驱动..."
                    timeout 10 upsdrvctl stop >/dev/null 2>&1 || true

                    # 生成子驱动配置（APC 需要强制指定 subdriver）
                    local subdriver_opt=""
                    local vendor_lower_switch=$(echo "$found_vendor" | tr '[:upper:]' '[:lower:]')
                    if [ "$vendor_lower_switch" = "051d" ]; then
                        subdriver_opt="    subdriver = apc"
                    fi

                    # 重新生成 ups.conf
                    cat > /etc/nut/ups.conf << SWITCH_EOF
# 由 monitor_ups_driver 自动切换到真实设备
# 检测时间: $(date)
maxretry = 5
retrydelay = 3
user = root

[${new_ups_name}]
    driver = ${found_driver}
    port = ${found_port}
    desc = "${found_model}"
    vendorid = "${found_vendor}"
    productid = "${found_product}"
${subdriver_opt}
    # 覆盖异常的低电量阈值
    override.battery.charge.low = $BATTERY_CHARGE_LOW
    override.battery.runtime.low = $BATTERY_RUNTIME_LOW
    # 忽略 UPS 硬件报告的 LB 标志
    ignorelb
    pollinterval = 5
SWITCH_EOF

                    # 更新 upsmon.conf 中的 UPS 名称
                    sed -i "s/^MONITOR .* 1 $UPSMON_USER/MONITOR ${new_ups_name}@localhost 1 $UPSMON_USER/" /etc/nut/upsmon.conf

                    # 更新全局变量
                    UPS_NAME="$new_ups_name"
                    UPS_DRIVER="$found_driver"

                    # 启动真实驱动
                    echo "$(date): 🔄 启动真实 UPS 驱动..."
                    if timeout 30 upsdrvctl start >/dev/null 2>&1; then
                        echo "$(date): ✅ UPS 驱动启动成功"

                        # 先强制杀死所有 upsd 和 upsmon 进程
                        echo "$(date): 🔄 停止旧的 upsd/upsmon 进程..."
                        kill $UPSD_PID 2>/dev/null || true
                        kill $UPSMON_PID 2>/dev/null || true
                        # 确保所有 upsmon 进程都被杀死（防止残留）
                        killall -9 upsmon 2>/dev/null || true
                        killall -9 upsd 2>/dev/null || true
                        # 删除 PID 文件
                        rm -f /var/run/nut/upsd.pid /run/upsmon.pid 2>/dev/null || true
                        sleep 2

                        # 重启 upsd
                        echo "$(date): 🔄 启动新的 upsd..."
                        /usr/sbin/upsd -D &
                        UPSD_PID=$!
                        sleep 1

                        # 重启 upsmon
                        echo "$(date): 🔄 启动新的 upsmon..."
                        /usr/sbin/upsmon -D &
                        UPSMON_PID=$!
                        sleep 1

                        echo "$(date): ✅ 已切换到真实 UPS 模式"
                        echo "$(date): 📊 upsd PID: $UPSD_PID, upsmon PID: $UPSMON_PID"

                        # 跳出 dummy 模式循环，进入正常监控模式
                        break
                    else
                        echo "$(date): ❌ UPS 驱动启动失败，继续 Dummy 模式..."
                    fi
                else
                    # 每10次扫描输出一次状态（约100秒）
                    if [ $((scan_count % 10)) -eq 0 ]; then
                        echo "$(date): 🔍 [Dummy] 第 ${scan_count} 次扫描，未发现 USB UPS 设备"
                    fi
                fi
            fi
        done

        # 如果跳出了 dummy 循环，继续执行下面的正常监控逻辑
        echo ""
        echo "═══════════════════════════════════════"
        echo "  已切换到真实 UPS 监控模式"
        echo "═══════════════════════════════════════"
        echo ""
    fi

    # 以下是真实 USB UPS 的监控逻辑
    echo ""
    echo "✅ NUT 服务就绪，等待连接..."
    echo "   如无异常日志输出，表示系统正常运行中"
    echo ""

    # 心跳计数器（用于定期输出状态）
    local heartbeat_count=0
    local heartbeat_interval=60  # 每60次检查输出一次心跳（约5分钟）
    # 标记是否处于 Dummy 等待模式（真实设备断开后自动切换的模式）
    local in_dummy_wait_mode=false
    # Dummy 等待模式下的扫描计数器
    local dummy_wait_scan_count=0

    while true; do
        # 根据当前状态决定等待时间
        local wait_time=$check_interval
        if [ "$usb_device_missing" = true ] || [ "$in_dummy_wait_mode" = true ]; then
            wait_time=$usb_scan_interval
        fi

        sleep $wait_time

        # 如果当前是 Dummy 等待模式，持续扫描真实设备
        if [ "$in_dummy_wait_mode" = true ]; then
            dummy_wait_scan_count=$((dummy_wait_scan_count + 1))

            # 检查 upsd/upsmon 进程是否存活
            if ! kill -0 $UPSD_PID 2>/dev/null; then
                log_debug "upsd 进程已退出，尝试重启..."
                /usr/sbin/upsd -D &
                UPSD_PID=$!
            fi
            if ! kill -0 $UPSMON_PID 2>/dev/null; then
                log_debug "upsmon 进程已退出，尝试重启..."
                /usr/sbin/upsmon -D &
                UPSMON_PID=$!
            fi

            # 扫描 USB 设备
            if command -v nut-scanner &> /dev/null; then
                SCAN_RESULT=$(nut-scanner -U 2>/dev/null || echo "")
                if [ -n "$SCAN_RESULT" ]; then
                    echo "$(date): 🎉 [Dummy等待] 发现真实 UPS 设备！正在切换..."
                    echo "$SCAN_RESULT"

                    # 提取设备信息
                    local new_vendor=$(echo "$SCAN_RESULT" | grep "vendorid =" | head -1 | sed 's/.*vendorid = "\([^"]*\)".*/\1/' || echo "")
                    local new_product=$(echo "$SCAN_RESULT" | grep "productid =" | head -1 | sed 's/.*productid = "\([^"]*\)".*/\1/' || echo "")
                    local new_driver=$(echo "$SCAN_RESULT" | grep "driver =" | head -1 | sed 's/.*driver = "\([^"]*\)".*/\1/' || echo "usbhid-ups")
                    local new_port=$(echo "$SCAN_RESULT" | grep "port =" | head -1 | sed 's/.*port = "\([^"]*\)".*/\1/' || echo "auto")
                    local new_serial=$(echo "$SCAN_RESULT" | grep "serial =" | head -1 | sed 's/.*serial = "\([^"]*\)".*/\1/' || echo "")
                    local new_model=$(echo "$SCAN_RESULT" | grep "product =" | head -1 | sed 's/.*product = "\([^"]*\)".*/\1/' || echo "UPS Device")

                    # 识别品牌
                    local new_brand="UPS"
                    case "$(echo "$new_vendor" | tr '[:upper:]' '[:lower:]')" in
                        "051d") new_brand="APC" ;;
                        "0463") new_brand="SANTAK" ;;
                        "0665") new_brand="CyberPower" ;;
                        "0764") new_brand="Huawei" ;;
                        "06da") new_brand="Eaton" ;;
                    esac

                    # 生成 UPS 名称
                    local new_ups_name
                    if [ -n "$new_serial" ]; then
                        local serial_suffix=$(echo "$new_serial" | tail -c 5)
                        new_ups_name="${new_brand}_${serial_suffix}"
                    else
                        new_ups_name="${new_brand}"
                    fi

                    echo "$(date): 📝 配置 UPS: name=${new_ups_name}, driver=${new_driver}"

                    # 停止 Dummy 服务
                    echo "$(date): 🔄 停止 Dummy 服务..."
                    timeout 10 upsdrvctl stop >/dev/null 2>&1 || true
                    kill $UPSD_PID 2>/dev/null || true
                    kill $UPSMON_PID 2>/dev/null || true
                    killall -9 upsd upsmon 2>/dev/null || true
                    rm -f /var/run/nut/upsd.pid /run/upsmon.pid 2>/dev/null || true
                    sleep 2

                    # 更新配置
                    UPS_NAME="$new_ups_name"
                    UPS_DRIVER="$new_driver"

                    # 生成子驱动配置（APC 需要强制指定 subdriver）
                    local subdriver_opt_wait=""
                    local vendor_lower_wait=$(echo "$new_vendor" | tr '[:upper:]' '[:lower:]')
                    if [ "$vendor_lower_wait" = "051d" ]; then
                        subdriver_opt_wait="    subdriver = apc"
                    fi

                    cat > /etc/nut/ups.conf << DUMMY_WAIT_RECONNECT_EOF
# 从 Dummy 等待模式恢复到真实设备
# 时间: $(date)
maxretry = 5
retrydelay = 3
user = root

[${new_ups_name}]
    driver = ${new_driver}
    port = ${new_port}
    desc = "${new_model}"
    vendorid = "${new_vendor}"
    productid = "${new_product}"
${subdriver_opt_wait}
    # 覆盖异常的低电量阈值
    override.battery.charge.low = $BATTERY_CHARGE_LOW
    override.battery.runtime.low = $BATTERY_RUNTIME_LOW
    # 忽略 UPS 硬件报告的 LB 标志
    ignorelb
    pollinterval = 5
DUMMY_WAIT_RECONNECT_EOF

                    sed -i "s/^MONITOR .* 1 $UPSMON_USER/MONITOR ${new_ups_name}@localhost 1 $UPSMON_USER/" /etc/nut/upsmon.conf

                    # 启动真实设备驱动
                    echo "$(date): 🔄 启动真实 UPS 驱动..."
                    if timeout 30 upsdrvctl start >/dev/null 2>&1; then
                        sleep 1
                        /usr/sbin/upsd -D &
                        UPSD_PID=$!
                        sleep 1
                        /usr/sbin/upsmon -D &
                        UPSMON_PID=$!

                        echo "$(date): ✅ 已从 Dummy 等待模式切换到真实 UPS (upsd PID: $UPSD_PID, upsmon PID: $UPSMON_PID)"

                        # 重置状态
                        in_dummy_wait_mode=false
                        dummy_wait_scan_count=0
                        retry_count=0
                        consecutive_failures=0
                        usb_device_missing=false
                        last_success_time=$(date +%s)
                    else
                        echo "$(date): ❌ UPS 驱动启动失败，继续 Dummy 等待模式..."
                    fi
                else
                    # 每10次扫描输出一次状态
                    if [ $((dummy_wait_scan_count % 10)) -eq 0 ]; then
                        echo "$(date): 🔍 [Dummy等待] 第 ${dummy_wait_scan_count} 次扫描，未发现 USB UPS 设备"
                    fi
                fi
            fi
            continue  # 继续下一轮 Dummy 等待扫描
        fi

        # 检查 UPS 驱动是否能获取数据
        if upsc ${UPS_NAME}@localhost ups.status >/dev/null 2>&1; then
            # 通信正常
            if [ $consecutive_failures -gt 0 ] || [ "$usb_device_missing" = true ]; then
                local current_time=$(date +%s)
                local downtime=$((current_time - last_success_time))
                echo "$(date): ✅ UPS 驱动通信已恢复（故障持续 ${downtime}s，共重试 ${retry_count} 次）"
                retry_count=0
                consecutive_failures=0
                usb_device_missing=false
            fi
            last_success_time=$(date +%s)
        else
            # 通信中断
            consecutive_failures=$((consecutive_failures + 1))
            retry_count=$((retry_count + 1))
            
            # 先扫描 USB 设备，确定是驱动问题还是设备丢失
            local device_found=false
            if command -v nut-scanner &> /dev/null; then
                SCAN_RESULT=$(nut-scanner -U 2>/dev/null || echo "")
                if [ -n "$SCAN_RESULT" ]; then
                    device_found=true
                fi
            fi

            if [ "$device_found" = false ]; then
                # USB 设备未检测到
                if [ "$usb_device_missing" = false ]; then
                    # 首次检测到设备丢失，开始重试
                    usb_device_missing=true
                    usb_missing_retry_count=0
                    echo "$(date): ⚠️  USB UPS 设备未检测到，开始重试..."
                    echo "$(date): 💡 可能原因: USB 断开、设备被占用、Docker 设备映射问题"
                    # 先停止驱动，避免无效查询
                    timeout 10 upsdrvctl stop >/dev/null 2>&1 || true
                fi

                usb_missing_retry_count=$((usb_missing_retry_count + 1))

                # 前 5 次快速重试（每 10 秒），之后切换到 dummy 模式
                local max_usb_retries=5

                if [ $usb_missing_retry_count -le $max_usb_retries ]; then
                    # 快速重试阶段
                    echo "$(date): 🔍 扫描 USB 设备... (第 ${usb_missing_retry_count}/${max_usb_retries} 次重试，间隔 ${usb_scan_interval}s)"

                    # 输出 /dev/bus/usb 状态（调试用）
                    if [ "$LOG_LEVEL" = "debug" ]; then
                        echo "$(date): [DEBUG] /dev/bus/usb 内容:"
                        ls -la /dev/bus/usb/ 2>/dev/null || echo "  (无法访问)"
                        for bus in /dev/bus/usb/*/; do
                            if [ -d "$bus" ]; then
                                echo "  $bus: $(ls "$bus" 2>/dev/null | wc -l) 个设备"
                            fi
                        done
                    fi

                    continue  # 继续重试
                fi

                # 超过最大重试次数，切换到 dummy 等待模式
                if [ $usb_missing_retry_count -eq $((max_usb_retries + 1)) ]; then
                    echo "$(date): ⚠️  USB 设备重试 ${max_usb_retries} 次后仍未恢复，切换到 Dummy 等待模式..."

                    # 停止所有 NUT 服务
                    echo "$(date): 🔄 停止所有 NUT 服务..."
                    timeout 10 upsdrvctl stop >/dev/null 2>&1 || true
                    kill $UPSD_PID 2>/dev/null || true
                    kill $UPSMON_PID 2>/dev/null || true
                    killall -9 upsd upsmon 2>/dev/null || true
                    rm -f /var/run/nut/upsd.pid /run/upsmon.pid 2>/dev/null || true
                    sleep 2

                    # 切换到 dummy 模式配置
                    echo "$(date): 🔄 切换到 Dummy 等待模式..."
                    UPS_NAME="dummy"
                    UPS_DRIVER="dummy-ups"

                    # 重新生成配置文件
                    cat > /etc/nut/ups.conf << WAIT_EOF
# USB 设备丢失，切换到 dummy 等待模式
# 时间: $(date)
maxretry = 3
user = root

[dummy]
    driver = dummy-ups
    port = dummy.dev
    desc = "Waiting for USB UPS device"
WAIT_EOF

                    # 创建 dummy.dev 文件（状态设为 OL 避免触发关机）
                    cat > /etc/nut/dummy.dev << 'DUMMY_WAIT_EOF'
# USB 设备已断开，等待重新连接
# 状态设为 OL 避免 upsmon 触发自动关机
ups.status: OL
ups.load: 0
battery.charge: 100
battery.runtime: 9999
device.mfr: Waiting
device.model: USB Device Disconnected
ups.mfr: Waiting
ups.model: USB Device Disconnected
ups.serial: WAITING
DUMMY_WAIT_EOF

                    # 更新 upsmon.conf
                    sed -i "s/^MONITOR .* 1 $UPSMON_USER/MONITOR dummy@localhost 1 $UPSMON_USER/" /etc/nut/upsmon.conf

                    # 重新启动驱动和服务
                    echo "$(date): 🔄 启动 Dummy 模式服务..."
                    timeout 30 upsdrvctl start >/dev/null 2>&1 || true
                    sleep 1
                    /usr/sbin/upsd -D &
                    UPSD_PID=$!
                    sleep 1
                    /usr/sbin/upsmon -D &
                    UPSMON_PID=$!

                    echo "$(date): ✅ 已切换到 Dummy 等待模式 (upsd PID: $UPSD_PID, upsmon PID: $UPSMON_PID)"

                    # 标记当前处于 Dummy 等待模式，需要持续扫描真实设备
                    in_dummy_wait_mode=true
                    dummy_wait_scan_count=0

                    # 直接进入下一轮循环，由 Dummy 等待模式的专门逻辑处理
                    continue
                fi

                # 如果还在快速重试阶段，继续等待
                continue
            fi

            # USB 设备存在但驱动通信失败，使用指数退避策略
            usb_device_missing=false

            # 计算重连延迟（智能指数退避）
            local reconnect_delay
            if [ $retry_count -le $max_fast_retries ]; then
                # 快速重试阶段：2s, 4s, 6s, 8s, 10s (更快的间隔，用于 USB-IP 瞬断恢复)
                reconnect_delay=$((2 * retry_count))
                echo "$(date): ⚠️  UPS 驱动通信中断 (第 ${retry_count} 次重试，快速模式，延迟 ${reconnect_delay}s)"
            else
                # 降低频率：每 15s 重试一次（从 30s 优化为 15s，适应 USB-IP 不稳定性）
                reconnect_delay=15
                echo "$(date): ⚠️  UPS 驱动通信中断 (第 ${retry_count} 次重试，常规模式，延迟 ${reconnect_delay}s)"
            fi

            # 停止现有驱动（使用 timeout 防止卡死）
            echo "$(date): 🔄 停止现有驱动..."
            timeout 10 upsdrvctl stop >/dev/null 2>&1 || true
            # 清理可能残留的驱动进程（支持多种驱动类型）
            killall -9 usbhid-ups blazer_usb nutdrv_qx 2>/dev/null || true
            rm -f /var/run/nut/usbhid-ups-*.pid /var/run/nut/blazer_usb-*.pid /var/run/nut/nutdrv_qx-*.pid 2>/dev/null || true
            # USB-IP 环境下，设备可能需要额外时间重新枚举
            sleep 2

            # 等待后重启驱动
            sleep $reconnect_delay

            # USB 设备已确认存在，处理扫描结果
            if [ -n "$SCAN_RESULT" ]; then
                # 提取设备信息用于日志
                local found_vendor=$(echo "$SCAN_RESULT" | grep "vendorid =" | head -1 | sed 's/.*vendorid = "\([^"]*\)".*/\1/' || echo "unknown")
                local found_product=$(echo "$SCAN_RESULT" | grep "productid =" | head -1 | sed 's/.*productid = "\([^"]*\)".*/\1/' || echo "unknown")
                local found_driver=$(echo "$SCAN_RESULT" | grep "driver =" | head -1 | sed 's/.*driver = "\([^"]*\)".*/\1/' || echo "usbhid-ups")
                local found_port=$(echo "$SCAN_RESULT" | grep "port =" | head -1 | sed 's/.*port = "\([^"]*\)".*/\1/' || echo "auto")
                local found_serial=$(echo "$SCAN_RESULT" | grep "serial =" | head -1 | sed 's/.*serial = "\([^"]*\)".*/\1/' || echo "")
                local found_model=$(echo "$SCAN_RESULT" | grep "product =" | head -1 | sed 's/.*product = "\([^"]*\)".*/\1/' || echo "UPS Device")

                echo "$(date): ✅ 发现 UPS 设备 (VID:${found_vendor} PID:${found_product})，重新配置驱动..."

                # 根据 Vendor ID 识别品牌并生成 UPS 名称
                local new_brand="UPS"
                local vendor_lower=$(echo "$found_vendor" | tr '[:upper:]' '[:lower:]')
                case "$vendor_lower" in
                    "051d") new_brand="APC" ;;
                    "0463") new_brand="SANTAK" ;;
                    "0665") new_brand="CyberPower" ;;
                    "0764") new_brand="Huawei" ;;
                    "06da") new_brand="Eaton" ;;
                esac

                # 生成新的 UPS 名称
                local new_ups_name
                if [ -n "$found_serial" ]; then
                    local serial_suffix=$(echo "$found_serial" | tail -c 5)
                    new_ups_name="${new_brand}_${serial_suffix}"
                else
                    new_ups_name="${new_brand}"
                fi

                echo "$(date): 📝 更新配置: UPS_NAME=${new_ups_name}, driver=${found_driver}"

                # 生成子驱动配置（APC 需要强制指定 subdriver）
                local subdriver_opt_mon=""
                if [ "$vendor_lower" = "051d" ]; then
                    subdriver_opt_mon="    subdriver = apc"
                fi

                # 重新生成 ups.conf
                cat > /etc/nut/ups.conf << MONITOR_EOF
# 由 monitor_ups_driver 自动重新生成
# 检测时间: $(date)
maxretry = 5
retrydelay = 3
user = root

[${new_ups_name}]
    driver = ${found_driver}
    port = ${found_port}
    desc = "${found_model}"
    vendorid = "${found_vendor}"
    productid = "${found_product}"
${subdriver_opt_mon}
    # 覆盖异常的低电量阈值
    override.battery.charge.low = $BATTERY_CHARGE_LOW
    override.battery.runtime.low = $BATTERY_RUNTIME_LOW
    # 忽略 UPS 硬件报告的 LB 标志
    ignorelb
    pollinterval = 5
MONITOR_EOF

                # 更新 upsmon.conf 中的 UPS 名称
                sed -i "s/^MONITOR .* 1 $UPSMON_USER/MONITOR ${new_ups_name}@localhost 1 $UPSMON_USER/" /etc/nut/upsmon.conf

                # 更新全局变量供后续检查使用
                UPS_NAME="$new_ups_name"

                # USB-IP 环境下，设备重连需要额外等待时间让设备稳定
                echo "$(date): 🔄 等待 USB 设备稳定 (5s)..."
                sleep 5

                # 清理可能残留的驱动进程和锁文件（支持多种驱动类型）
                killall -9 usbhid-ups blazer_usb nutdrv_qx 2>/dev/null || true
                rm -f /var/run/nut/usbhid-ups-*.pid /var/run/nut/blazer_usb-*.pid /var/run/nut/nutdrv_qx-*.pid 2>/dev/null || true
                sleep 2

                # 重启驱动（使用 timeout 防止卡死）
                if timeout 45 upsdrvctl start 2>&1; then
                    echo "$(date): ✅ UPS 驱动重启成功"

                    # 强制杀死旧的 upsd/upsmon 进程
                    kill $UPSD_PID 2>/dev/null || true
                    kill $UPSMON_PID 2>/dev/null || true
                    killall -9 upsd 2>/dev/null || true
                    killall -9 upsmon 2>/dev/null || true
                    rm -f /var/run/nut/upsd.pid /run/upsmon.pid 2>/dev/null || true
                    sleep 2

                    # 重启 upsd 以加载新配置
                    /usr/sbin/upsd -D &
                    UPSD_PID=$!
                    sleep 1

                    # 重启 upsmon
                    /usr/sbin/upsmon -D &
                    UPSMON_PID=$!

                    echo "$(date): ✅ upsd/upsmon 已重新加载配置 (upsd PID: $UPSD_PID, upsmon PID: $UPSMON_PID)"
                else
                    echo "$(date): ❌ UPS 驱动重启失败，将继续重试..."
                fi
            else
                # 没有 nut-scanner，直接尝试重启驱动
                echo "$(date): 🔄 尝试重启驱动（无 nut-scanner）..."
                if timeout 30 upsdrvctl start >/dev/null 2>&1; then
                    echo "$(date): ✅ UPS 驱动重启成功"
                else
                    echo "$(date): ❌ UPS 驱动重启失败，将继续重试..."
                fi
            fi
        fi
    done
}

# 在后台启动 UPS 驱动监控
monitor_ups_driver &
MONITOR_PID=$!
echo "UPS driver monitor started (PID: $MONITOR_PID)"

# 捕获信号以优雅关闭
cleanup() {
    echo "Shutting down NUT server..."
    # 停止监控进程
    kill $MONITOR_PID 2>/dev/null || true
    # 使用 timeout 停止驱动，防止卡死
    timeout 10 upsdrvctl stop 2>/dev/null || true
    # 停止 upsd 和 upsmon
    kill $UPSD_PID 2>/dev/null || true
    kill $UPSMON_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGTERM SIGINT

# 等待后台进程（比 tail -f 更干净）
wait $MONITOR_PID
