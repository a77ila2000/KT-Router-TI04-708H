#!/bin/sh
set -eu
cd "$(dirname "$0")"
mkdir -p build
cp -R root/. build/
"${CC:-arm-linux-gnueabihf-gcc}" -O2 -static -Wall -Wextra -Werror \
 -o build/usr/sbin/ti04-phy-led src/ti04-phy-led.c
chmod 755 build/usr/sbin/ti04-phy-led build/usr/sbin/ti04-wifi-led build/etc/init.d/ti04-leds
tar -czf ti04-led-settings.tgz -C build .
echo 'Built ti04-led-settings.tgz; inspect board and LED mapping before applying.'
