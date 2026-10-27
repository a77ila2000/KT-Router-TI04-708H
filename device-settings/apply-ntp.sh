#!/bin/sh
set -eu
[ "$(cat /tmp/sysinfo/board_name)" = 'giga,kt-9200' ]
[ "$(cat /tmp/sysinfo/model)" = 'TI04-708H' ]
if uci -q show system | grep -q '=timeserver$'; then
 echo 'Existing time-server configuration preserved'; exit 0
fi
[ -z "$(uci -q changes system)" ] || { echo 'Save or discard existing system changes first'; exit 1; }
[ ! -e /root/ti04-system-before-ntp ] || { echo 'Previous NTP backup exists'; exit 1; }
cp -p /etc/config/system /root/ti04-system-before-ntp
uci set system.ntp=timeserver
uci set system.ntp.enabled='1'
uci set system.ntp.enable_server='0'
for number in 0 1 2 3; do uci add_list system.ntp.server="$number.openwrt.pool.ntp.org"; done
uci commit system
/etc/init.d/sysntpd enable
/etc/init.d/sysntpd restart
echo 'Default NTP client configured; verify the actual clock after Internet access.'
