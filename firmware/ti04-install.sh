#!/bin/sh
# Run in the release RAM installer. Never run from NAND or generic OpenWrt.
set -eu
fail() { echo "STOP: $*" >&2; exit 1; }
get() { jsonfilter -i "$1" -e "$2"; }
digest() { sha256sum "$1" | cut -d' ' -f1; }
prop() { cat "/sys/class/mtd/$1/$2"; }
find_mtd() {
 found=''
 for p in /sys/class/mtd/mtd[0-9]*; do
  [ -f "$p/name" ] || continue
  if [ "$(cat "$p/name")" = "$1" ]; then
   [ -z "$found" ] || fail "duplicate MTD name $1"
   found=${p##*/}
  fi
 done
 [ -n "$found" ] || fail "missing MTD $1"
 echo "$found"
}
check_partition() {
 [ "$(prop "$1" type)" = "$2" ] && [ "$(prop "$1" offset)" = "$3" ] &&
 [ "$(prop "$1" size)" = "$4" ] && [ "$(prop "$1" erasesize)" = "$5" ] &&
 [ "$(prop "$1" flags)" = "$6" ] || fail "unsupported layout: $1"
 [ -c "/dev/$1" ] || fail "not a character MTD: $1"
}
preservation() {
 [ "$(digest "/dev/$tail")" = "$(get "$receipt" '@.nand_tail_sha256')" ] || fail 'NAND tail differs from own backup'
 index=0
 for name in SBL1 MIBIB QSEE CDT DDRPARAMS APPSBLENV APPSBL ART; do
  m=$(find_mtd "$name")
  [ "$(get "$receipt" "@.nor[$index].name")" = "$name" ] || fail 'NOR receipt order'
  [ "$(prop "$m" offset)" = "$(get "$receipt" "@.nor[$index].offset")" ] || fail 'NOR offset'
  [ "$(prop "$m" size)" = "$(get "$receipt" "@.nor[$index].bytes")" ] || fail 'NOR size'
  [ "$(prop "$m" type)" = nor ] && [ "$(prop "$m" flags)" = 0x800 ] || fail 'NOR not read-only'
  [ "$(digest "/dev/$m")" = "$(get "$receipt" "@.nor[$index].sha256")" ] || fail "NOR changed: $name"
  index=$((index + 1))
 done
}
[ "$#" -ge 3 ] || fail 'usage: ti04-install.sh --check|--apply BUNDLE_DIR OWN_BACKUP_RECEIPT [WRITE-FIRST32M]'
mode=$1; bundle=$2; receipt=$3
case "$mode" in --check) ;; --apply) [ "${4:-}" = WRITE-FIRST32M ] || fail 'explicit write token required';; *) fail 'unknown mode';; esac
[ "$(id -u)" = 0 ] || fail 'root required'
[ "$(cat /etc/ti04-installer-release)" = 25.12.6-ti04-r1 ] || fail 'wrong RAM installer'
[ "$(cat /tmp/sysinfo/board_name)" = giga,kt-9200 ] || fail 'wrong board'
grep -q 'rdinit=/init' /proc/cmdline || fail 'not external initramfs'
grep -q '^tmpfs / tmpfs ' /proc/mounts || fail 'root is not tmpfs'
[ ! -d /overlay/upper ] || fail 'persistent overlay is present'
for p in /sys/class/ubi/ubi[0-9]*; do [ ! -e "$p" ] || fail 'UBI already attached'; done
[ "$(get "$receipt" '@.format')" = TI04_BACKUP_V1 ] || fail 'wrong backup receipt'
[ "$(get "$receipt" '@.main_ecc_bytes')" = 134217728 ] || fail 'incomplete ECC backup'
[ "$(get "$receipt" '@.raw_oob_bytes')" = 138412032 ] || fail 'incomplete raw+OOB backup'
[ "$(get "$receipt" '@.all_chunk_crc_verified')" = true ] || fail 'chunk CRC evidence missing'
target=$(find_mtd install-target); tail=$(find_mtd stock-reserved)
check_partition "$target" nand 0 33554432 131072 0x400
check_partition "$tail" nand 33554432 100663296 131072 0x0
[ "$(prop "$target" writesize)" = 2048 ] && [ "$(prop "$target" oobsize)" = 64 ] || fail 'wrong NAND geometry'
[ "$(prop "$target" bad_blocks)" = 0 ] && [ "$(prop "$tail" bad_blocks)" = 0 ] || fail 'bad-block NAND needs separate tested handling'
manifest="$bundle/manifest.json"
[ "$(get "$manifest" '@.release')" = 25.12.6-ti04-r1 ] || fail 'wrong release'
image="$bundle/ti04-25.12.6-first32m.ubi"
[ "$(wc -c <"$image" | tr -d ' ')" = "$(get "$manifest" '@.files.ubi.bytes')" ] || fail 'image length'
[ "$(digest "$image")" = "$(get "$manifest" '@.files.ubi.sha256')" ] || fail 'image SHA256'
# Require manifest too to match the immutable copy inside the RAM image.
cmp "$manifest" /etc/ti04-release-manifest.json || fail 'manifest differs from RAM release'
preservation
echo 'TI04_ALL_INSTALL_GUARDS_PASS'
[ "$mode" = --apply ] || exit 0
mkdir /tmp/ti04-install-once || fail 'a write was already attempted this boot'
echo 'Writing ONLY first32MiB; keep power and UART connected.'
ubiformat "/dev/$target" -y -f "$image" || fail 'ubiformat failed; stay in RAM'
ubiattach -m "${target#mtd}" -d 0 || fail 'attach failed; stay in RAM'
[ "$(cat /sys/class/ubi/ubi0/mtd_num)" = "${target#mtd}" ] || fail 'wrong attach'
for n in 0 1 2; do
 case "$n" in 0) expected=kernel;; 1) expected=rootfs;; 2) expected=rootfs_data;; esac
 [ "$(cat /sys/class/ubi/ubi0_$n/name)" = "$expected" ] || fail 'volume layout mismatch'
done
for kind in kernel rootfs; do
 case "$kind" in kernel) volume=0;; rootfs) volume=1;; esac
 count=$(get "$manifest" "@.files.$kind.bytes")
 case "$count" in ''|*[!0-9]*) fail 'invalid payload length';; esac
 actual=$(head -c "$count" "/dev/ubi0_$volume" | sha256sum | cut -d' ' -f1)
 [ "$actual" = "$(get "$manifest" "@.files.$kind.sha256")" ] || fail "$kind readback mismatch; stay in RAM"
done
preservation
ubidetach -m "${target#mtd}"
sync
echo 'TI04_WRITE_READBACK_PRESERVATION_PASS. Reboot manually; NAND boot still needs verification.'
