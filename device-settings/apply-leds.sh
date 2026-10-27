#!/bin/sh
set -eu
[ "$(cat /tmp/sysinfo/board_name)" = 'giga,kt-9200' ]
[ "$(cat /tmp/sysinfo/model)" = 'TI04-708H' ]
[ -z "$(uci -q changes system)" ] || { echo 'Save or discard existing system changes first'; exit 1; }
[ -w /sys/class/leds/green:wan/brightness ] && [ -w /sys/class/leds/green:wlan/brightness ]
source=${1:?usage: sh apply-leds.sh EXTRACTED_PACKAGE_DIRECTORY}
backup=/root/ti04-led-settings-backup
[ ! -e "$backup" ] || { echo 'Existing backup: inspect it before reinstalling'; exit 1; }
for path in usr/sbin/ti04-phy-led usr/sbin/ti04-wifi-led etc/init.d/ti04-leds; do
 [ -f "$source/$path" ] && [ ! -e "/$path" ] || { echo "Missing source or existing target: $path"; exit 1; }
done
for section in led_ti04_wan led_ti04_wlan; do
 if uci -q get "system.$section" >/dev/null; then echo "Existing LED section: $section"; exit 1; fi
done
"$source/usr/sbin/ti04-phy-led" --self-test
"$source/usr/sbin/ti04-phy-led"
mkdir -m 700 "$backup"
cp -p /etc/config/system "$backup/system"
restore_on_error() {
 code=$?
 if [ "$code" -ne 0 ]; then
  /etc/init.d/ti04-leds stop 2>/dev/null || true
  /etc/init.d/ti04-leds disable 2>/dev/null || true
  uci -q revert system || true
  cp -p "$backup/system" /etc/config/system
  for path in usr/sbin/ti04-phy-led usr/sbin/ti04-wifi-led etc/init.d/ti04-leds; do rm -f "/$path"; done
  /etc/init.d/led restart || true
  echo 'LED installation failed; previous system configuration restored'
 fi
}
trap restore_on_error EXIT
for path in usr/sbin/ti04-phy-led usr/sbin/ti04-wifi-led etc/init.d/ti04-leds; do
 cp "$source/$path" "/$path"; chmod 755 "/$path"
done
uci set system.led_ti04_wan=led
uci set system.led_ti04_wan.name='WAN link and activity'
uci set system.led_ti04_wan.sysfs='green:wan'
uci set system.led_ti04_wan.trigger='netdev'
uci set system.led_ti04_wan.dev='wan'
uci set system.led_ti04_wan.mode='link tx rx'
uci set system.led_ti04_wan.default='0'
uci set system.led_ti04_wlan=led
uci set system.led_ti04_wlan.name='Wi-Fi 2.4 and 5 GHz activity'
uci set system.led_ti04_wlan.sysfs='green:wlan'
uci set system.led_ti04_wlan.trigger='none'
uci set system.led_ti04_wlan.default='0'
uci commit system
/etc/init.d/led restart
/etc/init.d/ti04-leds enable
/etc/init.d/ti04-leds start
sync
echo 'LED settings installed; check actual LAN numbers and visible activity.'
