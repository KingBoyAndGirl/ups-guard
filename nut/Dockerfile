FROM alpine:latest

# 安装 NUT 和依赖
# 包含 libusb-dev 以支持 USB 设备扫描
RUN apk add --no-cache \
    nut \
    bash \
    curl \
    usbutils \
    dos2unix \
    libusb-dev \
    eudev

# 创建 udev 规则允许 nut 用户访问 UPS 设备
RUN mkdir -p /etc/udev/rules.d && \
    echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="051d", MODE="0666"' > /etc/udev/rules.d/99-nut-ups.rules && \
    echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="0463", MODE="0666"' >> /etc/udev/rules.d/99-nut-ups.rules && \
    echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="0665", MODE="0666"' >> /etc/udev/rules.d/99-nut-ups.rules && \
    echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="06da", MODE="0666"' >> /etc/udev/rules.d/99-nut-ups.rules

# 创建配置目录
RUN mkdir -p /etc/nut /var/run/nut /var/state/ups && \
    chown -R nut:nut /etc/nut /var/run/nut /var/state/ups

# 复制 entrypoint 脚本并转换行尾
COPY entrypoint.sh /entrypoint.sh
RUN dos2unix /entrypoint.sh && chmod +x /entrypoint.sh

# 暴露 NUT 端口
EXPOSE 3493

# 使用 entrypoint 脚本启动
ENTRYPOINT ["/entrypoint.sh"]
